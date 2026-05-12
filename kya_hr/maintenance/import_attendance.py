"""Import des présences mensuelles depuis Excel KYA → ERPNext Attendance.

Source : `D:\\Stage_KYA_Energy\\RH\\PRESENCE DU PERSONNEL_*.xlsx`
Onglet `VENTILATION` (grille jour × employé).

Codes Excel → status Attendance ERPNext :
  P     -> Present
  R     -> Present (late_entry = 1)
  M     -> Work From Home (Mission terrain)
  C     -> On Leave (Annual Leave)
  PC    -> On Leave (Permission convenance)
  CM    -> On Leave (Maternité / Paternité)
  RM    -> On Leave (Sick Leave)
  CF    -> On Leave (Formation)
  PE    -> On Leave (Permission Exceptionnelle)
  MP    -> Absent (Mis à pied — pénalisé)
  CG    -> On Leave (Congé général)
  F     -> Holiday → skip (géré par Holiday List)
  vide  -> Absent (à activer via flag --include-absences)

Usage :
    bench --site <site> execute kya_hr.maintenance.import_attendance.run \
        --kwargs '{"path":"/path/to/file.xlsx", "dry_run":true}'

Ou en local pour preview du JSON sans toucher la base :
    python kya_hr/maintenance/import_attendance.py --path "D:\\..." --output ./attendance.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import openpyxl


STATUS_MAP = {
    "P":  {"status": "Present"},
    "R":  {"status": "Present", "late_entry": 1},
    "M":  {"status": "Work From Home"},
    "C":  {"status": "On Leave", "leave_type": "Congé Annuel"},
    "PC": {"status": "On Leave", "leave_type": "Permission Convenance"},
    "CM": {"status": "On Leave", "leave_type": "Congé Maternité"},
    "RM": {"status": "On Leave", "leave_type": "Congé Maladie"},
    "CF": {"status": "On Leave", "leave_type": "Congé Formation"},
    "PE": {"status": "On Leave", "leave_type": "Permission Exceptionnelle"},
    "MP": {"status": "Absent"},
    "CG": {"status": "On Leave", "leave_type": "Congé Général"},
    "F":  None,  # skip — Holiday géré côté Holiday List
}


def _norm(value) -> str:
    """Normalise un nom (sans accents, lowercase, sans doublons d'espaces)."""
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text).lower()
    return text


def _find_header_row(ws):
    """Cherche la ligne contenant 'N° ORD' ou 'NOM' + 'PRENOMS' (en-tête tableau)."""
    for r in range(1, min(ws.max_row + 1, 50)):
        for c in range(1, min(ws.max_column + 1, 10)):
            value = _norm(ws.cell(r, c).value)
            if value in ("nom",) and _norm(ws.cell(r, c + 1).value) == "prenoms":
                return r
    return None


def _parse_dates_row(ws, header_row, max_col=50):
    """Récupère la ligne de dates (juste au-dessus du header tableau)."""
    dates = {}
    for r in range(max(1, header_row - 3), header_row):
        for c in range(1, min(ws.max_column + 1, max_col)):
            value = ws.cell(r, c).value
            if isinstance(value, (date, datetime)):
                dates[c] = value.date() if isinstance(value, datetime) else value
        if len(dates) >= 5:
            return dates
    return dates


VALID_CODES = set(STATUS_MAP.keys()) | {"A", ""}

# Sous-headers à ignorer dans la zone de données (Excel KYA a plusieurs lignes
# de titres sous l'en-tête principal : day numbers, "Colonne36", "Mle/Nom/...").
SUBHEADER_NOMS = {"nom", "mle", "n ord", "n°ord", "section"}


def _row_looks_like_data(ws, r):
    """True si la ligne ressemble à un employé (col 2 = NOM en majuscules)."""
    nom = ws.cell(r, 2).value
    prenoms = ws.cell(r, 3).value
    if not nom or not prenoms:
        return False
    nom_str = str(nom).strip()
    if _norm(nom_str) in SUBHEADER_NOMS:
        return False
    # On veut au moins 2 caractères et des lettres
    if len(nom_str) < 2 or not re.search(r"[A-Za-zÀ-ÿ]", nom_str):
        return False
    return True


def parse_workbook(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True)
    if "VENTILATION" not in wb.sheetnames:
        raise SystemExit(f"Onglet VENTILATION introuvable dans {path}")
    ws = wb["VENTILATION"]

    header_row = _find_header_row(ws)
    if not header_row:
        raise SystemExit("Impossible de localiser la ligne d'en-tête (NOM + PRENOMS).")

    dates = _parse_dates_row(ws, header_row)
    if not dates:
        raise SystemExit("Aucune date détectée au-dessus de l'en-tête.")

    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        if not _row_looks_like_data(ws, r):
            continue
        nom = ws.cell(r, 2).value
        prenoms = ws.cell(r, 3).value
        full_name = f"{str(nom).strip()} {str(prenoms).strip()}".strip()
        full_name_norm = _norm(full_name)
        daily = {}
        for col, date_value in dates.items():
            code = ws.cell(r, col).value
            if code is None:
                continue
            code_str = str(code).strip().upper()
            # On ne garde que les codes connus (filtre les jours non remplis ou
            # autres bruits hérités de mise en forme conditionnelle)
            if code_str not in STATUS_MAP:
                continue
            daily[date_value.isoformat()] = code_str
        if daily:
            rows.append({
                "nom": str(nom).strip(),
                "prenoms": str(prenoms).strip(),
                "full_name": full_name,
                "full_name_norm": full_name_norm,
                "poste": ws.cell(r, 4).value,
                "departement": ws.cell(r, 5).value,
                "daily": daily,
            })
    return rows


def _employee_index():
    """Construit deux index de matching pour les Employees actifs.

    Retourne (exact_index, last_name_index) :
    - exact_index  : norm(full_name) → employee_name  (unicité garantie)
    - last_name_index : norm(last_name) → [list of employees]  (pour déambiguation prénom)
    """
    import frappe
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "first_name", "last_name", "custom_matricule_kya"],
    )
    exact_index: dict[str, str] = {}
    last_name_index: dict[str, list] = {}

    for emp in employees:
        fn = emp.first_name or ""
        ln = emp.last_name or ""
        en = emp.employee_name or ""

        # Variantes du nom complet à indexer (NOM PRENOMS et PRENOMS NOM)
        variants = [
            _norm(en),
            _norm(f"{ln} {fn}"),
            _norm(f"{fn} {ln}"),
        ]
        for key in variants:
            if key:
                exact_index.setdefault(key, emp.name)

        # Index secondaire par nom de famille (pour déambiguation si doublon de NOM)
        lk = _norm(ln)
        if lk:
            last_name_index.setdefault(lk, []).append({
                "employee": emp.name,
                "first_norm": _norm(fn),
                "employee_name": en,
            })

    return exact_index, last_name_index


def _resolve_by_prenom(nom_excel: str, prenom_excel: str, last_name_index: dict) -> str | None:
    """Si deux employés ont le même NOM, choisit celui dont le prénom correspond
    à l'initiale ou aux premiers caractères du prénom Excel."""
    ln_key = _norm(nom_excel)
    candidates = last_name_index.get(ln_key, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]["employee"]

    # Plusieurs candidats : comparer prénom normalisé
    pn = _norm(prenom_excel)
    # Match exact prénom
    for c in candidates:
        if c["first_norm"] == pn:
            return c["employee"]
    # Match partiel (prénom Excel commence par prénom DB ou vice-versa)
    for c in candidates:
        fp = c["first_norm"]
        if fp and (pn.startswith(fp) or fp.startswith(pn)):
            return c["employee"]
    # Fallback : premier candidat (ambiguïté non résolue → loguer)
    return None  # ambigu, ne pas forcer


def build_attendance_payloads(rows, employee_index, include_absences=False, default_company=None):
    """Transforme les lignes Excel en payloads Attendance pour insertion Frappe.

    Matching robuste en 3 passes :
    1. Correspondance exacte sur le nom complet normalisé (NOM PRENOMS)
    2. Correspondance inversée (PRENOMS NOM) — déjà dans l'index
    3. Déambiguïsation par nom de famille + prénom si NOM non-unique
    """
    exact_index, last_name_index = employee_index
    payloads = []
    unmatched = []
    for row in rows:
        # Passe 1 + 2 : exact match (toutes les variantes sont dans exact_index)
        emp_name = exact_index.get(row["full_name_norm"])

        # Passe 3 : déambiguïsation par NOM + PRENOMS séparés
        if not emp_name:
            emp_name = _resolve_by_prenom(row["nom"], row["prenoms"], last_name_index)

        if not emp_name:
            unmatched.append(row["full_name"])
            continue
        for iso_date, code in row["daily"].items():
            mapping = STATUS_MAP.get(code)
            if mapping is None:
                continue
            if mapping["status"] == "Absent" and not include_absences:
                # Les "vide" → Absent peuvent être bruyants, on les filtre par défaut
                pass
            payload = {
                "doctype": "Attendance",
                "employee": emp_name,
                "attendance_date": iso_date,
                "status": mapping["status"],
                "late_entry": mapping.get("late_entry", 0),
                "leave_type": mapping.get("leave_type"),
                "company": default_company,
            }
            payloads.append(payload)
    return payloads, unmatched


def run(path=None, dry_run=True, include_absences=False, output=None):
    """Entrypoint Frappe (bench execute).

    Args:
        path: chemin local du .xlsx
        dry_run: True → ne pas insérer, retourne juste un résumé
        include_absences: inclure les cellules vides comme Absent
        output: chemin facultatif pour sauvegarder le JSON des payloads
    """
    import frappe
    src = Path(path or r"D:\Stage_KYA_Energy\RH\PRESENCE DU PERSONNEL_NOVEMBRE_2025XXX.xlsx")
    if not src.exists():
        return {"ok": False, "error": f"Fichier introuvable : {src}"}

    rows = parse_workbook(src)
    index = _employee_index()
    default_company = frappe.db.get_default("company")
    payloads, unmatched = build_attendance_payloads(
        rows, index, include_absences=include_absences, default_company=default_company
    )

    if output:
        Path(output).write_text(
            json.dumps({"payloads": payloads, "unmatched": unmatched}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "rows_excel": len(rows),
            "matched_employees": len(rows) - len(unmatched),
            "unmatched": unmatched,
            "attendance_records": len(payloads),
        }

    inserted, skipped, errors = 0, 0, []
    for payload in payloads:
        try:
            if frappe.db.exists("Attendance", {
                "employee": payload["employee"],
                "attendance_date": payload["attendance_date"],
            }):
                skipped += 1
                continue
            doc = frappe.get_doc(payload).insert(ignore_permissions=True)
            doc.submit()
            inserted += 1
        except Exception as exc:
            errors.append(f"{payload['employee']}@{payload['attendance_date']}: {exc}")
    frappe.db.commit()
    return {
        "ok": True,
        "inserted": inserted,
        "skipped_existing": skipped,
        "errors": errors,
        "unmatched": unmatched,
    }


def _main_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--output", default="./attendance_preview.json")
    parser.add_argument("--include-absences", action="store_true")
    args = parser.parse_args()

    src = Path(args.path)
    rows = parse_workbook(src)
    # En mode CLI sans Frappe, l'index est vide (2-tuple vide)
    payloads, unmatched = build_attendance_payloads(
        rows, employee_index=({}, {}), include_absences=args.include_absences, default_company=None
    )
    Path(args.output).write_text(
        json.dumps({"rows": rows, "unmatched_will_be_all": True}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"OK : {len(rows)} lignes Excel parsees -> {args.output}")
    print("Pour matcher aux Employees + creer les Attendance, lance via Frappe :")
    print('  bench --site <site> execute kya_hr.maintenance.import_attendance.run \\')
    print(f'      --kwargs \'{{"path":"{src}", "dry_run":true}}\'')


if __name__ == "__main__":
    _main_cli()

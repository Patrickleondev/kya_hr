"""KYA Imports RH — endpoints d'import Excel pour la RH.

Architecture :
  1. RH télécharge un template Excel via download_template(type_import=...)
  2. RH remplit puis upload via Frappe File API
  3. Frontend appelle upload_and_parse(file_url, type_import, periode)
     → crée un KYA Import RH (statut=Parsé), stocke rows_json + log
  4. RH revue le résultat, puis appelle commit_import(name)
     → écrit dans le doctype cible (Attendance, etc.) (statut=Importé)

Pour la session 2026-05-16, SEUL `Presence` (VENTILATION matrix) est
totalement implémenté. Les 4 autres (Solde / Planning / Fiche Gestion /
Gestion Equipe) auront leur parser en next session — endpoints renvoient
NotImplementedError pour l'instant.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils.file_manager import get_file_path
from frappe.utils import now_datetime


# ─── STATUT MAP (codes Excel → Attendance.status) ────────────────────────────
STATUS_MAP = {
    "P": "Present",
    "PR": "Present",
    "PRESENT": "Present",
    "A": "Absent",
    "ABSENT": "Absent",
    "RM": "On Leave",        # Repos Médical
    "REPOS": "On Leave",
    "M": "Work From Home",   # Mission
    "MISSION": "Work From Home",
    "PC": "On Leave",        # Permission/Congé
    "C": "On Leave",
    "CONGE": "On Leave",
    "HD": "Half Day",
    "DEMI": "Half Day",
}


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _norm(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip()).lower()


def _find_employee_by_matricule(matricule):
    """Cherche un Employee par matricule. Tente employee_number, puis name custom."""
    if matricule is None:
        return None
    try:
        mat = str(int(float(matricule))).strip()
    except (TypeError, ValueError):
        mat = str(matricule).strip()
    if not mat:
        return None

    # Tente employee_number
    emp = frappe.db.get_value("Employee", {"employee_number": mat, "status": "Active"}, "name")
    if emp:
        return emp
    # Tente employee_number sans 0-padding
    emp = frappe.db.get_value("Employee", {"employee_number": mat.lstrip("0"), "status": "Active"}, "name")
    if emp:
        return emp
    # Tente name commençant par le matricule
    emp = frappe.db.get_value("Employee", {"name": ["like", f"%{mat}%"], "status": "Active"}, "name")
    return emp


def _parse_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, (date, datetime)):
        return v if isinstance(v, date) and not isinstance(v, datetime) else v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ─── PARSER PRESENCE (sheet VENTILATION matrice employee × jour) ─────────────

def _parse_presence_ventilation(file_path):
    """Parse la sheet VENTILATION (matrice mensuelle KYA).

    Layout attendu :
      - Lignes 1-9 : letterhead KYA (skip)
      - Une ligne contient les dates en cellules (cherche entre lignes 8 et 14)
      - Première colonne data : matricule (int)
      - Colonnes suivantes : statuts journaliers (P/A/RM/M/PC/.)

    Retourne : list de dicts {matricule, employee, employee_name, date, status_code, status}
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        frappe.throw(_("openpyxl non installé sur le site."))

    wb = load_workbook(file_path, data_only=True, read_only=False)

    # Chercher la sheet VENTILATION (ou par défaut première)
    sheet_name = None
    for sn in wb.sheetnames:
        if "ventilation" in sn.lower():
            sheet_name = sn
            break
    if not sheet_name:
        sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]

    # Trouver la ligne des dates : itère lignes 5-15, cherche cellule qui est un date/datetime
    date_row_idx = None
    cols_to_date = {}
    for r in range(5, min(20, ws.max_row + 1)):
        dates_in_row = {}
        for c in range(1, min(ws.max_column + 1, 60)):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, (date, datetime)):
                dates_in_row[c] = v if isinstance(v, date) and not isinstance(v, datetime) else v.date()
        if len(dates_in_row) >= 3:  # au moins 3 dates → c'est la ligne d'en-tête
            date_row_idx = r
            cols_to_date = dates_in_row
            break

    if not date_row_idx:
        return [], ["Aucune ligne d'en-tête de dates détectée (cherché lignes 5-19)."]

    # Trouver la première ligne de données : matricule entier en col 1 ou 2
    data_start_row = None
    mat_col = 1
    for r in range(date_row_idx + 1, min(date_row_idx + 10, ws.max_row + 1)):
        for c in (1, 2):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, (int, float)) and 0 < v < 100000:
                data_start_row = r
                mat_col = c
                break
        if data_start_row:
            break

    if not data_start_row:
        return [], [f"Aucune ligne de données détectée après ligne {date_row_idx}."]

    # Trouver les colonnes nom/prénom (juste après mat_col)
    name_col = mat_col + 1
    prenom_col = mat_col + 2

    rows = []
    errors = []
    for r in range(data_start_row, ws.max_row + 1):
        matricule = ws.cell(row=r, column=mat_col).value
        if matricule is None or not isinstance(matricule, (int, float)):
            continue
        try:
            mat_str = str(int(matricule))
        except (TypeError, ValueError):
            continue

        nom = ws.cell(row=r, column=name_col).value or ""
        prenom = ws.cell(row=r, column=prenom_col).value or ""
        employee_name = f"{str(nom).strip()} {str(prenom).strip()}".strip()

        emp = _find_employee_by_matricule(mat_str)
        if not emp:
            errors.append(f"L{r} : Employé matricule={mat_str} ({employee_name}) introuvable en DB")
            continue

        # Pour chaque colonne de date, lire le statut
        for c, att_date in cols_to_date.items():
            v = ws.cell(row=r, column=c).value
            code = _norm(v).upper() if v is not None else ""
            if not code or code == ".":
                continue
            status = STATUS_MAP.get(code)
            if not status:
                # Code inconnu — on log mais on continue
                errors.append(f"L{r} {att_date} : code statut inconnu {code!r} (skip)")
                continue
            rows.append({
                "matricule": mat_str,
                "employee": emp,
                "employee_name": employee_name,
                "date": att_date.isoformat() if isinstance(att_date, date) else str(att_date),
                "status_code": code,
                "status": status,
            })

    return rows, errors


# ─── ENDPOINTS PUBLICS ───────────────────────────────────────────────────────

@frappe.whitelist()
def upload_and_parse(file_url, type_import, periode):
    """Upload + parse + crée un KYA Import RH avec statut=Parsé.

    Args :
      file_url : URL du fichier uploadé (/files/... ou /private/...)
      type_import : Presence | Solde Conges | Planning Conges | Fiche Gestion Conges | Gestion Equipe
      periode : libellé période (ex 'Novembre 2025')

    Returns : { name, total_lignes, total_erreurs, errors_preview }
    """
    if not frappe.has_permission("KYA Import RH", "create"):
        frappe.throw(_("Permission refusée"), frappe.PermissionError)

    path = get_file_path(file_url) if (file_url.startswith("/files/") or file_url.startswith("/private/")) else file_url
    if not os.path.isfile(path):
        frappe.throw(_("Fichier introuvable : {0}").format(file_url))

    if type_import == "Presence":
        rows, errors = _parse_presence_ventilation(path)
    else:
        # 4 autres types — à implémenter
        frappe.throw(_("Type d'import non encore implémenté : {0}. Voir ROADMAP_IMPORTS_RH.md").format(type_import))

    # Créer le doc KYA Import RH
    doc = frappe.new_doc("KYA Import RH")
    doc.type_import = type_import
    doc.periode = periode
    doc.fichier_source = file_url
    doc.statut = "Parsé"
    doc.imported_by = frappe.session.user
    doc.date_import = now_datetime()
    doc.total_lignes = len(rows)
    doc.total_erreurs = len(errors)
    doc.log_traces = "\n".join(errors[:200])
    doc.rows_json = json.dumps(rows, ensure_ascii=False)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "total_lignes": doc.total_lignes,
        "total_erreurs": doc.total_erreurs,
        "errors_preview": errors[:10],
        "statut": doc.statut,
    }


@frappe.whitelist()
def commit_import(name):
    """Écrit les rows parsés dans les doctypes cibles (Attendance pour Presence).

    Idempotent : un Attendance existant pour le même (employee, date) est mis à jour.
    """
    doc = frappe.get_doc("KYA Import RH", name)
    if doc.statut == "Importé":
        return {"already_imported": True, "name": name}
    if not doc.rows_json:
        frappe.throw(_("Aucune donnée parsée — relancer upload_and_parse"))

    rows = json.loads(doc.rows_json)
    inserted, updated, skipped = 0, 0, 0
    extra_errors = []

    if doc.type_import == "Presence":
        for r in rows:
            try:
                emp = r["employee"]
                att_date = _parse_date(r["date"])
                status = r["status"]
                if not att_date:
                    skipped += 1
                    continue
                existing = frappe.db.get_value(
                    "Attendance",
                    {"employee": emp, "attendance_date": att_date, "docstatus": ["<", 2]},
                    "name",
                )
                if existing:
                    a = frappe.get_doc("Attendance", existing)
                    a.status = status
                    a.save(ignore_permissions=True)
                    updated += 1
                else:
                    a = frappe.new_doc("Attendance")
                    a.employee = emp
                    a.attendance_date = att_date
                    a.status = status
                    a.company = (
                        frappe.db.get_value("Employee", emp, "company")
                        or frappe.defaults.get_user_default("Company")
                    )
                    a.insert(ignore_permissions=True)
                    try:
                        a.submit()
                    except Exception:
                        pass
                    inserted += 1
            except Exception as e:
                extra_errors.append(f"{r.get('employee_name','?')} {r.get('date','?')} : {e}")
                skipped += 1
    else:
        frappe.throw(_("Commit non implémenté pour type : {0}").format(doc.type_import))

    # Mise à jour du doc
    doc.statut = "Importé"
    doc.total_inseres = inserted
    doc.total_skipped = skipped
    if extra_errors:
        existing = doc.log_traces or ""
        doc.log_traces = (existing + "\n=== Erreurs au commit ===\n" + "\n".join(extra_errors[:100])).strip()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": name,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "extra_errors": extra_errors[:10],
        "statut": doc.statut,
    }


# ─── TEMPLATE DOWNLOAD ───────────────────────────────────────────────────────

@frappe.whitelist()
def download_template(type_import):
    """Retourne un modèle Excel pré-formaté pour le type d'import demandé.

    Returns : { filename, data (base64), mime }
    """
    if type_import == "Presence":
        return _build_template_presence()
    else:
        frappe.throw(_("Template non implémenté pour : {0}").format(type_import))


def _build_template_presence():
    """Modèle Présence — format MATRICE (1 ligne par employé × 1 colonne par jour).

    Reproduit la structure du fichier KYA officiel : letterhead minimale +
    légende des codes + 31 colonnes de jours.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        frappe.throw(_("openpyxl non installé."))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "VENTILATION"

    # Letterhead minimaliste (lignes 1-6)
    ws.cell(row=1, column=1, value="KYA-Energy Group — Présences mensuelles").font = Font(bold=True, size=14, color="1F4E78")
    ws.cell(row=2, column=1, value="Référence : RH-ENG-04-V01")
    ws.cell(row=3, column=1, value="Date : à compléter")
    ws.cell(row=5, column=1, value="Légende :")
    ws.cell(row=5, column=2, value="P = Présent  |  A = Absent  |  RM = Repos Médical  |  M = Mission  |  PC = Permission/Congé  |  . = Weekend/Férié")
    ws.cell(row=5, column=2).font = Font(italic=True, size=9)

    # Ligne 8 : en-tête colonnes
    headers_row = 8
    ws.cell(row=headers_row, column=1, value="Matricule").font = Font(bold=True, color="FFFFFF")
    ws.cell(row=headers_row, column=2, value="Nom").font = Font(bold=True, color="FFFFFF")
    ws.cell(row=headers_row, column=3, value="Prénom").font = Font(bold=True, color="FFFFFF")
    ws.cell(row=headers_row, column=4, value="Fonction").font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F4E78")
    for c in range(1, 5):
        ws.cell(row=headers_row, column=c).fill = head_fill

    # 31 colonnes de jours (à partir col 5)
    from datetime import date as date_cls
    today = date_cls.today()
    base = date_cls(today.year, today.month, 1)
    for d in range(1, 32):
        try:
            day_date = date_cls(today.year, today.month, d)
        except ValueError:
            break
        cell = ws.cell(row=headers_row, column=4 + d, value=day_date)
        cell.fill = head_fill
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")
        cell.number_format = "dd/mm"

    # Exemple de ligne (row 9)
    ws.cell(row=9, column=1, value=18)
    ws.cell(row=9, column=2, value="EXEMPLE")
    ws.cell(row=9, column=3, value="Prénom")
    ws.cell(row=9, column=4, value="POSTE")
    for d in range(1, 6):
        ws.cell(row=9, column=4 + d, value="P")

    # Sheet Aide
    aide = wb.create_sheet("Aide")
    aide.append(["Champ", "Explication"])
    aide.append(["Matricule", "Numéro matricule de l'employé (Employee.employee_number)"])
    aide.append(["Nom + Prénom", "Pour affichage uniquement, l'employé est trouvé par matricule"])
    aide.append(["Colonnes jours", "Une lettre par jour : P / A / RM / M / PC. Vide ou '.' = weekend ou férié (ignoré)"])
    aide.append(["Letterhead", "Lignes 1-7 réservées au letterhead KYA. L'import skip ces lignes."])
    aide.append(["Ligne 8", "En-tête colonnes : Matricule, Nom, Prénom, Fonction, puis dates (1 par jour)"])
    aide.append(["Données", "À partir de la ligne 9"])
    for col, w in (("A", 20), ("B", 70)):
        aide.column_dimensions[col].width = w
    aide["A1"].font = Font(bold=True, color="FFFFFF")
    aide["A1"].fill = head_fill
    aide["B1"].font = Font(bold=True, color="FFFFFF")
    aide["B1"].fill = head_fill

    # Largeurs colonnes
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 24
    ws.column_dimensions["D"].width = 26
    for d in range(1, 32):
        col_letter = openpyxl.utils.get_column_letter(4 + d)
        ws.column_dimensions[col_letter].width = 6

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return {
        "filename": f"modele_import_presence_{today.year}_{today.month:02d}.xlsx",
        "data": base64.b64encode(buf.read()).decode(),
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

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


# ─── PARSER SOLDE CONGES ─────────────────────────────────────────────────────

def _parse_solde_conges(file_path):
    """Parse 'SOLDE CONGES PERSONNEL 2025XXX.xlsx'.

    Layout :
      - Row 1 : titre 'ETAT DU SOLDE DE...'
      - Row 2 : headers principaux (N° Ord, Nom & Prénoms, Date embauche,
        Date référence, Ancienneté, Total jours, Jours pris, Solde initial,
        Périodes de jouissance)
      - Row 3 : sub-headers (2023, 2024, CONGE ANTICIPE C, CONGE INDIVIDUEL)
      - Row 4+ : data
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        frappe.throw(_("openpyxl non installé."))

    wb = load_workbook(file_path, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]

    rows = []
    errors = []
    # Data starts after the 3 header rows
    for r in range(4, ws.max_row + 1):
        n_ord = ws.cell(row=r, column=1).value
        nom_prenoms = ws.cell(row=r, column=2).value
        if not n_ord and not nom_prenoms:
            continue
        try:
            n_ord_i = int(n_ord) if n_ord is not None else None
        except (TypeError, ValueError):
            continue

        date_embauche = ws.cell(row=r, column=3).value
        date_ref = ws.cell(row=r, column=4).value
        anciennete = ws.cell(row=r, column=5).value
        total_jours = ws.cell(row=r, column=6).value
        jours_pris = ws.cell(row=r, column=7).value
        solde_initial = ws.cell(row=r, column=8).value

        # Lookup employee (by name only — matricule pas dans la 1re colonne)
        name = str(nom_prenoms or "").strip()
        emp = None
        if name:
            parts = name.split()
            if parts:
                emp = frappe.db.get_value("Employee", {"employee_name": ["like", f"%{parts[0]}%"], "status": "Active"}, "name")

        rows.append({
            "n_ordre": n_ord_i,
            "nom_prenoms": name,
            "employee": emp,
            "date_embauche": _date_iso(date_embauche),
            "date_reference": _date_iso(date_ref),
            "anciennete_mois": _safe_float(anciennete),
            "total_jours_acquis": _safe_float(total_jours),
            "jours_pris": _safe_float(jours_pris),
            "solde_initial": _safe_float(solde_initial),
            "jouissance_2023": _safe_float(ws.cell(row=r, column=9).value),
            "jouissance_2024": _safe_float(ws.cell(row=r, column=10).value),
            "conge_anticipe": _safe_float(ws.cell(row=r, column=11).value),
            "conge_individuel": _safe_float(ws.cell(row=r, column=12).value),
        })
        if not emp and name:
            errors.append(f"L{r} : Employé '{name}' introuvable (lookup par prénom)")

    return rows, errors


# ─── PARSER PLANNING CONGES ──────────────────────────────────────────────────

def _parse_planning_conges(file_path):
    """Parse 'PLANNING DES CONGÉS ANNUELS 2025XXXX.xlsx'.

    Layout (sheet 'PLANNING GLOBAL') :
      - Rows 1-13 : letterhead KYA (logo, RH-ENG-21-V01, signatures Rédigé/Vérifié/Validé)
      - Row 14 : headers (NOM, PRENOMS, FONCTION, PROPOSITIONS VALIDÉES, Dates, NBRE JOURS)
      - Row 15+ : data
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        frappe.throw(_("openpyxl non installé."))

    wb = load_workbook(file_path, data_only=True, read_only=True)
    # Cherche la sheet PLANNING GLOBAL ou la première
    sheet_name = None
    for sn in wb.sheetnames:
        if "planning" in sn.lower():
            sheet_name = sn
            break
    if not sheet_name:
        sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]

    # Détecte la ligne d'en-tête : cherche 'NOM' en col 1 entre R10 et R20
    header_row = None
    for r in range(10, min(25, ws.max_row + 1)):
        v = ws.cell(row=r, column=1).value
        if v and "nom" in str(v).lower():
            header_row = r
            break
    if not header_row:
        return [], ["Aucune ligne d'en-tête (cherché 'NOM' en col 1 entre R10-R24)"]

    rows = []
    errors = []
    for r in range(header_row + 1, ws.max_row + 1):
        nom = ws.cell(row=r, column=1).value
        if not nom:
            continue
        prenoms = ws.cell(row=r, column=2).value
        fonction = ws.cell(row=r, column=3).value
        propositions = ws.cell(row=r, column=4).value
        dates = ws.cell(row=r, column=5).value
        nbre_jours = ws.cell(row=r, column=6).value

        name = f"{str(nom).strip()} {str(prenoms or '').strip()}".strip()
        emp = frappe.db.get_value("Employee", {"employee_name": ["like", f"%{str(nom).strip()}%"], "status": "Active"}, "name")

        rows.append({
            "nom": str(nom).strip(),
            "prenoms": str(prenoms or "").strip(),
            "employee_name_recherche": name,
            "employee": emp,
            "fonction": str(fonction or "").strip(),
            "propositions": str(propositions or "").strip(),
            "dates": str(dates or "").strip(),
            "nbre_jours": _safe_float(nbre_jours),
        })
        if not emp:
            errors.append(f"L{r} : Employé '{name}' introuvable")

    return rows, errors


# ─── PARSER FICHE GESTION CONGES ─────────────────────────────────────────────

def _parse_fiche_gestion_conges(file_path):
    """Parse 'FICHE DE GESTION DES CONGES ANNUELS 2026.xlsx'.

    Layout :
      - Row 2 : titre 'FICHE DE GESTION...'
      - Row 3 : headers ligne 1 (Nbre Jours Acquis, Congés anticipés, ...)
      - Row 4 : headers ligne 2 (N° Ord, Nom, Prénoms, Date départ 1, ...)
      - Row 5+ : data, plusieurs dates de départ possibles par employé
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        frappe.throw(_("openpyxl non installé."))

    wb = load_workbook(file_path, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]

    rows = []
    errors = []
    for r in range(5, ws.max_row + 1):
        n_ord = ws.cell(row=r, column=1).value
        nom = ws.cell(row=r, column=2).value
        prenoms = ws.cell(row=r, column=3).value
        if not nom and not n_ord:
            continue
        try:
            n_ord_i = int(n_ord) if n_ord is not None else None
        except (TypeError, ValueError):
            continue

        name = f"{str(nom or '').strip()} {str(prenoms or '').strip()}".strip()
        emp = frappe.db.get_value("Employee", {"employee_name": ["like", f"%{str(nom or '').strip()}%"], "status": "Active"}, "name")

        # Champs depart 1 (cols 9-11) + depart 2 (cols 12-14)
        depart_1 = {
            "date_depart": _date_iso(ws.cell(row=r, column=9).value),
            "date_reprise": _date_iso(ws.cell(row=r, column=10).value),
            "nb_jours": _safe_float(ws.cell(row=r, column=11).value),
        }
        depart_2 = {
            "date_depart": _date_iso(ws.cell(row=r, column=13).value),
            "date_reprise": _date_iso(ws.cell(row=r, column=14).value),
            "nb_jours": _safe_float(ws.cell(row=r, column=15).value),
        }

        rows.append({
            "n_ordre": n_ord_i,
            "nom": str(nom or "").strip(),
            "prenoms": str(prenoms or "").strip(),
            "employee": emp,
            "nbre_jours_acquis": _safe_float(ws.cell(row=r, column=4).value),
            "conges_anticipes": _safe_float(ws.cell(row=r, column=5).value),
            "nbre_jours_restants": _safe_float(ws.cell(row=r, column=6).value),
            "duree_conge_general": _safe_float(ws.cell(row=r, column=7).value),
            "solde_fin_janvier": _safe_float(ws.cell(row=r, column=8).value),
            "departs": [d for d in (depart_1, depart_2) if d["date_depart"]],
        })
        if not emp and nom:
            errors.append(f"L{r} : Employé '{name}' introuvable")

    return rows, errors


# ─── PARSER GESTION EQUIPE ───────────────────────────────────────────────────

def _parse_gestion_equipe(file_path):
    """Parse template Gestion Équipe (format défini par KYA — pas de fichier source).

    Layout attendu :
      - Sheet 'Equipes' : nom_equipe, chef_matricule, description, date_creation
      - Sheet 'Membres' : nom_equipe, matricule_membre, role
      - Sheet 'Taches' : nom_equipe, titre, description, date_debut, date_fin, taux_effectif
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        frappe.throw(_("openpyxl non installé."))

    wb = load_workbook(file_path, data_only=True, read_only=True)
    rows = []
    errors = []

    # Sheet Equipes
    if "Equipes" in wb.sheetnames:
        ws = wb["Equipes"]
        for r in range(2, ws.max_row + 1):
            nom = ws.cell(row=r, column=1).value
            if not nom:
                continue
            chef_mat = ws.cell(row=r, column=2).value
            chef_emp = _find_employee_by_matricule(chef_mat) if chef_mat else None
            rows.append({
                "type": "equipe",
                "nom_equipe": str(nom).strip(),
                "chef_matricule": str(chef_mat).strip() if chef_mat else "",
                "chef_employee": chef_emp,
                "description": str(ws.cell(row=r, column=3).value or "").strip(),
                "date_creation": _date_iso(ws.cell(row=r, column=4).value),
            })
            if chef_mat and not chef_emp:
                errors.append(f"Equipes L{r} : chef matricule={chef_mat} introuvable")

    # Sheet Membres
    if "Membres" in wb.sheetnames:
        ws = wb["Membres"]
        for r in range(2, ws.max_row + 1):
            equipe = ws.cell(row=r, column=1).value
            matricule = ws.cell(row=r, column=2).value
            if not equipe or matricule is None:
                continue
            emp = _find_employee_by_matricule(matricule)
            rows.append({
                "type": "membre",
                "nom_equipe": str(equipe).strip(),
                "matricule": str(matricule).strip(),
                "employee": emp,
                "role": str(ws.cell(row=r, column=3).value or "").strip(),
            })
            if not emp:
                errors.append(f"Membres L{r} : employé matricule={matricule} introuvable")

    # Sheet Taches
    if "Taches" in wb.sheetnames:
        ws = wb["Taches"]
        for r in range(2, ws.max_row + 1):
            equipe = ws.cell(row=r, column=1).value
            titre = ws.cell(row=r, column=2).value
            if not equipe or not titre:
                continue
            rows.append({
                "type": "tache",
                "nom_equipe": str(equipe).strip(),
                "titre": str(titre).strip(),
                "description": str(ws.cell(row=r, column=3).value or "").strip(),
                "date_debut": _date_iso(ws.cell(row=r, column=4).value),
                "date_fin": _date_iso(ws.cell(row=r, column=5).value),
                "taux_effectif": _safe_float(ws.cell(row=r, column=6).value),
            })

    return rows, errors


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _safe_float(v):
    if v is None or v == "" or str(v).strip() in ("#REF!", "#N/A", "#DIV/0!"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _date_iso(v):
    d = _parse_date(v)
    return d.isoformat() if d else None


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
    elif type_import == "Solde Conges":
        rows, errors = _parse_solde_conges(path)
    elif type_import == "Planning Conges":
        rows, errors = _parse_planning_conges(path)
    elif type_import == "Fiche Gestion Conges":
        rows, errors = _parse_fiche_gestion_conges(path)
    elif type_import == "Gestion Equipe":
        rows, errors = _parse_gestion_equipe(path)
    else:
        frappe.throw(_("Type d'import inconnu : {0}").format(type_import))

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
    elif doc.type_import == "Solde Conges":
        # Ecrit dans Leave Allocation (HRMS) si employee trouvé
        leave_type = frappe.db.get_value("Leave Type", {"name": ["like", "%Congé Annuel%"]}, "name") \
                     or frappe.db.get_value("Leave Type", {"name": ["like", "%Annual%"]}, "name") \
                     or "Annual Leave"
        for r in rows:
            try:
                emp = r.get("employee")
                if not emp:
                    skipped += 1
                    continue
                total = r.get("total_jours_acquis") or r.get("solde_initial") or 0
                if not total:
                    skipped += 1
                    continue
                existing = frappe.db.get_value("Leave Allocation",
                    {"employee": emp, "leave_type": leave_type,
                     "from_date": ["like", "2025%"], "docstatus": ["<", 2]}, "name")
                if existing:
                    a = frappe.get_doc("Leave Allocation", existing)
                    a.new_leaves_allocated = total
                    a.save(ignore_permissions=True)
                    updated += 1
                else:
                    a = frappe.new_doc("Leave Allocation")
                    a.employee = emp
                    a.leave_type = leave_type
                    a.from_date = "2025-01-01"
                    a.to_date = "2025-12-31"
                    a.new_leaves_allocated = total
                    a.insert(ignore_permissions=True)
                    try: a.submit()
                    except Exception: pass
                    inserted += 1
            except Exception as e:
                extra_errors.append(f"{r.get('nom_prenoms','?')} : {e}")
                skipped += 1

    elif doc.type_import == "Planning Conges":
        # Ecrit dans Planning Conge (custom KYA existant)
        for r in rows:
            try:
                emp = r.get("employee")
                if not emp:
                    skipped += 1
                    continue
                pc = frappe.new_doc("Planning Conge")
                pc.employee = emp
                pc.nb_jours = r.get("nbre_jours") or 0
                pc.objet = f"Import planning - {r.get('dates','')}"
                # workflow_state = Validé (planning officiel)
                if hasattr(pc, "workflow_state"):
                    pc.workflow_state = "Validé"
                pc.insert(ignore_permissions=True)
                inserted += 1
            except Exception as e:
                extra_errors.append(f"{r.get('nom','?')} : {e}")
                skipped += 1

    elif doc.type_import == "Fiche Gestion Conges":
        # Pour chaque employé, créer 1 Leave Allocation + N Leave Application par départ
        leave_type = frappe.db.get_value("Leave Type", {"name": ["like", "%Congé Annuel%"]}, "name") \
                     or frappe.db.get_value("Leave Type", {"name": ["like", "%Annual%"]}, "name") \
                     or "Annual Leave"
        for r in rows:
            try:
                emp = r.get("employee")
                if not emp:
                    skipped += 1
                    continue
                # Leave Allocation pour l'année
                total = r.get("nbre_jours_acquis") or 0
                if total:
                    a = frappe.new_doc("Leave Allocation")
                    a.employee = emp
                    a.leave_type = leave_type
                    a.from_date = "2026-01-01"
                    a.to_date = "2026-12-31"
                    a.new_leaves_allocated = total
                    a.insert(ignore_permissions=True)
                    try: a.submit()
                    except Exception: pass
                    inserted += 1
                # Leave Applications pour chaque départ
                for dep in (r.get("departs") or []):
                    if not dep.get("date_depart"):
                        continue
                    la = frappe.new_doc("Leave Application")
                    la.employee = emp
                    la.leave_type = leave_type
                    la.from_date = dep["date_depart"]
                    la.to_date = dep["date_reprise"] or dep["date_depart"]
                    la.total_leave_days = dep.get("nb_jours") or 0
                    la.description = "Import Fiche Gestion Congés 2026"
                    la.status = "Approved"
                    la.insert(ignore_permissions=True)
                    inserted += 1
            except Exception as e:
                extra_errors.append(f"{r.get('nom','?')} : {e}")
                skipped += 1

    elif doc.type_import == "Gestion Equipe":
        # Ecrit dans Equipe KYA + Tache Equipe
        equipes_by_name = {}
        # 1. Créer les équipes
        for r in [x for x in rows if x.get("type") == "equipe"]:
            try:
                if not frappe.db.exists("Equipe KYA", r["nom_equipe"]):
                    eq = frappe.new_doc("Equipe KYA")
                    eq.nom_equipe = r["nom_equipe"]
                    if r.get("chef_employee"):
                        eq.chef_equipe = r["chef_employee"]
                    if r.get("description"):
                        eq.description = r["description"]
                    eq.insert(ignore_permissions=True)
                    inserted += 1
                    equipes_by_name[r["nom_equipe"]] = eq.name
                else:
                    equipes_by_name[r["nom_equipe"]] = r["nom_equipe"]
                    updated += 1
            except Exception as e:
                extra_errors.append(f"Equipe {r.get('nom_equipe')} : {e}")
                skipped += 1
        # 2. Ajouter membres (table child sur Equipe KYA)
        for r in [x for x in rows if x.get("type") == "membre"]:
            try:
                eq_name = equipes_by_name.get(r["nom_equipe"]) or r["nom_equipe"]
                if not r.get("employee") or not frappe.db.exists("Equipe KYA", eq_name):
                    skipped += 1
                    continue
                eq = frappe.get_doc("Equipe KYA", eq_name)
                eq.append("membres", {"employee": r["employee"], "role": r.get("role") or "Membre"})
                eq.save(ignore_permissions=True)
                inserted += 1
            except Exception as e:
                extra_errors.append(f"Membre {r.get('matricule')} : {e}")
                skipped += 1
        # 3. Créer les tâches
        for r in [x for x in rows if x.get("type") == "tache"]:
            try:
                eq_name = equipes_by_name.get(r["nom_equipe"]) or r["nom_equipe"]
                if not frappe.db.exists("Equipe KYA", eq_name):
                    skipped += 1
                    continue
                t = frappe.new_doc("Tache Equipe")
                t.equipe = eq_name
                t.titre = r["titre"]
                t.description = r.get("description") or ""
                if r.get("date_debut"): t.date_debut = r["date_debut"]
                if r.get("date_fin"): t.date_fin = r["date_fin"]
                if r.get("taux_effectif") is not None: t.taux_effectif = r["taux_effectif"]
                t.insert(ignore_permissions=True)
                inserted += 1
            except Exception as e:
                extra_errors.append(f"Tache {r.get('titre')} : {e}")
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
def download_template(type_import, as_json=0):
    """Modèle Excel pré-formaté pour le type d'import demandé.

    Par défaut (clic direct sur un lien / raccourci) : déclenche un VRAI
    téléchargement de fichier .xlsx (frappe.local.response binaire), sinon le
    navigateur affichait le base64 brut.
    Avec `as_json=1` : renvoie { filename, data (base64), mime } pour un appel JS.
    """
    builders = {
        "Presence": _build_template_presence,
        "Solde Conges": _build_template_solde_conges,
        "Planning Conges": _build_template_planning_conges,
        "Fiche Gestion Conges": _build_template_fiche_gestion_conges,
        "Gestion Equipe": _build_template_gestion_equipe,
    }
    builder = builders.get(type_import)
    if not builder:
        frappe.throw(_("Type d'import inconnu : {0}").format(type_import))

    result = builder()  # { filename, data (base64), mime }
    if frappe.utils.cint(as_json):
        return result

    import base64
    frappe.local.response.filename = result["filename"]
    frappe.local.response.filecontent = base64.b64decode(result["data"])
    frappe.local.response.type = "binary"


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


# ─── HELPER pour construire un template Excel simple ────────────────────────

def _build_simple_template(sheet_name, headers, examples, aide_lines, filename):
    """Génère un xlsx avec :
      - Sheet `sheet_name` : 1 ligne d'en-tête KYA, 1 ligne vide, headers en bleu, examples
      - Sheet 'Aide' : explications colonne par colonne
    Retourne le dict {filename, data, mime}.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name

    head_fill = PatternFill("solid", fgColor="1F4E78")
    head_font = Font(color="FFFFFF", bold=True)

    # Letterhead minimal
    ws.cell(row=1, column=1, value=f"KYA-Energy Group — {sheet_name}").font = Font(bold=True, size=14, color="1F4E78")
    ws.cell(row=2, column=1, value="Renseigner les données à partir de la ligne 5. Voir 'Aide' pour les colonnes.").font = Font(italic=True, size=9)

    # Headers row 4
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.fill = head_fill
        c.font = head_font
        c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = max(14, len(h) + 2)

    # Examples
    for ri, row in enumerate(examples, 5):
        for ci, val in enumerate(row, 1):
            ws.cell(row=ri, column=ci, value=val)

    # Aide
    aide = wb.create_sheet("Aide")
    aide.append(["Colonne", "Explication"])
    for c in aide[1]:
        c.fill = head_fill
        c.font = head_font
    for line in aide_lines:
        aide.append(line)
    aide.column_dimensions["A"].width = 24
    aide.column_dimensions["B"].width = 70

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return {
        "filename": filename,
        "data": base64.b64encode(buf.read()).decode(),
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }


def _build_template_solde_conges():
    headers = ["N° Ord", "Nom & Prénoms", "Date d'embauche", "Date de référence",
               "Ancienneté (mois)", "Total jours acquis", "Jours pris", "Solde initial",
               "Jouissance 2023", "Jouissance 2024", "Congé Anticipé", "Congé Individuel"]
    examples = [
        [1, "AZOUMAH Yao Ketowoglo", "2016-01-02", "2025-12-31", 118, 295, 237.5, 57.5, 7, 15, 7, 0],
        [2, "LAWSON Avla Kossi", "2016-05-02", "2025-12-31", 114, 285, 190, 95, 22, 30, 7, 15],
    ]
    aide = [
        ["N° Ord", "Numéro d'ordre"],
        ["Nom & Prénoms", "Nom complet de l'employé (utilisé pour lookup en DB)"],
        ["Date d'embauche", "Format YYYY-MM-DD ou DD/MM/YYYY"],
        ["Ancienneté", "En mois (calculée à la date de référence)"],
        ["Total jours acquis", "Calculé selon ancienneté (ex: 2.5 jours/mois)"],
        ["Solde initial", "Jours non utilisés au 1er janvier"],
        ["Jouissance 2023/2024", "Jours pris ces années-là (pour historique)"],
        ["Congé Anticipé", "Jours pris en avance sur l'année courante"],
        ["Congé Individuel", "Jours hors congé annuel standard"],
        ["", ""],
        ["Note", "Les 3 premières lignes (1-3) sont réservées au letterhead. Les headers sont en ligne 4. Données à partir de la ligne 5."],
    ]
    return _build_simple_template("Solde Congés", headers, examples, aide, "modele_import_solde_conges.xlsx")


def _build_template_planning_conges():
    headers = ["NOM", "PRENOMS", "FONCTION", "PROPOSITIONS VALIDÉES", "DATES", "NBRE JOURS"]
    examples = [
        ["AZOUMAH", "Yao Ketowoglo", "DIRECTEUR GENERAL", "Du 07/05 au 20/05", "13", 13],
        ["LAWSON", "Avla Kossi", "DAF", "Du 20/04 au 27/04", "7", 7],
    ]
    aide = [
        ["NOM", "Nom de famille (lookup employé)"],
        ["PRENOMS", "Prénoms"],
        ["FONCTION", "Poste actuel"],
        ["PROPOSITIONS VALIDÉES", "Texte libre décrivant la période"],
        ["DATES", "Détail des dates (texte libre)"],
        ["NBRE JOURS", "Nombre de jours de congé"],
        ["", ""],
        ["Note", "À l'import : skip lignes 1-13 (letterhead), headers ligne 14, données à partir ligne 15. Ce template simplifié les met en ligne 4."],
    ]
    return _build_simple_template("PLANNING GLOBAL", headers, examples, aide, "modele_import_planning_conges.xlsx")


def _build_template_fiche_gestion_conges():
    headers = ["N° Ord", "Nom", "Prénoms", "Nbre Jours Acquis", "Congés anticipés",
               "Nbre Jours Restants", "Durée congé général", "Solde fin janvier",
               "Date départ 1", "Date reprise 1", "Nb jours départ 1",
               "Solde 1",
               "Date départ 2", "Date reprise 2", "Nb jours départ 2"]
    examples = [
        [1, "AZOUMAH", "Yao Ketowoglo", 30, 7, 23, 0, 23, "2026-05-07", "2026-05-20", 13, 10, "", "", ""],
        [2, "ZATO", "Yamine", 43, 7, 36, 16, 20, "2026-02-23", "2026-03-02", 7, 29, "2026-07-15", "2026-07-25", 10],
    ]
    aide = [
        ["N° Ord", "Numéro d'ordre"],
        ["Nom + Prénoms", "Nom complet (lookup employé)"],
        ["Nbre Jours Acquis", "Total jours de congé acquis pour l'année"],
        ["Congés anticipés", "Jours pris en avance"],
        ["Nbre Jours Restants", "= Acquis - Anticipés"],
        ["Date départ 1/2", "Format YYYY-MM-DD (pour générer Leave Application)"],
        ["Nb jours", "Calculé entre date départ et reprise"],
        ["", ""],
        ["Note", "Jusqu'à 2 départs par employé dans ce template. Si plus, dupliquer la ligne."],
    ]
    return _build_simple_template("Fiche Gestion Congés", headers, examples, aide, "modele_import_fiche_gestion_conges.xlsx")


def _build_template_gestion_equipe():
    """Template Gestion Equipe : 3 sheets (Equipes, Membres, Taches)."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    head_fill = PatternFill("solid", fgColor="1F4E78")
    head_font = Font(color="FFFFFF", bold=True)

    # Sheet 1 : Equipes
    ws = wb.active
    ws.title = "Equipes"
    headers = ["nom_equipe", "chef_matricule", "description", "date_creation"]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill = head_fill
        c.font = head_font
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 24
    ws.append(["Équipe IT", "1", "Équipe développement & support informatique", "2026-01-01"])
    ws.append(["Équipe Maintenance", "5", "Équipe maintenance préventive et curative", "2026-01-01"])

    # Sheet 2 : Membres
    ws = wb.create_sheet("Membres")
    headers = ["nom_equipe", "matricule_membre", "role"]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill = head_fill
        c.font = head_font
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 22
    ws.append(["Équipe IT", "1", "Chef d'équipe"])
    ws.append(["Équipe IT", "10", "Développeur"])
    ws.append(["Équipe IT", "12", "Support"])

    # Sheet 3 : Taches
    ws = wb.create_sheet("Taches")
    headers = ["nom_equipe", "titre", "description", "date_debut", "date_fin", "taux_effectif"]
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill = head_fill
        c.font = head_font
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 22
    ws.append(["Équipe IT", "Migration ERPNext v16", "Upgrade des modules custom", "2026-06-01", "2026-08-31", 0.6])
    ws.append(["Équipe Maintenance", "Audit annuel sites clients", "Visite préventive Q3", "2026-07-01", "2026-09-30", 0.4])

    # Sheet Aide
    aide = wb.create_sheet("Aide")
    aide.append(["Sheet", "Colonne", "Explication"])
    for c in aide[1]:
        c.fill = head_fill
        c.font = head_font
    rows_aide = [
        ["Equipes", "nom_equipe", "Nom unique de l'équipe (clé primaire)"],
        ["Equipes", "chef_matricule", "Matricule de l'employé chef d'équipe (employee_number)"],
        ["Equipes", "description", "Description libre"],
        ["Equipes", "date_creation", "YYYY-MM-DD"],
        ["Membres", "nom_equipe", "Doit correspondre à une équipe de la sheet 'Equipes'"],
        ["Membres", "matricule_membre", "Matricule employé membre"],
        ["Membres", "role", "Ex: 'Chef d'équipe', 'Développeur', 'Support', 'Membre'"],
        ["Taches", "nom_equipe", "Équipe assignée"],
        ["Taches", "titre", "Titre court de la tâche"],
        ["Taches", "date_debut/fin", "YYYY-MM-DD"],
        ["Taches", "taux_effectif", "Pourcentage temps consacré (0.0 à 1.0)"],
    ]
    for r in rows_aide:
        aide.append(r)
    for col, w in (("A", 14), ("B", 22), ("C", 60)):
        aide.column_dimensions[col].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return {
        "filename": "modele_import_gestion_equipe.xlsx",
        "data": base64.b64encode(buf.read()).decode(),
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

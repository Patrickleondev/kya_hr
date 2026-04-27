"""
Fix complet des DocTypes + notifications manquants.
- Ajoute report_to dans pv_sortie_materiel, planning_conge, demande_achat_kya, bilan_fin_de_stage
- Pour pv_sortie_materiel: ajoute aussi employee (caché) car pas de champ employee
- Ajoute signatures dans planning_conge et bilan_fin_de_stage
- Corrige notifications PV Chef + Achat Chef -> report_to
"""
import json, os, copy

BASE = "kya_hr"

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def load(dt):
    path = f"{BASE}/doctype/{dt}/{dt}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f), path

def save(d, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

def field_names(d):
    return [f["fieldname"] for f in d.get("fields", [])]

def insert_after(fields, after_fieldname, new_fields):
    idx = next((i for i, f in enumerate(fields) if f["fieldname"] == after_fieldname), None)
    if idx is None:
        print(f"  WARNING: field '{after_fieldname}' not found, appending at start")
        idx = 0
    for i, nf in enumerate(new_fields):
        fields.insert(idx + 1 + i, nf)

def insert_before(fields, before_fieldname, new_fields):
    idx = next((i for i, f in enumerate(fields) if f["fieldname"] == before_fieldname), None)
    if idx is None:
        print(f"  WARNING: field '{before_fieldname}' not found, appending")
        fields.extend(new_fields)
        return
    for i, nf in enumerate(new_fields):
        fields.insert(idx + i, nf)

REPORT_TO_FIELD = {
    "fieldname": "report_to",
    "fieldtype": "Link",
    "options": "Employee",
    "label": "Responsable direct",
    "fetch_from": "employee.reports_to",
    "hidden": 1,
    "read_only": 1,
    "in_list_view": 0,
    "print_hide": 1,
}

EMPLOYEE_HIDDEN_FIELD = {
    "fieldname": "employee",
    "fieldtype": "Link",
    "options": "Employee",
    "label": "Employé (demandeur)",
    "hidden": 1,
    "read_only": 1,
    "in_list_view": 0,
    "print_hide": 1,
}

EMPLOYEE_NAME_HIDDEN_FIELD = {
    "fieldname": "employee_name",
    "fieldtype": "Data",
    "label": "Nom employé",
    "fetch_from": "employee.employee_name",
    "hidden": 1,
    "read_only": 1,
    "in_list_view": 0,
    "print_hide": 1,
}

# ─────────────────────────────────────────────────────────────
# 1. pv_sortie_materiel: ajouter employee (caché) + report_to
# ─────────────────────────────────────────────────────────────
d, path = load("pv_sortie_materiel")
fnames = field_names(d)
changed = False

if "employee" not in fnames:
    # Insérer employee + employee_name + report_to après company
    insert_after(d["fields"], "company", [
        copy.deepcopy(EMPLOYEE_HIDDEN_FIELD),
        copy.deepcopy(EMPLOYEE_NAME_HIDDEN_FIELD),
        copy.deepcopy(REPORT_TO_FIELD),
    ])
    print("pv_sortie_materiel: added employee + employee_name + report_to")
    changed = True
elif "report_to" not in fnames:
    insert_after(d["fields"], "employee_name", [copy.deepcopy(REPORT_TO_FIELD)])
    print("pv_sortie_materiel: added report_to")
    changed = True
else:
    print("pv_sortie_materiel: already OK")

if changed:
    save(d, path)

# ─────────────────────────────────────────────────────────────
# 2. planning_conge: ajouter report_to + signatures (Employé, RH, DG)
# ─────────────────────────────────────────────────────────────
d, path = load("planning_conge")
fnames = field_names(d)
changed = False

if "report_to" not in fnames:
    insert_after(d["fields"], "employee_name", [copy.deepcopy(REPORT_TO_FIELD)])
    print("planning_conge: added report_to")
    changed = True

# Signatures: avant section_workflow
SIG_PLANNING = [
    {"fieldname": "section_signatures", "fieldtype": "Section Break", "label": "Signatures"},
    {"fieldname": "col_sig_employe", "fieldtype": "Column Break", "label": "Employé"},
    {"fieldname": "signature_employe", "fieldtype": "Signature", "label": "Signature Employé"},
    {"fieldname": "signataire_employe", "fieldtype": "Data", "label": "Signataire Employé", "read_only": 1},
    {"fieldname": "date_signature_employe", "fieldtype": "Date", "label": "Date Signature Employé", "read_only": 1},
    {"fieldname": "col_sig_rh", "fieldtype": "Column Break", "label": "Responsable RH"},
    {"fieldname": "signature_rh", "fieldtype": "Signature", "label": "Signature RH"},
    {"fieldname": "signataire_rh", "fieldtype": "Data", "label": "Signataire RH", "read_only": 1},
    {"fieldname": "date_signature_rh", "fieldtype": "Date", "label": "Date Signature RH", "read_only": 1},
    {"fieldname": "col_sig_dg", "fieldtype": "Column Break", "label": "Directeur Général"},
    {"fieldname": "signature_dg", "fieldtype": "Signature", "label": "Signature DG"},
    {"fieldname": "signataire_dg", "fieldtype": "Data", "label": "Signataire DG", "read_only": 1},
    {"fieldname": "date_signature_dg", "fieldtype": "Date", "label": "Date Signature DG", "read_only": 1},
]
fnames = field_names(d)
if "signature_employe" not in fnames:
    insert_before(d["fields"], "section_workflow", SIG_PLANNING)
    print("planning_conge: added signature fields")
    changed = True

if changed:
    save(d, path)
else:
    print("planning_conge: already OK")

# ─────────────────────────────────────────────────────────────
# 3. demande_achat_kya: ajouter report_to après employee_name
# ─────────────────────────────────────────────────────────────
d, path = load("demande_achat_kya")
fnames = field_names(d)

if "report_to" not in fnames:
    insert_after(d["fields"], "employee_name", [copy.deepcopy(REPORT_TO_FIELD)])
    save(d, path)
    print("demande_achat_kya: added report_to")
else:
    print("demande_achat_kya: report_to already OK")

# ─────────────────────────────────────────────────────────────
# 4. bilan_fin_de_stage: ajouter report_to + signatures
# ─────────────────────────────────────────────────────────────
d, path = load("bilan_fin_de_stage")
fnames = field_names(d)
changed = False

if "report_to" not in fnames:
    insert_after(d["fields"], "employee_name", [copy.deepcopy(REPORT_TO_FIELD)])
    print("bilan_fin_de_stage: added report_to")
    changed = True

SIG_BILAN = [
    {"fieldname": "section_signatures", "fieldtype": "Section Break", "label": "Signatures & Validation"},
    {"fieldname": "col_sig_stagiaire", "fieldtype": "Column Break", "label": "Stagiaire"},
    {"fieldname": "signature_stagiaire", "fieldtype": "Signature", "label": "Signature Stagiaire"},
    {"fieldname": "signataire_stagiaire", "fieldtype": "Data", "label": "Signataire Stagiaire", "read_only": 1},
    {"fieldname": "date_signature_stagiaire", "fieldtype": "Date", "label": "Date Signature Stagiaire", "read_only": 1},
    {"fieldname": "col_sig_encadrant", "fieldtype": "Column Break", "label": "Encadrant / Maître de Stage"},
    {"fieldname": "signature_encadrant", "fieldtype": "Signature", "label": "Signature Encadrant"},
    {"fieldname": "signataire_encadrant", "fieldtype": "Data", "label": "Signataire Encadrant", "read_only": 1},
    {"fieldname": "date_signature_encadrant", "fieldtype": "Date", "label": "Date Signature Encadrant", "read_only": 1},
    {"fieldname": "col_sig_resp_stagiaires", "fieldtype": "Column Break", "label": "Responsable Stagiaires"},
    {"fieldname": "signature_resp_stagiaires", "fieldtype": "Signature", "label": "Signature Resp. Stagiaires"},
    {"fieldname": "signataire_resp_stagiaires", "fieldtype": "Data", "label": "Signataire Resp. Stagiaires", "read_only": 1},
    {"fieldname": "date_signature_resp_stagiaires", "fieldtype": "Date", "label": "Date Signature Resp. Stagiaires", "read_only": 1},
]
fnames = field_names(d)
if "signature_stagiaire" not in fnames:
    insert_before(d["fields"], "section_valid", SIG_BILAN)
    print("bilan_fin_de_stage: added signature fields")
    changed = True

if changed:
    save(d, path)
else:
    print("bilan_fin_de_stage: already OK")

# ─────────────────────────────────────────────────────────────
# 5. Notifications: PV Chef + Achat Chef -> report_to
# ─────────────────────────────────────────────────────────────
notif_path = "kya_hr/fixtures/notification.json"
with open(notif_path, encoding="utf-8") as f:
    notifs = json.load(f)

fixes = {
    "KYA - PV Matériel: En attente Chef": {"receiver_by_document_field": "report_to"},
    "KYA - Demande Achat: En attente Chef": {"receiver_by_document_field": "report_to"},
}

notif_changed = 0
for n in notifs:
    name = n.get("name", "")
    if name in fixes:
        old = n.get("recipients")
        n["recipients"] = [fixes[name]]
        print(f"Notification fixed: {name}  {old} -> {n['recipients']}")
        notif_changed += 1

with open(notif_path, "w", encoding="utf-8") as f:
    json.dump(notifs, f, ensure_ascii=False, indent=1)
print(f"\nFixed {notif_changed} notifications.")
print("\nAll done.")

"""
Script de seed pour les donnees de test KYA HR.
Cree des enregistrements de test dans les 4 DocTypes principaux.

Usage :
  docker exec kya-test-8084-backend bench --site frontend execute kya_hr.kya_hr.seed_test_data.execute
"""
import frappe
from frappe.utils import today, add_days


def _get_or_create_test_employee():
    emp = frappe.db.get_value("Employee", {}, "name", order_by="creation asc")
    if emp:
        return emp
    company = frappe.db.get_value("Company", {}, "name", order_by="creation asc") or "Demo"
    emp_doc = frappe.get_doc({
        "doctype": "Employee",
        "first_name": "KYA",
        "last_name": "TestUser",
        "employee_name": "KYA TestUser",
        "status": "Active",
        "gender": "Male",
        "date_of_joining": today(),
        "date_of_birth": "1990-01-01",
        "company": company,
    })
    emp_doc.flags.ignore_permissions = True
    emp_doc.flags.ignore_links = True
    emp_doc.insert()
    frappe.db.commit()
    print("  [SEED] Employe cree : " + emp_doc.name)
    return emp_doc.name


def _insert_doc(doc_data, state_override=None):
    """Insert un document en ignorant permissions/links/mandatory. Force l etat WF via DB."""
    doc = frappe.get_doc(doc_data)
    doc.insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)
    if state_override:
        frappe.db.set_value(doc_data["doctype"], doc.name, "workflow_state", state_override)
    frappe.db.commit()
    return doc.name


def _get_or_create(doctype, filters, doc_data, state_override=None, label=""):
    existing = frappe.db.get_value(doctype, filters, "name")
    if existing:
        print("  [SEED] " + label + " (existant) : " + existing)
        return existing
    name = _insert_doc(doc_data, state_override)
    print("  [SEED] " + label + " : " + name)
    return name


def _seed_permission_sortie_employe(employee):
    created = []
    created.append(_get_or_create(
        "Permission Sortie Employe",
        {"employee": employee, "workflow_state": "Brouillon"},
        {"doctype": "Permission Sortie Employe", "employee": employee,
         "date_sortie": today(), "heure_depart": "09:00:00", "heure_retour": "11:00:00",
         "motif": "Rendez-vous medical (donnees de test)", "duree_heures": 2},
        label="PSE Brouillon"
    ))
    created.append(_get_or_create(
        "Permission Sortie Employe",
        {"employee": employee, "workflow_state": "En attente Chef Service"},
        {"doctype": "Permission Sortie Employe", "employee": employee,
         "date_sortie": add_days(today(), 1), "heure_depart": "14:00:00", "heure_retour": "17:00:00",
         "motif": "Demarche administrative (donnees de test)", "duree_heures": 3},
        state_override="En attente Chef Service",
        label="PSE En attente Chef"
    ))
    return [n for n in created if n]


def _seed_demande_achat(employee):
    created = []
    created.append(_get_or_create(
        "Demande Achat KYA",
        {"employee": employee, "workflow_state": "Brouillon"},
        {"doctype": "Demande Achat KYA", "employee": employee, "date_demande": today(),
         "objet": "Achat fournitures bureau (donnees de test)", "urgence": "Normal",
         "justification": "Renouvellement Q2 2026",
         "items": [{"designation": "Rames papier A4", "quantite": 10, "unite": "Rame", "prix_unitaire_estime": 3500},
                   {"designation": "Stylos bille", "quantite": 5, "unite": "Boite", "prix_unitaire_estime": 2000}]},
        label="DA Brouillon"
    ))
    created.append(_get_or_create(
        "Demande Achat KYA",
        {"employee": employee, "workflow_state": "En attente Chef Service"},
        {"doctype": "Demande Achat KYA", "employee": employee, "date_demande": add_days(today(), -3),
         "objet": "Cartouche imprimante (donnees de test)", "urgence": "Urgent",
         "justification": "Urgente",
         "items": [{"designation": "Cartouche HP toner noir", "quantite": 2, "unite": "Piece", "prix_unitaire_estime": 45000}]},
        state_override="En attente Chef Service",
        label="DA En attente Chef"
    ))
    return [n for n in created if n]


def _seed_pv_sortie_materiel():
    created = []
    created.append(_get_or_create(
        "PV Sortie Materiel",
        {"owner": "Administrator", "workflow_state": "Brouillon"},
        {"doctype": "PV Sortie Materiel", "objet": "Transport materiel informatique (donnees de test)",
         "date_sortie": today(), "lieu_destination": "Site Kovie",
         "items": [{"designation": "Laptop Dell Latitude", "quantite": 1, "numero_serie": "DL-2024-001", "observation": "Bon etat"},
                   {"designation": "Switch reseau 8 ports", "quantite": 1, "numero_serie": "SW-2024-005", "observation": "Bon etat"}]},
        label="PV Brouillon"
    ))
    created.append(_get_or_create(
        "PV Sortie Materiel",
        {"owner": "Administrator", "workflow_state": "En attente Magasin"},
        {"doctype": "PV Sortie Materiel", "objet": "Retour materiel maintenance (donnees de test)",
         "date_sortie": add_days(today(), -1), "lieu_destination": "Entrepot principal",
         "items": [{"designation": "Cable electrique 10mm2", "quantite": 2, "numero_serie": "", "observation": "Retour chantier"}]},
        state_override="En attente Magasin",
        label="PV En attente Magasin"
    ))
    return [n for n in created if n]


def _seed_planning_conge(employee):
    import datetime
    annee = datetime.date.today().year
    created = []
    created.append(_get_or_create(
        "Planning Conge",
        {"employee": employee, "annee": annee},
        {"doctype": "Planning Conge", "employee": employee, "annee": annee,
         "periodes": [{"date_debut": str(annee) + "-07-01", "date_fin": str(annee) + "-07-14",
                       "duree_jours": 14, "type_conge": "Conge Annuel", "note": "Periode estivale"},
                      {"date_debut": str(annee) + "-12-23", "date_fin": str(annee) + "-12-31",
                       "duree_jours": 9, "type_conge": "Conge Annuel", "note": "Fin annee"}]},
        label="Planning Conge " + str(annee) + " Brouillon"
    ))
    annee_prec = annee - 1
    created.append(_get_or_create(
        "Planning Conge",
        {"employee": employee, "annee": annee_prec},
        {"doctype": "Planning Conge", "employee": employee, "annee": annee_prec,
         "periodes": [{"date_debut": str(annee_prec) + "-08-01", "date_fin": str(annee_prec) + "-08-14",
                       "duree_jours": 14, "type_conge": "Conge Annuel", "note": "Conge ete"}]},
        state_override="Approuve",
        label="Planning Conge " + str(annee_prec) + " Approuve"
    ))
    return [n for n in created if n]


def execute():
    print("=" * 60)
    print("  KYA HR - SEED TEST DATA")
    print("=" * 60)

    employee = _get_or_create_test_employee()
    emp_info = frappe.db.get_value("Employee", employee, ["employee_name", "department"], as_dict=True)
    print("\n  Employe : " + employee + " (" + (emp_info.employee_name or "") + ")")
    print()

    try:
        pse = _seed_permission_sortie_employe(employee)
    except Exception as e:
        print("  [WARN] PSE: " + str(e))
        pse = frappe.db.get_all("Permission Sortie Employe", {"employee": employee}, pluck="name") or []

    try:
        da = _seed_demande_achat(employee)
    except Exception as e:
        print("  [WARN] DA: " + str(e))
        da = frappe.db.get_all("Demande Achat KYA", {"employee": employee}, pluck="name") or []

    try:
        pv = _seed_pv_sortie_materiel()
    except Exception as e:
        print("  [WARN] PV: " + str(e))
        pv = frappe.db.get_all("PV Sortie Materiel", {"owner": "Administrator"}, pluck="name") or []

    try:
        pc = _seed_planning_conge(employee)
    except Exception as e:
        print("  [WARN] PC: " + str(e))
        pc = frappe.db.get_all("Planning Conge", {"employee": employee}, pluck="name") or []

    print()
    print("=" * 60)
    print("  RESUME - IDs crees / trouves")
    print("=" * 60)
    print("  Permission Sortie Employe : " + str(pse))
    print("  Demande Achat KYA        : " + str(da))
    print("  PV Sortie Materiel       : " + str(pv))
    print("  Planning Conge           : " + str(pc))
    print()
    print("  URLs de test (Web Forms):")
    all_ids = {
        "permission-sortie-employe": pse,
        "demande-achat": da,
        "pv-sortie-materiel": pv,
        "planning-conge": pc,
    }
    for route, ids in all_ids.items():
        for doc_id in (ids or []):
            print("    http://localhost:8084/" + route + "?name=" + doc_id)
    print()
    print("  Termine OK")

import frappe
from frappe.utils import nowdate, add_days, add_months, getdate, today
import random

def run():
    frappe.flags.in_import = True
    frappe.conf.server_script_enabled = True

    # Temporarily disable server scripts on Employee to avoid safe_exec issues
    server_scripts = frappe.get_all("Server Script", filters={"reference_doctype": "Employee"}, pluck="name")
    for ss in server_scripts:
        frappe.db.set_value("Server Script", ss, "disabled", 1, update_modified=False)
    frappe.db.commit()
    frappe.clear_cache()

    # Cleanup: delete orphan user from previous failed run
    if frappe.db.exists("User", "dg@kya-energy.com") and not frappe.db.exists("Employee", {"user_id": "dg@kya-energy.com"}):
        frappe.delete_doc("User", "dg@kya-energy.com", force=True, ignore_permissions=True)
        frappe.db.commit()
        print("  Cleaned up orphan user: dg@kya-energy.com")

    # ========================================
    # 1. COMPANY - Rename Demo -> KYA-Energy Group
    # ========================================
    print("=== 1. SETTING UP COMPANY ===")
    # Use existing Demo company - abbr is set_only_once, can't change
    if frappe.db.exists("Company", "KYA-Energy Group"):
        company = "KYA-Energy Group"
        print(f"  Company: {company}")
    elif frappe.db.exists("Company", "Demo"):
        company = "Demo"
        # Just ensure currency is XOF
        frappe.db.set_value("Company", company, "default_currency", "XOF")
        frappe.db.set_value("Company", company, "country", "Togo")
        frappe.db.commit()
        print(f"  Using company: {company} (XOF)")
    else:
        company = "KYA-Energy Group"
        frappe.get_doc({
            "doctype": "Company",
            "company_name": company,
            "abbr": "KYA",
            "default_currency": "XOF",
            "country": "Togo"
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Created company: {company}")

    # ========================================
    # 2. DEPARTMENTS
    # ========================================
    print("\n=== 2. CREATING DEPARTMENTS ===")
    departments = [
        {"department_name": "Direction Générale"},
        {"department_name": "Services Supports"},
        {"department_name": "Equipe RH"},
        {"department_name": "Achat et Approvisionnement"},
        {"department_name": "Stocks et Logistics"},
        {"department_name": "Finance et Comptabilité"},
        {"department_name": "Services Commercial"},
        {"department_name": "Services Technique"},
        {"department_name": "EQUIPE INFORMATIQUE"},
    ]
    dept_map = {}
    abbr = frappe.db.get_value("Company", company, "abbr") or company
    for dept in departments:
        expected_name = f"{dept['department_name']} - {abbr}"
        if not frappe.db.exists("Department", expected_name):
            d = frappe.get_doc({
                "doctype": "Department",
                "department_name": dept["department_name"],
                "company": company,
                "is_group": 0,
                "parent_department": "Tous les départements"
            })
            d.insert(ignore_permissions=True)
            dept_map[dept["department_name"]] = d.name
            print(f"  Created: {d.name}")
        else:
            dept_map[dept["department_name"]] = expected_name
            print(f"  Exists: {expected_name}")
    frappe.db.commit()

    # ========================================
    # 3. DESIGNATIONS
    # ========================================
    print("\n=== 3. CREATING DESIGNATIONS ===")
    designations = [
        "CHEF EQPE MAINTENANCE", "ING. CHARGE OFFRES", "MANAGER EQPES PC",
        "ING. DES TRAVAUX", "ASS. EQPE ACHATS", "COMPTABLE", "TECHNICIEN",
        "CAISSIERE", "RESP. AUDITS INTERNES", "ASSISTANT LOGISTIQUE",
        "CHAUFFEUR", "ELECTROTECHNICIEN", "RESP. ACHAT & APPROV",
        "ASS. COMMERCIALE", "DIRECTEUR G. ADJOINT", "DIRECTEUR GENERAL",
        "STAGE-COMPTABILITE", "STAGE-QHSE", "STAGE-INFORMATIQUE", "STAGE-ELECTRONIQUE"
    ]
    for des in designations:
        if not frappe.db.exists("Designation", des):
            try:
                frappe.get_doc({"doctype": "Designation", "designation_name": des}).insert(ignore_permissions=True)
                print(f"  Created: {des}")
            except Exception as e:
                print(f"  Designation error {des}: {e}")
    frappe.db.commit()

    # ========================================
    # 3b. EMPLOYMENT TYPES
    # ========================================
    print("\n=== 3b. CREATING EMPLOYMENT TYPES ===")
    for et_name in ["CDI", "CDD", "Stage", "Prestataire"]:
        if not frappe.db.exists("Employment Type", et_name):
            frappe.get_doc({"doctype": "Employment Type", "employee_type_name": et_name}).insert(ignore_permissions=True)
            print(f"  Created: {et_name}")
        else:
            print(f"  Exists: {et_name}")
    frappe.db.commit()

    # ========================================
    # 4. ROLES
    # ========================================
    print("\n=== 4. ENSURING ROLES ===")
    for role in ["Employee Self Service", "KYA Survey Admin", "KYA Destinataire Notif"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "is_custom": 1}).insert(ignore_permissions=True)
            print(f"  Created role: {role}")
    frappe.db.commit()

    # ========================================
    # 5. USERS & EMPLOYEES
    # ========================================
    print("\n=== 5. CREATING USERS & EMPLOYEES ===")

    def dept_name(short):
        return dept_map.get(short, f"{short} - {abbr}")

    users_data = [
        {"email": "dg@kya-energy.com", "first_name": "Komlan", "last_name": "AGBEKO",
         "roles": ["Employee", "HR Manager", "Stock Manager", "Purchase Manager", "KYA Destinataire Notif"],
         "department": dept_name("Direction Générale"), "designation": "DIRECTEUR GENERAL",
         "emp_type": "CDI", "dob": "1978-03-12",
         "classe": "P", "echelon": "5"},
        {"email": "dga@kya-energy.com", "first_name": "Afi", "last_name": "MENSAH",
         "roles": ["Employee", "HR Manager", "Stock Manager", "Purchase Manager", "Auditor", "KYA Destinataire Notif"],
         "department": dept_name("Direction Générale"), "designation": "DIRECTEUR G. ADJOINT",
         "emp_type": "CDI", "dob": "1982-07-25",
         "classe": "O", "echelon": "4"},
        {"email": "chef.tech@kya-energy.com", "first_name": "Koffi", "last_name": "AMOUZOU",
         "roles": ["Employee", "HR User", "Stock User", "Purchase User", "KYA Destinataire Notif"],
         "department": dept_name("Services Technique"), "designation": "CHEF EQPE MAINTENANCE",
         "emp_type": "CDI", "dob": "1985-11-03",
         "classe": "K", "echelon": "3"},
        {"email": "rh@kya-energy.com", "first_name": "Akouvi", "last_name": "KOUDJO",
         "roles": ["Employee", "HR User", "HR Manager", "KYA Destinataire Notif"],
         "department": dept_name("Equipe RH"), "designation": "RESP. AUDITS INTERNES",
         "emp_type": "CDI", "dob": "1988-01-18",
         "classe": "J", "echelon": "4"},
        {"email": "achats@kya-energy.com", "first_name": "Yao", "last_name": "GNASSINGBE",
         "roles": ["Employee", "Purchase User", "Purchase Manager", "Stock User"],
         "department": dept_name("Achat et Approvisionnement"), "designation": "RESP. ACHAT & APPROV",
         "emp_type": "CDI", "dob": "1990-09-07",
         "classe": "I", "echelon": "3"},
        {"email": "magasin@kya-energy.com", "first_name": "Kodjo", "last_name": "ASSOGBA",
         "roles": ["Employee", "Stock User", "Stock Manager"],
         "department": dept_name("Stocks et Logistics"), "designation": "ASSISTANT LOGISTIQUE",
         "emp_type": "CDI", "dob": "1992-04-22",
         "classe": "F", "echelon": "2"},
        {"email": "audit@kya-energy.com", "first_name": "Essivi", "last_name": "TOGBE",
         "roles": ["Employee", "Auditor"],
         "department": dept_name("Services Supports"), "designation": "RESP. AUDITS INTERNES",
         "emp_type": "CDI", "dob": "1987-06-14",
         "classe": "J", "echelon": "5"},
        {"email": "compta@kya-energy.com", "first_name": "Ama", "last_name": "DJOSSOU",
         "roles": ["Employee"],
         "department": dept_name("Finance et Comptabilité"), "designation": "COMPTABLE",
         "emp_type": "CDI", "dob": "1993-12-30",
         "classe": "G", "echelon": "2"},
        {"email": "tech1@kya-energy.com", "first_name": "Messan", "last_name": "ADJAMAGBO",
         "roles": ["Employee"],
         "department": dept_name("Services Technique"), "designation": "TECHNICIEN",
         "emp_type": "CDD", "dob": "1995-02-08",
         "classe": "E", "echelon": "3"},
        {"email": "commercial@kya-energy.com", "first_name": "Akofa", "last_name": "LAWSON",
         "roles": ["Employee"],
         "department": dept_name("Services Commercial"), "designation": "ASS. COMMERCIALE",
         "emp_type": "CDD", "dob": "1994-08-19",
         "classe": "D", "echelon": "4"},
        # STAGIAIRES
        {"email": "stagiaire1@kya-energy.com", "first_name": "Edem", "last_name": "AGBODJAN",
         "roles": ["Employee", "Employee Self Service"],
         "department": dept_name("EQUIPE INFORMATIQUE"), "designation": "STAGE-INFORMATIQUE",
         "emp_type": "Stage", "dob": "2001-05-15",
         "classe": "A", "echelon": "1"},
        {"email": "stagiaire2@kya-energy.com", "first_name": "Abla", "last_name": "GBEDEMAH",
         "roles": ["Employee", "Employee Self Service"],
         "department": dept_name("Finance et Comptabilité"), "designation": "STAGE-COMPTABILITE",
         "emp_type": "Stage", "dob": "2000-10-03",
         "classe": "A", "echelon": "1"},
        {"email": "stagiaire3@kya-energy.com", "first_name": "Kossi", "last_name": "EKUE",
         "roles": ["Employee", "Employee Self Service"],
         "department": dept_name("Services Technique"), "designation": "STAGE-ELECTRONIQUE",
         "emp_type": "Stage", "dob": "2002-01-27",
         "classe": "A", "echelon": "1"},
        {"email": "stagiaire4@kya-energy.com", "first_name": "Kafui", "last_name": "AMEGAH",
         "roles": ["Employee", "Employee Self Service"],
         "department": dept_name("Services Supports"), "designation": "STAGE-QHSE",
         "emp_type": "Stage", "dob": "2001-08-11",
         "classe": "A", "echelon": "1"},
    ]

    employee_map = {}

    for u in users_data:
        try:
            # Create User
            if not frappe.db.exists("User", u["email"]):
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": u["email"],
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "enabled": 1,
                    "user_type": "System User",
                    "send_welcome_email": 0,
                    "new_password": "Kya@2025",
                    "roles": [{"role": r} for r in u["roles"]]
                })
                user.flags.no_welcome_mail = True
                user.insert(ignore_permissions=True)
                print(f"  User created: {u['email']}")
            else:
                print(f"  User exists: {u['email']}")

            # Create Employee
            existing_emp = frappe.db.get_value("Employee", {"user_id": u["email"]}, "name")
            if not existing_emp:
                gender = "Female" if u["first_name"] in ["Afi","Akouvi","Ama","Akofa","Abla","Kafui"] else "Male"
                doj = "2023-01-15" if u["emp_type"] != "Stage" else "2025-03-01"
                dob = u.get("dob", "1990-05-15")
                emp = frappe.get_doc({
                    "doctype": "Employee",
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "employee_name": f"{u['first_name']} {u['last_name']}",
                    "company": company,
                    "department": u["department"],
                    "designation": u["designation"],
                    "gender": gender,
                    "date_of_birth": dob,
                    "date_of_joining": doj,
                    "status": "Active",
                    "employment_type": u["emp_type"],
                    "user_id": u["email"],
                    "custom_kya_classe": u.get("classe", ""),
                    "custom_kya_echelon": u.get("echelon", ""),
                })
                emp.flags.ignore_permissions = True
                emp.flags.ignore_mandatory = True
                emp.insert(ignore_permissions=True)
                employee_map[u["email"]] = emp.name
                print(f"  Employee created: {emp.name} - {emp.employee_name}")
            else:
                employee_map[u["email"]] = existing_emp
                print(f"  Employee exists: {existing_emp}")
        except Exception as e:
            print(f"  ERROR for {u['email']}: {e}")

    frappe.db.commit()

    # ========================================
    # 6. PSS
    # ========================================
    print("\n=== 6. CREATING PSS TEST DATA ===")
    pss_data = [
        {"email": "stagiaire1@kya-energy.com", "date": add_days(today(), -10),
         "heure_depart": "09:30:00", "heure_retour": "11:00:00",
         "motif": "Rendez-vous médical au CHU Sylvanus Olympio", "wf": "Approuvé"},
        {"email": "stagiaire2@kya-energy.com", "date": add_days(today(), -7),
         "heure_depart": "14:00:00", "heure_retour": "16:00:00",
         "motif": "Remise de documents à l'université de Lomé", "wf": "En attente Chef"},
        {"email": "stagiaire3@kya-energy.com", "date": add_days(today(), -3),
         "heure_depart": "10:00:00", "heure_retour": "12:00:00",
         "motif": "Achat de composants électroniques au marché", "wf": "En attente Resp. Stagiaires"},
        {"email": "stagiaire1@kya-energy.com", "date": add_days(today(), -1),
         "heure_depart": "08:00:00", "heure_retour": "09:30:00",
         "motif": "Récupération de colis à la poste", "wf": "Brouillon"},
        {"email": "stagiaire4@kya-energy.com", "date": add_days(today(), -15),
         "heure_depart": "13:00:00", "heure_retour": "15:00:00",
         "motif": "Démarches administratives (carte d'identité)", "wf": "Rejeté"},
        {"email": "stagiaire2@kya-energy.com", "date": add_days(today(), -20),
         "heure_depart": "11:00:00", "heure_retour": "12:30:00",
         "motif": "Visite chez le dentiste", "wf": "Approuvé"},
    ]

    for p in pss_data:
        emp_id = employee_map.get(p["email"])
        if not emp_id:
            print(f"  Skip PSS: no employee for {p['email']}")
            continue
        emp = frappe.get_doc("Employee", emp_id)
        try:
            doc = frappe.get_doc({
                "doctype": "Permission Sortie Stagiaire",
                "employee": emp_id,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "date_sortie": p["date"],
                "heure_depart": p["heure_depart"],
                "heure_retour": p["heure_retour"],
                "motif": p["motif"],
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            ds = 1 if p["wf"] in ["Approuvé", "Rejeté"] else 0
            frappe.db.set_value("Permission Sortie Stagiaire", doc.name,
                {"workflow_state": p["wf"], "docstatus": ds}, update_modified=False)
            print(f"  PSS: {doc.name} [{p['wf']}]")
        except Exception as e:
            print(f"  PSS error: {e}")
    frappe.db.commit()

    # ========================================
    # 7. PSE
    # ========================================
    print("\n=== 7. CREATING PSE TEST DATA ===")
    pse_data = [
        {"email": "tech1@kya-energy.com", "date": add_days(today(), -8),
         "heure_depart": "09:00:00", "heure_retour": "11:00:00",
         "motif": "Rendez-vous à la banque pour ouverture de compte", "wf": "Approuvé"},
        {"email": "compta@kya-energy.com", "date": add_days(today(), -5),
         "heure_depart": "14:00:00", "heure_retour": "16:00:00",
         "motif": "Dépôt de chèques à Ecobank", "wf": "En attente RH"},
        {"email": "commercial@kya-energy.com", "date": add_days(today(), -2),
         "heure_depart": "10:00:00", "heure_retour": "12:00:00",
         "motif": "Visite client Projet solaire Atakpamé", "wf": "En attente DGA"},
        {"email": "tech1@kya-energy.com", "date": add_days(today(), 0),
         "heure_depart": "08:30:00", "heure_retour": "10:00:00",
         "motif": "Intervention urgente site client Kégué", "wf": "En attente Chef"},
        {"email": "compta@kya-energy.com", "date": add_days(today(), -12),
         "heure_depart": "15:00:00", "heure_retour": "17:00:00",
         "motif": "Rendez-vous à la CNSS pour déclarations", "wf": "Approuvé"},
    ]

    for p in pse_data:
        emp_id = employee_map.get(p["email"])
        if not emp_id:
            continue
        emp = frappe.get_doc("Employee", emp_id)
        try:
            doc = frappe.get_doc({
                "doctype": "Permission Sortie Employe",
                "employee": emp_id,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "date_sortie": p["date"],
                "heure_depart": p["heure_depart"],
                "heure_retour": p["heure_retour"],
                "motif": p["motif"],
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            ds = 1 if p["wf"] in ["Approuvé", "Rejeté"] else 0
            frappe.db.set_value("Permission Sortie Employe", doc.name,
                {"workflow_state": p["wf"], "docstatus": ds}, update_modified=False)
            print(f"  PSE: {doc.name} [{p['wf']}]")
        except Exception as e:
            print(f"  PSE error: {e}")
    frappe.db.commit()

    # ========================================
    # 8. PV SORTIE MATERIEL
    # ========================================
    print("\n=== 8. CREATING PV SORTIE MATERIEL ===")
    pv_data = [
        {"email": "tech1@kya-energy.com", "date": add_days(today(), -6),
         "objet": "Sortie matériel pour intervention site solaire Kpalimé",
         "items": [
             {"designation": "Panneau solaire 350W", "qte_demandee": 4},
             {"designation": "Onduleur hybride 5kVA", "qte_demandee": 1},
             {"designation": "Câble solaire 6mm² (50m)", "qte_demandee": 2},
         ], "wf": "Approuvé"},
        {"email": "chef.tech@kya-energy.com", "date": add_days(today(), -3),
         "objet": "Matériel maintenance préventive centrale Aného",
         "items": [
             {"designation": "Batterie 200Ah AGM", "qte_demandee": 6},
             {"designation": "Fusible 15A DC", "qte_demandee": 10},
             {"designation": "Disjoncteur DC 32A", "qte_demandee": 2},
         ], "wf": "En attente Audit"},
        {"email": "tech1@kya-energy.com", "date": add_days(today(), -1),
         "objet": "Outils pour dépannage onduleur client",
         "items": [
             {"designation": "Multimètre numérique", "qte_demandee": 1},
             {"designation": "Pince ampèremétrique", "qte_demandee": 1},
         ], "wf": "En attente Magasin"},
        {"email": "commercial@kya-energy.com", "date": add_days(today(), 0),
         "objet": "Échantillons pour démonstration client Lomé",
         "items": [
             {"designation": "Kit lampe solaire LED", "qte_demandee": 3},
             {"designation": "Brochure technique A4", "qte_demandee": 20},
         ], "wf": "Brouillon"},
    ]

    for p in pv_data:
        emp_id = employee_map.get(p["email"])
        if not emp_id:
            continue
        emp = frappe.get_doc("Employee", emp_id)
        try:
            doc = frappe.get_doc({
                "doctype": "PV Sortie Materiel",
                "objet": p["objet"],
                "date_sortie": p["date"],
                "items": p["items"],
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            ds = 1 if p["wf"] in ["Approuvé", "Rejeté"] else 0
            frappe.db.set_value("PV Sortie Materiel", doc.name,
                {"workflow_state": p["wf"], "docstatus": ds}, update_modified=False)
            print(f"  PV: {doc.name} [{p['wf']}]")
        except Exception as e:
            print(f"  PV error: {e}")
    frappe.db.commit()

    # ========================================
    # 9. DEMANDE ACHAT KYA
    # ========================================
    print("\n=== 9. CREATING DEMANDE ACHAT KYA ===")
    da_data = [
        {"email": "chef.tech@kya-energy.com", "date": add_days(today(), -10),
         "objet": "Achat panneaux solaires pour projet Kara", "urgence": "Haute",
         "items": [
             {"description": "Panneau solaire monocristallin 450W", "quantite": 20, "prix_unitaire": 185000},
             {"description": "Structure de montage aluminium", "quantite": 20, "prix_unitaire": 45000},
         ], "wf": "Approuvé"},
        {"email": "tech1@kya-energy.com", "date": add_days(today(), -5),
         "objet": "Achat outillage atelier", "urgence": "Normale",
         "items": [
             {"description": "Perceuse visseuse 18V", "quantite": 2, "prix_unitaire": 35000},
         ], "wf": "En attente Chef"},
        {"email": "achats@kya-energy.com", "date": add_days(today(), -3),
         "objet": "Fournitures de bureau trimestrielles", "urgence": "Basse",
         "items": [
             {"description": "Ramette papier A4 (carton 5)", "quantite": 10, "prix_unitaire": 18000},
             {"description": "Cartouche encre HP 305", "quantite": 4, "prix_unitaire": 12000},
             {"description": "Stylos BIC (boîte 50)", "quantite": 2, "prix_unitaire": 7500},
         ], "wf": "En attente Approbation"},
        {"email": "chef.tech@kya-energy.com", "date": add_days(today(), -1),
         "objet": "Achat batteries pour stock sécurité", "urgence": "Haute",
         "items": [
             {"description": "Batterie Lithium 48V 100Ah", "quantite": 10, "prix_unitaire": 450000},
         ], "wf": "En attente DG"},
        {"email": "compta@kya-energy.com", "date": add_days(today(), 0),
         "objet": "Logiciel comptabilité mise à jour", "urgence": "Normale",
         "items": [
             {"description": "Licence annuelle SAGE Comptabilité", "quantite": 1, "prix_unitaire": 750000},
         ], "wf": "Brouillon"},
    ]

    for p in da_data:
        emp_id = employee_map.get(p["email"])
        if not emp_id:
            continue
        emp = frappe.get_doc("Employee", emp_id)
        try:
            doc = frappe.get_doc({
                "doctype": "Demande Achat KYA",
                "employee": emp_id,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "date_demande": p["date"],
                "objet": p["objet"],
                "urgence": p["urgence"],
                "items": p["items"],
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            ds = 1 if p["wf"] in ["Approuvé", "Rejeté"] else 0
            frappe.db.set_value("Demande Achat KYA", doc.name,
                {"workflow_state": p["wf"], "docstatus": ds}, update_modified=False)
            print(f"  DA: {doc.name} [{p['wf']}]")
        except Exception as e:
            print(f"  DA error: {e}")
    frappe.db.commit()

    # ========================================
    # 10. PLANNING CONGE
    # ========================================
    print("\n=== 10. CREATING PLANNING CONGE ===")
    conge_data = [
        {"email": "tech1@kya-energy.com", "annee": "2026",
         "periodes": [
             {"date_debut": "2026-04-14", "date_fin": "2026-04-25", "type_conge": "Congé Annuel"},
             {"date_debut": "2026-08-01", "date_fin": "2026-08-15", "type_conge": "Congé Annuel"},
         ], "wf": "Approuvé"},
        {"email": "compta@kya-energy.com", "annee": "2026",
         "periodes": [
             {"date_debut": "2026-07-01", "date_fin": "2026-07-15", "type_conge": "Congé Annuel"},
         ], "wf": "En attente RH"},
        {"email": "commercial@kya-energy.com", "annee": "2026",
         "periodes": [
             {"date_debut": "2026-06-01", "date_fin": "2026-06-10", "type_conge": "Congé Annuel"},
             {"date_debut": "2026-12-20", "date_fin": "2026-12-31", "type_conge": "Congé Annuel"},
         ], "wf": "Brouillon"},
    ]

    for p in conge_data:
        emp_id = employee_map.get(p["email"])
        if not emp_id:
            continue
        emp = frappe.get_doc("Employee", emp_id)
        try:
            doc = frappe.get_doc({
                "doctype": "Planning Conge",
                "employee": emp_id,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "annee": p["annee"],
                "periodes": p["periodes"],
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            ds = 1 if p["wf"] in ["Approuvé", "Rejeté"] else 0
            frappe.db.set_value("Planning Conge", doc.name,
                {"workflow_state": p["wf"], "docstatus": ds}, update_modified=False)
            print(f"  Planning: {doc.name} [{p['wf']}]")
        except Exception as e:
            print(f"  Planning error: {e}")
    frappe.db.commit()

    # ========================================
    # 11. BILAN FIN DE STAGE
    # ========================================
    print("\n=== 11. CREATING BILAN FIN DE STAGE ===")
    bilan_data = [
        {"email": "stagiaire1@kya-energy.com", "date_debut": "2025-03-01", "date_fin": "2025-08-31",
         "note_globale": 16,
         "evaluation": "<p><b>Points forts :</b> Excellente maîtrise des outils informatiques.</p><p><b>Recommandation :</b> Embauche recommandée.</p>",
         "wf": "Approuvé"},
        {"email": "stagiaire2@kya-energy.com", "date_debut": "2025-03-01", "date_fin": "2025-08-31",
         "note_globale": 14,
         "evaluation": "<p><b>Points forts :</b> Bonne compréhension des processus comptables.</p>",
         "wf": "En attente DG"},
        {"email": "stagiaire3@kya-energy.com", "date_debut": "2025-06-01", "date_fin": "2025-11-30",
         "note_globale": 12,
         "evaluation": "<p><b>Points forts :</b> Bonne aptitude technique en électronique.</p>",
         "wf": "Brouillon"},
    ]

    for p in bilan_data:
        emp_id = employee_map.get(p["email"])
        if not emp_id:
            continue
        emp = frappe.get_doc("Employee", emp_id)
        try:
            doc = frappe.get_doc({
                "doctype": "Bilan Fin de Stage",
                "employee": emp_id,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "date_debut": p["date_debut"],
                "date_fin": p["date_fin"],
                "note_globale": p["note_globale"],
                "evaluation": p["evaluation"],
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            ds = 1 if p["wf"] in ["Approuvé", "Rejeté"] else 0
            frappe.db.set_value("Bilan Fin de Stage", doc.name,
                {"workflow_state": p["wf"], "docstatus": ds}, update_modified=False)
            print(f"  Bilan: {doc.name} [{p['wf']}]")
        except Exception as e:
            print(f"  Bilan error: {e}")
    frappe.db.commit()

    # ========================================
    # 12. ATTENDANCE
    # ========================================
    print("\n=== 12. CREATING ATTENDANCE RECORDS ===")
    all_employees = list(employee_map.values())
    statuses = ["Present", "Absent", "Half Day"]
    weights = [0.80, 0.08, 0.12]
    start_date = add_days(today(), -30)
    count = 0
    for day_offset in range(31):
        date = add_days(start_date, day_offset)
        dt = getdate(date)
        if dt.weekday() >= 5:
            continue
        for emp_id in all_employees:
            if frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": date}):
                continue
            status = random.choices(statuses, weights=weights, k=1)[0]
            try:
                att = frappe.get_doc({
                    "doctype": "Attendance",
                    "employee": emp_id,
                    "attendance_date": date,
                    "status": status,
                    "company": company,
                })
                att.flags.ignore_permissions = True
                att.flags.ignore_validate = True
                att.insert(ignore_permissions=True)
                frappe.db.set_value("Attendance", att.name, "docstatus", 1, update_modified=False)
                count += 1
            except Exception:
                pass
    frappe.db.commit()
    print(f"  Created {count} attendance records")

    # ========================================
    # 13. LEAVE TYPE & ALLOCATION
    # ========================================
    print("\n=== 13. CREATING LEAVE DATA ===")
    if not frappe.db.exists("Leave Type", "Congé Annuel"):
        frappe.get_doc({
            "doctype": "Leave Type",
            "leave_type_name": "Congé Annuel",
            "max_leaves_allowed": 30,
            "is_carry_forward": 1
        }).insert(ignore_permissions=True)
        print("  Created Leave Type: Congé Annuel")

    employees_only = [employee_map[e] for e in employee_map if not e.startswith("stagiaire")]
    for emp_id in employees_only:
        if frappe.db.exists("Leave Allocation", {"employee": emp_id, "leave_type": "Congé Annuel", "docstatus": 1}):
            continue
        try:
            la = frappe.get_doc({
                "doctype": "Leave Allocation",
                "employee": emp_id,
                "leave_type": "Congé Annuel",
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "new_leaves_allocated": 22,
            })
            la.flags.ignore_permissions = True
            la.flags.ignore_validate = True
            la.insert(ignore_permissions=True)
            frappe.db.set_value("Leave Allocation", la.name, "docstatus", 1, update_modified=False)
            print(f"  Leave allocated: {emp_id}")
        except Exception as e:
            print(f"  Leave alloc error: {e}")
    frappe.db.commit()

    # ========================================
    # 12. DEFAULT ENQUETE & EVALUATION DATA (KYA Services)
    # ========================================
    print("\n=== 12. DEFAULT ENQUETE & EVALUATION ===")

    # Create a default satisfaction survey if kya_services is installed
    try:
        if "KYA Form" in [d.name for d in frappe.get_all("DocType", filters={"module": "KYA Services"})]:
            if not frappe.db.exists("KYA Form", {"titre": "Enquête de Satisfaction Trimestrielle"}):
                survey = frappe.get_doc({
                    "doctype": "KYA Form",
                    "titre": "Enquête de Satisfaction Trimestrielle",
                    "type_formulaire": "Enquête",
                    "statut": "Brouillon",
                    "anonyme": 1,
                    "envoyer_tous": 1,
                    "description": "Enquête anonyme de satisfaction des employés — T1 2026",
                    "questions": [
                        {"libelle": "Comment évaluez-vous votre satisfaction générale au travail ?",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 1},
                        {"libelle": "L'ambiance de travail est-elle positive ?",
                         "type_reponse": "Oui / Non", "obligatoire": 1, "ordre": 2},
                        {"libelle": "Êtes-vous satisfait(e) de la communication interne ?",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 3},
                        {"libelle": "Les conditions de travail (bureaux, équipements) sont-elles satisfaisantes ?",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 4},
                        {"libelle": "Recommanderiez-vous KYA-Energy Group comme employeur ?",
                         "type_reponse": "Oui / Non", "obligatoire": 1, "ordre": 5},
                        {"libelle": "Quels aspects de votre travail souhaiteriez-vous améliorer ?",
                         "type_reponse": "Texte libre", "obligatoire": 0, "ordre": 6},
                        {"libelle": "Commentaires ou suggestions libres",
                         "type_reponse": "Texte libre", "obligatoire": 0, "ordre": 7},
                    ],
                })
                survey.flags.ignore_permissions = True
                survey.insert(ignore_permissions=True)
                print(f"  Enquête créée: {survey.name} (Brouillon, anonyme)")
            else:
                print("  Enquête satisfaction déjà existante")

            # Create a default evaluation campaign template (N+1 → N) for demo
            if not frappe.db.exists("KYA Form", {"titre": "Évaluation de Performance — Modèle"}):
                eval_form = frappe.get_doc({
                    "doctype": "KYA Form",
                    "titre": "Évaluation de Performance — Modèle",
                    "type_formulaire": "Évaluation",
                    "statut": "Brouillon",
                    "anonyme": 0,
                    "envoyer_tous": 0,
                    "description": "Modèle d'évaluation de performance trimestrielle (N+1 évalue N). À activer par l'admin pour lancer une campagne.",
                    "questions": [
                        {"libelle": "Niveau d'atteinte des objectifs individuels",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 1},
                        {"libelle": "Compétences spécifiques liées au poste",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 2},
                        {"libelle": "Qualité et précision du travail fourni",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 3},
                        {"libelle": "Capacité à collaborer avec les autres",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 4},
                        {"libelle": "Efficacité des compétences en communication",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 5},
                        {"libelle": "Capacité à identifier et résoudre des problèmes",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 6},
                        {"libelle": "Niveau d'engagement et de motivation",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 7},
                        {"libelle": "Incarnation des valeurs de l'organisation",
                         "type_reponse": "Note 1-5", "obligatoire": 1, "ordre": 8},
                        {"libelle": "Points forts observés",
                         "type_reponse": "Texte libre", "obligatoire": 0, "ordre": 9},
                        {"libelle": "Axes d'amélioration suggérés",
                         "type_reponse": "Texte libre", "obligatoire": 0, "ordre": 10},
                    ],
                })
                eval_form.flags.ignore_permissions = True
                eval_form.insert(ignore_permissions=True)
                print(f"  Évaluation modèle créée: {eval_form.name} (Brouillon)")
            else:
                print("  Évaluation modèle déjà existante")
        else:
            print("  KYA Services non installé — skip enquêtes/évaluations")
    except Exception as e:
        print(f"  Enquête/Évaluation error: {e}")

    frappe.db.commit()

    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "="*60)
    print("SEEDING COMPLETE!")
    print("="*60)
    print(f"Company: {company}")
    print(f"Users/Employees: {len(users_data)}")
    print(f"Attendance records: {count}")
    print()
    print("LOGIN CREDENTIALS (password: Kya@2025):")
    print("-" * 50)
    for u in users_data:
        role_desc = u["roles"][1] if len(u["roles"]) > 1 else u["roles"][0]
        print(f"  {u['email']:35s} {u['first_name']} {u['last_name']}")

    # Re-enable server scripts
    for ss in server_scripts:
        frappe.db.set_value("Server Script", ss, "disabled", 0, update_modified=False)
    frappe.db.commit()

    frappe.flags.in_import = False

import frappe

def full_workspace_fix():
    print("--- Fully Fixing Workspaces (RH & Op + Stagiaires) ---")
    
    # --- 1. Workspace KYA RH & Op ---
    ws1_name = "KYA RH & Op"
    if not frappe.db.exists("Workspace", ws1_name):
        ws1 = frappe.get_doc({
            "doctype": "Workspace", "name": ws1_name, "label": ws1_name, "title": ws1_name,
            "type": "Workspace", "icon": "users", "public": 1, "module": "KYA HR"
        }).insert(ignore_permissions=True)
    else:
        ws1 = frappe.get_doc("Workspace", ws1_name)

    ws1.links = []
    ws1_links = [
        {"label": "Demandes d'Achat", "link_to": "KYA Purchase Request", "link_type": "DocType"},
        {"label": "Tickets de Sortie", "link_to": "KYA Exit Ticket", "link_type": "DocType"},
        {"label": "Planning de Congés", "link_to": "KYA Leave Planning", "link_type": "DocType"},
        {"label": "Suivi Carburant", "link_to": "KYA Fuel Log", "link_type": "DocType"}
    ]
    for l in ws1_links:
        ws1.append("links", l)
    ws1.save(ignore_permissions=True)
    print(f"✅ Workspace {ws1_name} updated.")

    # --- 2. Workspace KYA Stagiaires ---
    ws2_name = "KYA Stagiaires"
    if not frappe.db.exists("Workspace", ws2_name):
        ws2 = frappe.get_doc({
            "doctype": "Workspace", "name": ws2_name, "label": ws2_name, "title": ws2_name,
            "type": "Workspace", "icon": "educator", "public": 1, "module": "KYA HR"
        }).insert(ignore_permissions=True)
    else:
        ws2 = frappe.get_doc("Workspace", ws2_name)

    ws2.links = []
    ws2_links = [
        {"label": "Liste des Stagiaires", "link_to": "Employee", "link_type": "DocType"},
        {"label": "Demandes de Permission", "link_to": "KYA Permission Request", "link_type": "DocType"},
        {"label": "Présences (Pointage)", "link_to": "Attendance", "link_type": "DocType"},
    ]
    for l in ws2_links:
        ws2.append("links", l)
    
    # Add Number Cards for Stagiaires
    ws2.number_cards = []
    cards = [
        {"name": "Stagiaires Actifs", "label": "Stagiaires Actifs", "function": "Count", "parent_dt": "Employee", "filters": "[[\"Employee\",\"employment_type\",\"=\",\"Intern\"],[\"Employee\",\"status\",\"=\",\"Active\"]]" },
        {"name": "Demandes Permissions", "label": "Permissions en Attente", "function": "Count", "parent_dt": "KYA Permission Request", "filters": "[[\"KYA Permission Request\",\"status\",\"=\",\"En attente\"]]" }
    ]
    for c in cards:
        if not frappe.db.exists("Number Card", c["name"]):
            frappe.get_doc({
                "doctype": "Number Card", "name": c["name"], "label": c["label"], "function": c["function"],
                "document_type": c["parent_dt"], "filters_config": c["filters"]
            }).insert(ignore_permissions=True)
        ws2.append("number_cards", {"number_card": c["name"], "label": c["label"]})

    ws2.save(ignore_permissions=True)
    print(f"✅ Workspace {ws2_name} updated.")
    
    frappe.db.commit()
    print("✅ Workspace Fully Updated.")

if __name__ == "__main__":
    full_workspace_fix()

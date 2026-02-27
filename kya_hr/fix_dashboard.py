import frappe

def create_dashboard_and_charts():
    print("--- Creating Dashboards & Charts ---")
    
    # 1. Number Cards
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
            print(f"Created Number Card: {c['name']}")

    # 2. Workspace integration (Shortcut)
    ws_name = "KYA RH & Op"
    if frappe.db.exists("Workspace", ws_name):
        ws = frappe.get_doc("Workspace", ws_name)
        # Clear existing cards to avoid duplicates
        ws.number_cards = []
        for c in cards:
            ws.append("number_cards", {"number_card": c["name"], "label": c["label"]})
        ws.save(ignore_permissions=True)
        print("Updated Workspace with Number Cards")

if __name__ == "__main__":
    create_dashboard_and_charts()
    frappe.db.commit()

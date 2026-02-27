import frappe
import traceback

def create_roles():
    print("--- 0. Roles Setup ---")
    roles = ["Responsable Stage", "Service RH"]
    for r in roles:
        if not frappe.db.exists("Role", r):
            frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(ignore_permissions=True)
            print(f"Created Role: {r}")

def create_workflow_actions(actions):
    for a in actions:
        if not frappe.db.exists("Workflow Action Master", a):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert(ignore_permissions=True)

def deploy_leave_planning_workflow():
    print("--- 1. Leave Planning Workflow ---")
    states = ["Brouillon", "En attente Supérieur", "En attente RH", "Approuvé", "Rejeté"]
    for s in states:
        if not frappe.db.exists("Workflow State", s):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s}).insert(ignore_permissions=True)

    create_workflow_actions(["Soumettre", "Approuver (Chef)", "Approuver (RH)", "Rejeter"])

    wf_name = "Flux de Planning Congés"
    if frappe.db.exists("Workflow", wf_name):
        frappe.delete_doc("Workflow", wf_name)
    
    frappe.get_doc({
        "doctype": "Workflow", "workflow_name": wf_name, "document_type": "KYA Leave Planning", "is_active": 1,
        "states": [
            {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee", "update_field": "status", "update_value": "Brouillon"},
            {"state": "En attente Supérieur", "doc_status": 0, "allow_edit": "Chef de Service", "update_field": "status", "update_value": "En attente"},
            {"state": "En attente RH", "doc_status": 0, "allow_edit": "Service RH", "update_field": "status", "update_value": "En attente"},
            {"state": "Approuvé", "doc_status": 1, "allow_edit": "Service RH", "update_field": "status", "update_value": "Approuvé"},
            {"state": "Rejeté", "doc_status": 0, "allow_edit": "Chef de Service", "update_field": "status", "update_value": "Rejeté"}
        ],
        "transitions": [
            {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente Supérieur", "allowed": "Employee"},
            {"state": "En attente Supérieur", "action": "Approuver (Chef)", "next_state": "En attente RH", "allowed": "Chef de Service"},
            {"state": "En attente Supérieur", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Chef de Service"},
            {"state": "En attente RH", "action": "Approuver (RH)", "next_state": "Approuvé", "allowed": "Service RH"},
            {"state": "En attente RH", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Service RH"}
        ]
    }).insert(ignore_permissions=True)
    print("Created Flux de Planning Congés")

def deploy_permission_request_workflow():
    print("--- 2. Permission Request Workflow (Stagiaires) ---")
    states = ["Brouillon", "En attente Supérieur", "En attente Responsable Stage", "Approuvé", "Rejeté"]
    for s in states:
        if not frappe.db.exists("Workflow State", s):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s}).insert(ignore_permissions=True)

    create_workflow_actions(["Demander", "Accorder (Supérieur)", "Valider (Stage)", "Rejeter"])

    wf_name = "Flux de Permission Stagiaire"
    if frappe.db.exists("Workflow", wf_name):
        frappe.delete_doc("Workflow", wf_name)
    
    frappe.get_doc({
        "doctype": "Workflow", "workflow_name": wf_name, "document_type": "KYA Permission Request", "is_active": 1,
        "states": [
            {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee", "update_field": "status", "update_value": "Brouillon"},
            {"state": "En attente Supérieur", "doc_status": 0, "allow_edit": "Chef de Service", "update_field": "status", "update_value": "En attente"},
            {"state": "En attente Responsable Stage", "doc_status": 0, "allow_edit": "Responsable Stage", "update_field": "status", "update_value": "En attente"},
            {"state": "Approuvé", "doc_status": 1, "allow_edit": "Responsable Stage", "update_field": "status", "update_value": "Approuvé"},
            {"state": "Rejeté", "doc_status": 0, "allow_edit": "Chef de Service", "update_field": "status", "update_value": "Rejeté"}
        ],
        "transitions": [
            {"state": "Brouillon", "action": "Demander", "next_state": "En attente Supérieur", "allowed": "Employee"},
            {"state": "En attente Supérieur", "action": "Accorder (Supérieur)", "next_state": "En attente Responsable Stage", "allowed": "Chef de Service"},
            {"state": "En attente Supérieur", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Chef de Service"},
            {"state": "En attente Responsable Stage", "action": "Valider (Stage)", "next_state": "Approuvé", "allowed": "Responsable Stage"},
            {"state": "En attente Responsable Stage", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Responsable Stage"}
        ]
    }).insert(ignore_permissions=True)
    print("Created Flux de Permission Stagiaire")

def setup_analytics():
    print("--- 3. Analytics & Dashboards ---")
    # Simple Number Cards for Stagiaires
    cards = [
        {"name": "Total Stagiaires Actifs", "label": "Stagiaires Actifs", "function": "Count", "dt": "Employee", "filters": "[[\"Employee\",\"employment_type\",\"=\",\"Intern\"],[\"Employee\",\"status\",\"=\",\"Active\"]]" },
        {"name": "Permissions en Attente", "label": "Permissions en Attente", "function": "Count", "dt": "KYA Permission Request", "filters": "[[\"KYA Permission Request\",\"status\",\"=\",\"En attente\"]]" }
    ]
    for c in cards:
        if not frappe.db.exists("Number Card", c["name"]):
            frappe.get_doc({
                "doctype": "Number Card", "name": c["name"], "label": c["label"], "function": c["function"],
                "parent_doctype": c["dt"], "filters_config": c["filters"]
            }).insert(ignore_permissions=True)
    
    # Simple Dashboard
    db_name = "Dashboard RH KYA"
    if not frappe.db.exists("Dashboard", db_name):
        frappe.get_doc({
            "doctype": "Dashboard", "name": db_name, "dashboard_name": db_name,
            "cards": [{"card": "Total Stagiaires Actifs"}, {"card": "Permissions en Attente"}]
        }).insert(ignore_permissions=True)
        print("Created Dashboard RH KYA")

def update_workspace():
    print("--- 4. Final Workspace Update ---")
    ws_name = "KYA RH & Op"
    if frappe.db.exists("Workspace", ws_name):
        ws = frappe.get_doc("Workspace", ws_name)
        # Add dashboards
        ws.append("dashboards", {"dashboard": "Dashboard RH KYA"})
        # Ensure all links are there
        links = [
            {"label": "Demandes de Permission", "link_to": "KYA Permission Request"},
            {"label": "Planning de Congés", "link_to": "KYA Leave Planning"},
            {"label": "Stagiaires", "link_to": "Employee"}
        ]
        existing = [l.link_to for l in ws.links]
        for l in links:
            if l["link_to"] not in existing:
                ws.append("links", {"type": "Link", "label": l["label"], "link_type": "DocType", "link_to": l["link_to"]})
        ws.save(ignore_permissions=True)
        print("Updated Workspace KYA RH & Op with Dashboards and Links")

def main():
    try:
        create_roles()
        deploy_leave_planning_workflow()
        deploy_permission_request_workflow()
        setup_analytics()
        update_workspace()
        frappe.db.commit()
        print("✅ Finished Deployment of Stagiaires & Leave Planning.")
    except Exception as e:
        print(f"Error: {repr(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

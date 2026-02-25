
import frappe
import json

def verify():
    results = {
        "DocTypes": frappe.db.get_list("DocType", filters={"module": "KYA HR"}, pluck="name"),
        "Roles": [r for r in ["Responsable Stage", "Chef de Service", "DGA", "DG", "Supérieur Immédiat"] if frappe.db.exists("Role", r)],
        "Workspaces": frappe.db.get_list("Workspace", filters={"module": "KYA HR"}, pluck="name"),
        "Workflows": frappe.db.get_list("Workflow", filters={"document_type": ["in", ["KYA Permission Request", "KYA Leave Planning", "KYA Exit Ticket", "KYA Mission"]]}, pluck="workflow_name"),
        "Notifications": frappe.db.get_list("Notification", filters={"enabled": 1}, pluck="name")
    }
    
    print("---VERIFICATION_START---")
    print(json.dumps(results, indent=2))
    print("---VERIFICATION_END---")

if __name__ == "__main__":
    verify()

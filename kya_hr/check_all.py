
import frappe
import json

def check():
    results = {
        "DocTypes": [d for d in ["KYA Permission Request", "KYA Leave Planning", "KYA Exit Ticket", "KYA Exit Ticket Passenger", "KYA Fuel Log", "KYA Mission"] if frappe.db.exists("DocType", d)],
        "Workspaces": [ws for ws in ["Stagiaires", "Logistique"] if frappe.db.exists("Workspace", ws)],
        "Roles": [r for r in ["Responsable Stage", "Chef de Service", "DGA", "DG", "Supérieur Immédiat"] if frappe.db.exists("Role", r)],
        "Workflows": [w for w in ["Workflow Permission Stagiaire", "Workflow Ticket de Sortie"] if frappe.db.exists("Workflow", w)]
    }
    print("---RESULTS_START---")
    print(json.dumps(results, indent=2))
    print("---RESULTS_END---")

if __name__ == "__main__":
    check()

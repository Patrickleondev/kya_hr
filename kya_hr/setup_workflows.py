import frappe
import json

def execute():
    # 1. Workflow Permission Request (Stagiaires)
    create_permission_request_workflow()
    
    # 2. Workflow Exit Ticket (Logistique)
    create_exit_ticket_workflow()
    
    # 3. Workflow Leave Planning (Simple)
    create_leave_planning_workflow()

    frappe.db.commit()
    print("✅ All Workflows for KYA Extensions created successfully!")

def create_permission_request_workflow():
    workflow_name = "Workflow Permission Stagiaire"
    if not frappe.db.exists("Workflow", workflow_name):
        frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": workflow_name,
            "document_type": "KYA Permission Request",
            "workflow_state_field": "workflow_state",
            "is_active": 1,
            "states": [
                {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee", "update_field": "status", "update_value": "Brouillon"},
                {"state": "En attente Supérieur", "doc_status": 0, "allow_edit": "Supérieur Immédiat", "update_field": "status", "update_value": "En attente"},
                {"state": "En attente Responsable Stage", "doc_status": 0, "allow_edit": "Responsable Stage", "update_field": "status", "update_value": "En attente"},
                {"state": "En attente DG", "doc_status": 0, "allow_edit": "DG", "update_field": "status", "update_value": "En attente"},
                {"state": "Approuvé", "doc_status": 1, "allow_edit": "HR Manager", "update_field": "status", "update_value": "Approuvé"},
                {"state": "Rejeté", "doc_status": 2, "allow_edit": "HR Manager", "update_field": "status", "update_value": "Rejeté"}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente Supérieur", "allowed": "Employee"},
                {"state": "En attente Supérieur", "action": "Approuver (Supérieur)", "next_state": "En attente Responsable Stage", "allowed": "Supérieur Immédiat"},
                {"state": "En attente Supérieur", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Supérieur Immédiat"},
                {"state": "En attente Responsable Stage", "action": "Approuver (Resp.)", "next_state": "En attente DG", "allowed": "Responsable Stage"},
                {"state": "En attente Responsable Stage", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Responsable Stage"},
                {"state": "En attente DG", "action": "Approuver (DG)", "next_state": "Approuvé", "allowed": "DG"},
                {"state": "En attente DG", "action": "Rejeter", "next_state": "Rejeté", "allowed": "DG"}
            ]
        }).insert()
        print(f"Workflow {workflow_name} created")

def create_exit_ticket_workflow():
    workflow_name = "Workflow Ticket de Sortie"
    if not frappe.db.exists("Workflow", workflow_name):
        frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": workflow_name,
            "document_type": "KYA Exit Ticket",
            "workflow_state_field": "workflow_state",
            "is_active": 1,
            "states": [
                {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee", "update_field": "status", "update_value": "Brouillon"},
                {"state": "En attente Chef", "doc_status": 0, "allow_edit": "Chef de Service", "update_field": "status", "update_value": "En attente Chef"},
                {"state": "En attente RH", "doc_status": 0, "allow_edit": "HR Manager", "update_field": "status", "update_value": "En attente RH"},
                {"state": "En attente DGA", "doc_status": 0, "allow_edit": "DGA", "update_field": "status", "update_value": "En attente DGA"},
                {"state": "Approuvé", "doc_status": 1, "allow_edit": "HR Manager", "update_field": "status", "update_value": "Approuvé"},
                {"state": "Rejeté", "doc_status": 2, "allow_edit": "HR Manager", "update_field": "status", "update_value": "Rejeté"}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente Chef", "allowed": "Employee"},
                {"state": "En attente Chef", "action": "Valider", "next_state": "En attente RH", "allowed": "Chef de Service"},
                {"state": "En attente Chef", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Chef de Service"},
                
                # Exception : Le RH peut approuver directement s'il y a urgence/absence
                {"state": "En attente Chef", "action": "Approver (RH - Urgence)", "next_state": "Approuvé", "allowed": "HR Manager"},
                
                {"state": "En attente RH", "action": "Valider", "next_state": "En attente DGA", "allowed": "HR Manager"},
                {"state": "En attente RH", "action": "Approuver (RH Final)", "next_state": "Approuvé", "allowed": "HR Manager"}, # Si DGA absent
                {"state": "En attente RH", "action": "Rejeter", "next_state": "Rejeté", "allowed": "HR Manager"},
                
                {"state": "En attente DGA", "action": "Approuver", "next_state": "Approuvé", "allowed": "DGA"},
                {"state": "En attente DGA", "action": "Rejeter", "next_state": "Rejeté", "allowed": "DGA"}
            ]
        }).insert()
        print(f"Workflow {workflow_name} created")

def create_leave_planning_workflow():
    workflow_name = "Workflow Planning de Congés"
    if not frappe.db.exists("Workflow", workflow_name):
        frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": workflow_name,
            "document_type": "KYA Leave Planning",
            "workflow_state_field": "workflow_state",
            "is_active": 1,
            "states": [
                {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee", "update_field": "status", "update_value": "Brouillon"},
                {"state": "En attente", "doc_status": 0, "allow_edit": "HR Manager", "update_field": "status", "update_value": "En attente"},
                {"state": "Approuvé", "doc_status": 1, "allow_edit": "HR Manager", "update_field": "status", "update_value": "Approuvé"},
                {"state": "Rejeté", "doc_status": 2, "allow_edit": "HR Manager", "update_field": "status", "update_value": "Rejeté"}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente", "allowed": "Employee"},
                {"state": "En attente", "action": "Approuver", "next_state": "Approuvé", "allowed": "HR Manager"},
                {"state": "En attente", "action": "Rejeter", "next_state": "Rejeté", "allowed": "HR Manager"}
            ]
        }).insert()
        print(f"Workflow {workflow_name} created")

if __name__ == "__main__":
    execute()

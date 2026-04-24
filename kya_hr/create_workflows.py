import frappe

def create_pv_workflow():
    if not frappe.db.exists("Workflow", "PV Sortie Materiel Flow"):
        wf = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "PV Sortie Materiel Flow",
            "document_type": "PV Sortie Materiel",
            "workflow_state_field": "statut",
            "is_active": 1,
            "states": [
                {"state": "Brouillon", "doc_status": 0, "allow_edit": "All"},
                {"state": "En attente Magasin", "doc_status": 0, "allow_edit": "System Manager"},
                {"state": "En attente Audit", "doc_status": 0, "allow_edit": "System Manager"},
                {"state": "En attente DGA", "doc_status": 0, "allow_edit": "System Manager"},
                {"state": "Approuv\u00e9", "doc_status": 1, "allow_edit": "System Manager"},
                {"state": "Rejet\u00e9", "doc_status": 2, "allow_edit": "System Manager"}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Envoyer au Magasin", "next_state": "En attente Magasin", "allowed": "All"},
                {"state": "En attente Magasin", "action": "Valider Magasin", "next_state": "En attente Audit", "allowed": "System Manager"},
                {"state": "En attente Audit", "action": "Valider Audit", "next_state": "En attente DGA", "allowed": "System Manager"},
                {"state": "En attente DGA", "action": "Approuver Final", "next_state": "Approuv\u00e9", "allowed": "System Manager"},
                {"state": "En attente Magasin", "action": "Rejeter", "next_state": "Rejet\u00e9", "allowed": "System Manager"},
                {"state": "En attente Audit", "action": "Rejeter", "next_state": "Rejet\u00e9", "allowed": "System Manager"},
                {"state": "En attente DGA", "action": "Rejeter", "next_state": "Rejet\u00e9", "allowed": "System Manager"}
            ]
        })
        wf.insert(ignore_permissions=True)
        print("Workflow PV Sortie Materiel Flow created.")

def create_permission_workflow():
    if not frappe.db.exists("Workflow", "Permission Sortie Flow"):
        wf = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "Permission Sortie Flow",
            "document_type": "Permission Sortie Stagiaire",
            "workflow_state_field": "statut",
            "is_active": 1,
            "states": [
                {"state": "Brouillon", "doc_status": 0, "allow_edit": "All"},
                {"state": "En attente", "doc_status": 0, "allow_edit": "System Manager"},
                {"state": "Approuv\u00e9", "doc_status": 1, "allow_edit": "System Manager"},
                {"state": "Rejet\u00e9", "doc_status": 2, "allow_edit": "System Manager"}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Soumettre pour Approbation", "next_state": "En attente", "allowed": "All"},
                {"state": "En attente", "action": "Approuver", "next_state": "Approuv\u00e9", "allowed": "System Manager"},
                {"state": "En attente", "action": "Rejeter", "next_state": "Rejet\u00e9", "allowed": "System Manager"}
            ]
        })
        wf.insert(ignore_permissions=True)
        print("Workflow Permission Sortie Flow created.")

def run():
    create_pv_workflow()
    create_permission_workflow()
    frappe.db.commit()

if __name__ == "__main__":
    run()

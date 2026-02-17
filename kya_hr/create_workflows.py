import frappe

def create_workflows():
    """
    Crée les flux de travail (Workflows) personnalisés pour KYA-Energy Group.
    """

    # 1. États du Flux de Travail
    workflow_states = [
        "Brouillon", 
        "En attente du Supérieur Immédiat", 
        "En attente du Responsable des Stagiaires", 
        "En attente RH", 
        "En attente du DG", 
        "Approuvé", 
        "Rejeté"
    ]

    for s in workflow_states:
        if not frappe.db.exists("Workflow State", s):
            doc = frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": s,
                "style": "Primary" if "Approuvé" in s else "Danger" if "Rejeté" in s else "Warning"
            })
            doc.insert()

    # 2. Actions du Flux
    actions = ["Soumettre", "Approuver", "Rejeter", "Annuler"]
    for a in actions:
        if not frappe.db.exists("Workflow Action Master", a):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert()

    # 3. Définition des Flux
    
    # --- Flux : Autorisation de Sortie Stagiaires ---
    if not frappe.db.exists("Workflow", "Flux Autorisation de Sortie Stagiaires"):
        wf_stagiaire = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "Flux Autorisation de Sortie Stagiaires",
            "document_type": "Leave Application",
            "is_active": 1,
            "workflow_state_field": "workflow_state",
            "states": [
                {"state": "Brouillon", "allow_edit": "Employee", "doc_status": 0},
                {"state": "En attente du Supérieur Immédiat", "allow_edit": "Supérieur Immédiat", "doc_status": 0},
                {"state": "En attente du Responsable des Stagiaires", "allow_edit": "Responsable des Stagiaires", "doc_status": 0},
                {"state": "En attente du DG", "allow_edit": "Directeur Général", "doc_status": 0},
                {"state": "Approuvé", "allow_edit": "Directeur Général", "doc_status": 1},
                {"state": "Rejeté", "allow_edit": "Directeur Général", "doc_status": 2}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente du Supérieur Immédiat", "allowed": "Employee"},
                {"state": "En attente du Supérieur Immédiat", "action": "Approuver", "next_state": "En attente du Responsable des Stagiaires", "allowed": "Supérieur Immédiat"},
                {"state": "En attente du Supérieur Immédiat", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Supérieur Immédiat"},
                {"state": "En attente du Responsable des Stagiaires", "action": "Approuver", "next_state": "En attente du DG", "allowed": "Responsable des Stagiaires"},
                {"state": "En attente du Responsable des Stagiaires", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Responsable des Stagiaires"},
                {"state": "En attente du DG", "action": "Approuver", "next_state": "Approuvé", "allowed": "Directeur Général"},
                {"state": "En attente du DG", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Directeur Général"}
            ]
        })
        wf_stagiaire.insert()

    # --- Flux : Congés et Sortie Employés ---
    if not frappe.db.exists("Workflow", "Flux Congés et Sortie Employés"):
        wf_employe = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "Flux Congés et Sortie Employés",
            "document_type": "Leave Application",
            "is_active": 1,
            "workflow_state_field": "workflow_state",
            "states": [
                {"state": "Brouillon", "allow_edit": "Employee", "doc_status": 0},
                {"state": "En attente du Supérieur Immédiat", "allow_edit": "Supérieur Immédiat", "doc_status": 0},
                {"state": "En attente RH", "allow_edit": "Responsable RH", "doc_status": 0},
                {"state": "En attente du DG", "allow_edit": "Directeur Général", "doc_status": 0},
                {"state": "Approuvé", "allow_edit": "Directeur Général", "doc_status": 1},
                {"state": "Rejeté", "allow_edit": "Directeur Général", "doc_status": 2}
            ],
            "transitions": [
                # 1. DEPUIS BROUILLON (Soumission)
                
                # Cas DRH (Manager RH) -> Direct DG
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente du DG", "allowed": "Employee", 
                 "condition": "'Responsable RH' in frappe.get_roles(doc.owner) and frappe.db.get_value('Employee', doc.employee, 'designation') == 'Manager RH'"},
                
                # Cas Assistant RH -> Vers Responsable RH
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente RH", "allowed": "Employee", 
                 "condition": "frappe.db.get_value('Employee', doc.employee, 'designation') == 'Assistant RH'"},

                # Cas Chef d'équipe -> Vers RH directly (bypasse Supérieur Immédiat)
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente RH", "allowed": "Employee", 
                 "condition": "frappe.db.get_value('Employee', doc.employee, 'designation') == 'Chef d\\'équipe'"},
                
                # Cas Standard (Autres employés) -> Vers Supérieur Immédiat
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente du Supérieur Immédiat", "allowed": "Employee", 
                 "condition": "frappe.db.get_value('Employee', doc.employee, 'designation') not in ['Manager RH', 'Assistant RH', 'Chef d\\'équipe']"},

                # 2. DEPUIS SUPÉRIEUR IMMÉDIAT
                {"state": "En attente du Supérieur Immédiat", "action": "Approuver", "next_state": "En attente RH", "allowed": "Supérieur Immédiat"},
                {"state": "En attente du Supérieur Immédiat", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Supérieur Immédiat"},
                
                # 3. DEPUIS RH
                {"state": "En attente RH", "action": "Approuver", "next_state": "En attente du DG", "allowed": "Responsable RH"},
                {"state": "En attente RH", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Responsable RH"},
                
                # 4. DEPUIS DG
                {"state": "En attente du DG", "action": "Approuver", "next_state": "Approuvé", "allowed": "Directeur Général"},
                {"state": "En attente du DG", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Directeur Général"}
            ]
        })
        wf_employe.insert()

    frappe.db.commit()
    print("Flux de travail KYA créés avec succès !")

if __name__ == "__main__":
    create_workflows()

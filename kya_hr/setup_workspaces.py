import frappe
import json

def execute():
    # 1. Create Intern Workspace
    create_intern_workspace()
    
    # 2. Create Logistics Workspace
    create_logistics_workspace()

    frappe.db.commit()
    print("✅ Workspaces for KYA Extensions created successfully!")

def create_intern_workspace():
    workspace_name = "Stagiaires"
    if not frappe.db.exists("Workspace", workspace_name):
        frappe.get_doc({
            "doctype": "Workspace",
            "name": workspace_name,
            "label": "Stagiaires",
            "module": "kya_hr",
            "extends": 0,
            "is_standard": 1,
            "public": 1,
            "icon": "user",
            "links": [
                {"link_type": "DocType", "link_to": "Employee", "label": "Liste des Stagiaires", "link_count": "Active Interns"},
                {"link_type": "DocType", "link_to": "KYA Permission Request", "label": "Demandes de Permission", "link_count": "Pending Permissions"},
                {"link_type": "DocType", "link_to": "KYA Leave Planning", "label": "Planning des Congés"}
            ],
            "charts": [
                {"chart_name": "Répartition par Statut Stagiaire", "label": "Statuts"}
            ],
            "number_cards": [
                {"number_card_name": "Nombre de Stagiaires Actifs", "label": "Actifs"}
            ]
        }).insert()
        print(f"Workspace {workspace_name} created")

def create_logistics_workspace():
    workspace_name = "Logistique"
    if not frappe.db.exists("Workspace", workspace_name):
        frappe.get_doc({
            "doctype": "Workspace",
            "name": workspace_name,
            "label": "Logistique",
            "module": "kya_hr",
            "extends": 0,
            "is_standard": 1,
            "public": 1,
            "icon": "truck",
            "links": [
                {"link_type": "DocType", "link_to": "Vehicle", "label": "Parc Automobile"},
                {"link_type": "DocType", "link_to": "KYA Exit Ticket", "label": "Tickets de Sortie"},
                {"link_type": "DocType", "link_to": "KYA Fuel Log", "label": "Suivi Carburant"},
                {"link_type": "DocType", "link_to": "KYA Mission", "label": "Suivi des Missions"}
            ],
            "charts": [
                {"chart_name": "Consommation Carburant par Véhicule", "label": "Carburant"}
            ]
        }).insert()
        print(f"Workspace {workspace_name} created")

if __name__ == "__main__":
    execute()

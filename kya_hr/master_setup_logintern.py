
import frappe
import json

def execute():
    print("🚀 Starting Master Setup for Interns and Logistics...")
    
    # 1. Create Roles
    create_roles()
    
    # 2. Create DocTypes
    create_doctypes()

    # 3. Create Workflows
    create_workflows()

    # 4. Create Workspaces
    create_workspaces()

    # 5. Create Analytics
    import setup_analytics
    setup_analytics.execute()

    # 6. Create Notifications
    create_notifications()

    # 7. Create Client Scripts
    import setup_client_scripts
    setup_client_scripts.execute()

    frappe.db.commit()
    print("✅ Master Setup Complete!")

def create_roles():
    roles = ["Responsable Stage", "Chef de Service", "DGA", "DG", "Supérieur Immédiat"]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert()
            print(f"Role {role} created")

def create_doctypes():
    # 2.1 Exit Ticket Passenger (Child Table) - MUST BE FIRST
    if not frappe.db.exists("DocType", "KYA Exit Ticket Passenger"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Exit Ticket Passenger",
            "module": "KYA HR",
            "istable": 1,
            "custom": 1,
            "fields": [
                {"label": "Employé", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"label": "Nom", "fieldname": "employee_name", "fieldtype": "Read Only", "fetch_from": "employee.employee_name", "in_list_view": 1}
            ]
        }).insert()
        print("DocType KYA Exit Ticket Passenger created")

    # 2.2 Permission Request
    if not frappe.db.exists("DocType", "KYA Permission Request"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Permission Request",
            "module": "KYA HR",
            "custom": 1,
            "autoname": "PR-.####",
            "naming_rule": "Expression (old style)",
            "fields": [
                {"label": "Employé (Stagiaire)", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"label": "Prénom et Nom", "fieldname": "employee_name", "fieldtype": "Read Only", "fetch_from": "employee.employee_name"},
                {"label": "Type de Permission", "fieldname": "permission_type", "fieldtype": "Select", "options": "Absence\nRetard\nSortie Anticipée", "reqd": 1},
                {"label": "Section Dates", "fieldtype": "Section Break"},
                {"label": "Date de Début", "fieldname": "from_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Date de Fin", "fieldname": "to_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Colonne 2", "fieldtype": "Column Break"},
                {"label": "Heure de Début", "fieldname": "from_time", "fieldtype": "Time", "depends_on": 'eval:doc.permission_type!="Absence"'},
                {"label": "Heure de Fin", "fieldname": "to_time", "fieldtype": "Time", "depends_on": 'eval:doc.permission_type!="Absence"'},
                {"label": "Section Raison", "fieldtype": "Section Break"},
                {"label": "Raison", "fieldname": "reason", "fieldtype": "Small Text", "reqd": 1},
                {"label": "Statut", "fieldname": "status", "fieldtype": "Select", "options": "Brouillon\nEn attente\nApprouvé\nRejeté", "default": "Brouillon", "read_only": 1, "in_list_view": 1},
                {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Link", "options": "Workflow State", "hidden": 1}
            ],
            "permissions": [
                {"role": "Employee", "read": 1, "write": 1, "create": 1, "if_owner": 1},
                {"role": "HR User", "read": 1, "write": 1, "create": 1},
                {"role": "HR Manager", "read": 1, "write": 1, "create": 1}
            ]
        }).insert()
        print("DocType KYA Permission Request created")

    # 2.3 Leave Planning
    if not frappe.db.exists("DocType", "KYA Leave Planning"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Leave Planning",
            "module": "KYA HR",
            "custom": 1,
            "autoname": "LP-.####",
            "naming_rule": "Expression (old style)",
            "fields": [
                {"label": "Employé", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"label": "Période demandée", "fieldname": "period", "fieldtype": "Section Break"},
                {"label": "Date de Début", "fieldname": "from_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Date de Fin", "fieldname": "to_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Colonne 2", "fieldtype": "Column Break"},
                {"label": "Justification", "fieldname": "reason", "fieldtype": "Small Text", "reqd": 1},
                {"label": "Motif de Rejet", "fieldname": "rejection_reason", "fieldtype": "Small Text", "read_only_depends_on": 'eval:doc.status!="Rejeté"'},
                {"label": "Statut", "fieldname": "status", "fieldtype": "Select", "options": "Brouillon\nEn attente\nApprouvé\nRejeté", "default": "Brouillon", "read_only": 1, "in_list_view": 1},
                {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Link", "options": "Workflow State", "hidden": 1}
            ],
            "permissions": [
                {"role": "Employee", "read": 1, "write": 1, "create": 1, "if_owner": 1},
                {"role": "HR User", "read": 1, "write": 1, "create": 1},
                {"role": "HR Manager", "read": 1, "write": 1, "create": 1}
            ]
        }).insert()
        print("DocType KYA Leave Planning created")

    # 2.4 Exit Ticket
    if not frappe.db.exists("DocType", "KYA Exit Ticket"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Exit Ticket",
            "module": "KYA HR",
            "custom": 1,
            "autoname": "ET-.####",
            "naming_rule": "Expression (old style)",
            "fields": [
                {"label": "Demandeur", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"label": "Passagers", "fieldname": "passengers", "fieldtype": "Table", "options": "KYA Exit Ticket Passenger"},
                {"label": "Section Logistique", "fieldtype": "Section Break"},
                {"label": "Véhicule", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "reqd": 1, "in_list_view": 1},
                {"label": "Chauffeur", "fieldname": "driver", "fieldtype": "Link", "options": "Employee"},
                {"label": "Colonne 2", "fieldtype": "Column Break"},
                {"label": "Destination", "fieldname": "destination", "fieldtype": "Data", "reqd": 1},
                {"label": "Motif de Sortie", "fieldname": "reason", "fieldtype": "Small Text", "reqd": 1},
                {"label": "Section Temps", "fieldtype": "Section Break"},
                {"label": "Heure de Sortie", "fieldname": "departure_time", "fieldtype": "Time", "reqd": 1},
                {"label": "Heure de Retour Prévue", "fieldname": "expected_return_time", "fieldtype": "Time"},
                {"label": "Heure de Retour Réelle", "fieldname": "actual_return_time", "fieldtype": "Time", "read_only": 1},
                {"label": "Statut", "fieldname": "status", "fieldtype": "Select", "options": "Brouillon\nEn attente Chef\nEn attente RH\nEn attente DGA\nApprouvé\nRejeté", "default": "Brouillon", "read_only": 1, "in_list_view": 1},
                {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Link", "options": "Workflow State", "hidden": 1}
            ],
            "permissions": [
                {"role": "Employee", "read": 1, "write": 1, "create": 1, "if_owner": 1},
                {"role": "HR User", "read": 1, "write": 1, "create": 1},
                {"role": "HR Manager", "read": 1, "write": 1, "create": 1}
            ]
        }).insert()
        print("DocType KYA Exit Ticket created")

    # 2.5 Fuel Log
    if not frappe.db.exists("DocType", "KYA Fuel Log"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Fuel Log",
            "module": "KYA HR",
            "custom": 1,
            "autoname": "FUEL-.####",
            "naming_rule": "Expression (old style)",
            "fields": [
                {"label": "Véhicule", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "reqd": 1, "in_list_view": 1},
                {"label": "Date", "fieldname": "date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Kilométrage", "fieldname": "odometer", "fieldtype": "Int", "reqd": 1, "in_list_view": 1},
                {"label": "Colonne 2", "fieldtype": "Column Break"},
                {"label": "Litres", "fieldname": "liters", "fieldtype": "Float", "reqd": 1},
                {"label": "Montant Total", "fieldname": "amount", "fieldtype": "Currency", "reqd": 1},
                {"label": "Station Service", "fieldname": "gas_station", "fieldtype": "Data"}
            ],
            "permissions": [
                {"role": "HR Manager", "read": 1, "write": 1, "create": 1},
                {"role": "Accounts User", "read": 1, "write": 1, "create": 1}
            ]
        }).insert()
        print("DocType KYA Fuel Log created")

    # 2.6 Mission
    if not frappe.db.exists("DocType", "KYA Mission"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Mission",
            "module": "KYA HR",
            "custom": 1,
            "autoname": "MISSION-.####",
            "naming_rule": "Expression (old style)",
            "fields": [
                {"label": "Employés", "fieldname": "employees", "fieldtype": "Table", "options": "KYA Exit Ticket Passenger", "reqd": 1},
                {"label": "Section Mission", "fieldtype": "Section Break"},
                {"label": "Destination", "fieldname": "destination", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                {"label": "Objectif de la Mission", "fieldname": "objective", "fieldtype": "Small Text", "reqd": 1},
                {"label": "Colonne 2", "fieldtype": "Column Break"},
                {"label": "Date de Départ", "fieldname": "start_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Date de Retour Prévue", "fieldname": "expected_end_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Date de Retour Réelle", "fieldname": "actual_end_date", "fieldtype": "Date"},
                {"label": "Section Logistique", "fieldtype": "Section Break"},
                {"label": "Véhicule", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle"},
                {"label": "Statut", "fieldname": "status", "fieldtype": "Select", "options": "Brouillon\nEn Cours\nTerminé\nAnnulé", "default": "Brouillon", "in_list_view": 1}
            ],
            "permissions": [
                {"role": "HR User", "read": 1, "write": 1, "create": 1},
                {"role": "HR Manager", "read": 1, "write": 1, "create": 1}
            ]
        }).insert()
        print("DocType KYA Mission created")

def create_workflows():
    # Permission Request
    workflow_name = "Workflow Permission Stagiaire"
    if not frappe.db.exists("Workflow", workflow_name) and frappe.db.exists("DocType", "KYA Permission Request"):
        frappe.get_doc({
            "doctype": "Workflow", "workflow_name": workflow_name, "document_type": "KYA Permission Request",
            "workflow_state_field": "workflow_state", "is_active": 1,
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
                {"state": "En attente Responsable Stage", "action": "Approuver (Resp.)", "next_state": "En attente DG", "allowed": "Responsable Stage"},
                {"state": "En attente DG", "action": "Approuver (DG)", "next_state": "Approuvé", "allowed": "DG"}
            ]
        }).insert()
        print(f"Workflow {workflow_name} created")

    # Exit Ticket
    workflow_name = "Workflow Ticket de Sortie"
    if not frappe.db.exists("Workflow", workflow_name) and frappe.db.exists("DocType", "KYA Exit Ticket"):
        frappe.get_doc({
            "doctype": "Workflow", "workflow_name": workflow_name, "document_type": "KYA Exit Ticket",
            "workflow_state_field": "workflow_state", "is_active": 1,
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
                {"state": "En attente Chef", "action": "Approver (RH - Urgence)", "next_state": "Approuvé", "allowed": "HR Manager"},
                {"state": "En attente RH", "action": "Valider", "next_state": "En attente DGA", "allowed": "HR Manager"},
                {"state": "En attente RH", "action": "Approuver (RH Final)", "next_state": "Approuvé", "allowed": "HR Manager"},
                {"state": "En attente DGA", "action": "Approuver", "next_state": "Approuvé", "allowed": "DGA"}
            ]
        }).insert()
        print(f"Workflow {workflow_name} created")

def create_workspaces():
    for ws_name, icon, links, charts in [
        ("Stagiaires", "user", [
            {"link_type": "DocType", "link_to": "Employee", "label": "Liste des Stagiaires"},
            {"link_type": "DocType", "link_to": "KYA Permission Request", "label": "Demandes de Permission"},
            {"link_type": "DocType", "link_to": "KYA Leave Planning", "label": "Planning des Congés"}
        ], [
            {"chart_name": "Répartition par Statut Stagiaire", "label": "Statistiques Stagiaires"}
        ]),
        ("Logistique", "truck", [
            {"link_type": "DocType", "link_to": "Vehicle", "label": "Parc Automobile"},
            {"link_type": "DocType", "link_to": "KYA Exit Ticket", "label": "Tickets de Sortie"},
            {"link_type": "DocType", "link_to": "KYA Fuel Log", "label": "Suivi Carburant"},
            {"link_type": "DocType", "link_to": "KYA Mission", "label": "Suivi des Missions"}
        ], [
            {"chart_name": "Consommation Carburant par Véhicule", "label": "Dépenses Carburant"}
        ])
    ]:
        if not frappe.db.exists("Workspace", ws_name):
            frappe.get_doc({
                "doctype": "Workspace", "name": ws_name, "label": ws_name, "module": "KYA HR",
                "extends": 0, "is_standard": 1, "public": 1, "icon": icon, "links": links, "charts": charts
            }).insert()
            print(f"Workspace {ws_name} created")
        else:
            ws_doc = frappe.get_doc("Workspace", ws_name)
            ws_doc.charts = charts
            ws_doc.save()
            print(f"Workspace {ws_name} updated with charts")


def create_notifications():
    for name, dt, subject, msg in [
        ("Notification Permission Stagiaire", "KYA Permission Request", "Demande de Permission : {{ doc.employee_name }}", "<p>Nouvelle demande de permission de {{ doc.employee_name }}.</p>"),
        ("Notification Ticket de Sortie", "KYA Exit Ticket", "Nouveau Ticket de Sortie : {{ doc.name }}", "<p>Un ticket de sortie pour {{ doc.destination }} attend votre validation.</p>")
    ]:
        if not frappe.db.exists("Notification", name) and frappe.db.exists("DocType", dt):
            frappe.get_doc({
                "doctype": "Notification", "name": name, "subject": subject, "document_type": dt,
                "event": "Value Change", "value_changed": "workflow_state", "send_to_all_assignees": 1,
                "message": msg, "enabled": 1
            }).insert()
            print(f"Notification {name} created")

if __name__ == "__main__":
    execute()

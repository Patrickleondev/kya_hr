import frappe
import json

def execute():
    # 1. Create KYA Permission Request DocType
    create_permission_request_doctype()
    
    # 2. Create KYA Leave Planning DocType
    create_leave_planning_doctype()
    
    # 3. Create KYA Exit Ticket Passenger Child DocType
    create_exit_ticket_passenger_doctype()
    
    # 4. Create KYA Exit Ticket DocType
    create_exit_ticket_doctype()
    
    # 5. Create KYA Fuel Log DocType
    create_fuel_log_doctype()

    frappe.db.commit()
    print("✅ All KYA Extensions DocTypes created/updated successfully!")

def create_permission_request_doctype():
    if not frappe.db.exists("DocType", "KYA Permission Request"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Permission Request",
            "module": "kya_hr",
            "custom": 1,
            "autoname": "PR-.####",
            "naming_rule": "Expression (Old Style)",
            "fields": [
                {"label": "Employé (Stagiaire)", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"label": "Prénom et Nom", "fieldname": "employee_name", "fieldtype": "Read Only", "fetch_from": "employee.employee_name"},
                {"label": "Type de Permission", "fieldname": "permission_type", "fieldtype": "Select", "options": "Absence\nRetard\nSortie Anticipée", "reqd": 1},
                {"label": "Section Dates", "fieldtype": "Section Break"},
                {"label": "Date de Début", "fieldname": "from_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Date de Fin", "fieldname": "to_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Colonne 2", "fieldtype": "Column Break"},
                {"label": "Heure de Début", "fieldname": "from_time", "fieldtype": "Time", "depends_on": "eval:doc.permission_type!=\"Absence\""},
                {"label": "Heure de Fin", "fieldname": "to_time", "fieldtype": "Time", "depends_on": "eval:doc.permission_type!=\"Absence\""},
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

def create_leave_planning_doctype():
    if not frappe.db.exists("DocType", "KYA Leave Planning"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Leave Planning",
            "module": "kya_hr",
            "custom": 1,
            "autoname": "LP-.####",
            "naming_rule": "Expression (Old Style)",
            "fields": [
                {"label": "Employé", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"label": "Période demandée", "fieldname": "period", "fieldtype": "Section Break"},
                {"label": "Date de Début", "fieldname": "from_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Date de Fin", "fieldname": "to_date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"label": "Colonne 2", "fieldtype": "Column Break"},
                {"label": "Justification", "fieldname": "reason", "fieldtype": "Small Text", "reqd": 1},
                {"label": "Motif de Rejet", "fieldname": "rejection_reason", "fieldtype": "Small Text", "read_only_depends_on": "eval:doc.status!='Rejeté'"},
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

def create_exit_ticket_passenger_doctype():
    if not frappe.db.exists("DocType", "KYA Exit Ticket Passenger"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Exit Ticket Passenger",
            "module": "kya_hr",
            "istable": 1,
            "custom": 1,
            "fields": [
                {"label": "Employé", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"label": "Nom", "fieldname": "employee_name", "fieldtype": "Read Only", "fetch_from": "employee.employee_name", "in_list_view": 1}
            ]
        }).insert()
        print("DocType KYA Exit Ticket Passenger created")

def create_exit_ticket_doctype():
    if not frappe.db.exists("DocType", "KYA Exit Ticket"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Exit Ticket",
            "module": "kya_hr",
            "custom": 1,
            "autoname": "ET-.####",
            "naming_rule": "Expression (Old Style)",
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

def create_fuel_log_doctype():
    if not frappe.db.exists("DocType", "KYA Fuel Log"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Fuel Log",
            "module": "kya_hr",
            "custom": 1,
            "autoname": "FUEL-.####",
            "naming_rule": "Expression (Old Style)",
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

if __name__ == "__main__":
    execute()

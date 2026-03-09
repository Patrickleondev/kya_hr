import frappe

frappe.local.conf.developer_mode = 1

print("\n--- SYNCING KYA SERVICES DOCTYPES ---")
doctypes_to_import = ["KYA Form", "KYA Form Question", "KYA Form Response", "KYA Form Answer"]
for dt in doctypes_to_import:
    try:
        m = dt.replace(" ", "_").lower()
        frappe.modules.import_file("kya_services", "doctype", m)
        print(f"Successfully imported {dt}")
    except Exception as e:
        print(f"Failed to import {dt}: {e}")

print("\n--- CREATING KYA STAGIAIRES DOCTYPES ---")

if not frappe.db.exists("DocType", "Permission Sortie Stagiaire"):
    print("Creating Permission Sortie Stagiaire...")
    frappe.get_doc({
        "doctype": "DocType",
        "name": "Permission Sortie Stagiaire",
        "module": "KYA HR",
        "custom": 0,
        "autoname": "format:PSS-{YYYY}-{####}",
        "fields": [
            {"fieldname": "employee", "label": "Employé / Stagiaire", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
            {"fieldname": "date_sortie", "label": "Date de Sortie", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
            {"fieldname": "motif", "label": "Motif", "fieldtype": "Small Text", "reqd": 1},
            {"fieldname": "status", "label": "Statut", "fieldtype": "Select", "options": "Brouillon\nEn attente\nApprouvé\nRejeté", "default": "Brouillon", "in_list_view": 1}
        ],
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}]
    }).insert(ignore_permissions=True)
else:
    print("Permission Sortie Stagiaire already exists.")

if not frappe.db.exists("DocType", "Bilan Fin de Stage"):
    print("Creating Bilan Fin de Stage...")
    frappe.get_doc({
        "doctype": "DocType",
        "name": "Bilan Fin de Stage",
        "module": "KYA HR",
        "custom": 0,
        "autoname": "format:BILAN-{YYYY}-{####}",
        "fields": [
            {"fieldname": "employee", "label": "Employé / Stagiaire", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
            {"fieldname": "date_bilan", "label": "Date du Bilan", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
            {"fieldname": "evaluation", "label": "Évaluation Globale", "fieldtype": "Text Editor", "reqd": 1},
            {"fieldname": "status", "label": "Statut", "fieldtype": "Select", "options": "Brouillon\nSoumis\nValidé", "default": "Brouillon"}
        ],
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}]
    }).insert(ignore_permissions=True)
else:
    print("Bilan Fin de Stage already exists.")

frappe.db.commit()
print("\n--- SYNC AND CREATE COMPLETE ---")


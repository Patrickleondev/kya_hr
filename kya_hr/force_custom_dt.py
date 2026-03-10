import frappe

def run():
    print("\n--- CLEANING BROKEN DOCTYPES ---")
    doctypes = ["Permission Sortie Stagiaire", "Bilan Fin de Stage"]
    for dt in doctypes:
        if frappe.db.exists("DocType", dt):
            try:
                frappe.delete_doc("DocType", dt, force=1)
                print(f"Deleted broken DocType: {dt}")
            except:
                frappe.db.sql(f"DELETE FROM tabDocType WHERE name='{dt}'")
                frappe.db.sql(f"DELETE FROM `tabDocField` WHERE parent='{dt}'")
            frappe.db.sql(f"DROP TABLE IF EXISTS `tab{dt}`")

    print("\n--- RECREATING DOCTYPES AS CUSTOM=1 ---")
    # Permission Sortie Stagiaire
    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": "Permission Sortie Stagiaire",
        "module": "KYA HR",
        "custom": 1,
        "autoname": "format:PSS-{YYYY}-{####}",
        "fields": [
            {"fieldname": "employee", "label": "Employé / Stagiaire", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
            {"fieldname": "date_sortie", "label": "Date de Sortie", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
            {"fieldname": "motif", "label": "Motif", "fieldtype": "Small Text", "reqd": 1},
            {"fieldname": "status", "label": "Statut", "fieldtype": "Select", "options": "Brouillon\nEn attente\nApprouvé\nRejeté", "default": "Brouillon", "in_list_view": 1}
        ],
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}]
    })
    doc.insert(ignore_permissions=True)

    # Bilan Fin de Stage
    doc2 = frappe.get_doc({
        "doctype": "DocType",
        "name": "Bilan Fin de Stage",
        "module": "KYA HR",
        "custom": 1,
        "autoname": "format:BILAN-{YYYY}-{####}",
        "fields": [
            {"fieldname": "employee", "label": "Employé / Stagiaire", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
            {"fieldname": "date_bilan", "label": "Date du Bilan", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
            {"fieldname": "evaluation", "label": "Évaluation Globale", "fieldtype": "Text Editor", "reqd": 1},
            {"fieldname": "status", "label": "Statut", "fieldtype": "Select", "options": "Brouillon\nSoumis\nValidé", "default": "Brouillon"}
        ],
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}]
    })
    doc2.insert(ignore_permissions=True)

    frappe.db.commit()
    print("\n--- DOCYTPE RECREATION SUCCESS ---")

if __name__ == "__main__":
    frappe.init(site="frontend-test")
    frappe.connect()
    # Mock Administrator so DocType creation has permissions
    frappe.set_user("Administrator")
    run()

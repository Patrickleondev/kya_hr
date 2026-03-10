import frappe
from frappe.model.docstatus import DocStatus

def repair_all():
    # Assuming frappe is already initialized by bench run-python-script
    frappe.set_user("Administrator")
    
    print("\n--- 1. ENSURING CUSTOM DOCTYPES ---")
    custom_doctypes = [
        {
            "name": "Permission Sortie Stagiaire",
            "module": "KYA HR",
            "fields": [
                {"fieldname": "employee", "label": "Employé / Stagiaire", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"fieldname": "date_sortie", "label": "Date de Sortie", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"fieldname": "motif", "label": "Motif", "fieldtype": "Small Text", "reqd": 1},
                {"fieldname": "status", "label": "Statut", "fieldtype": "Select", "options": "Brouillon\nEn attente\nApprouvé\nRejeté", "default": "Brouillon", "in_list_view": 1}
            ]
        },
        {
            "name": "Bilan Fin de Stage",
            "module": "KYA HR",
            "fields": [
                {"fieldname": "employee", "label": "Employé / Stagiaire", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"fieldname": "date_bilan", "label": "Date du Bilan", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
                {"fieldname": "evaluation", "label": "Évaluation Globale", "fieldtype": "Text Editor", "reqd": 1},
                {"fieldname": "status", "label": "Statut", "fieldtype": "Select", "options": "Brouillon\nSoumis\nValidé", "default": "Brouillon"}
            ]
        }
    ]
    
    for dt_cfg in custom_doctypes:
        if not frappe.db.exists("DocType", dt_cfg["name"]):
            print(f"Creating DocType: {dt_cfg['name']}")
            doc = frappe.get_doc({
                "doctype": "DocType",
                "name": dt_cfg["name"],
                "module": dt_cfg["module"],
                "custom": 1,
                "fields": dt_cfg["fields"],
                "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}]
            })
            doc.insert(ignore_permissions=True)
            print(f"Created {dt_cfg['name']}")
        else:
            print(f"DocType {dt_cfg['name']} already exists.")

    print("\n--- 2. RESTORING WORKSPACES ---")
    workspaces = [
        {
            "name": "KYA Stagiaires",
            "title": "KYA Stagiaires",
            "module": "KYA HR",
            "parent": "People",
            "icon": "contact-round",
            "shortcuts": [
                {"label": "Permission Sortie Stagiaire", "type": "DocType", "link_to": "Permission Sortie Stagiaire", "color": "Blue"},
                {"label": "Bilan Fin de Stage", "type": "DocType", "link_to": "Bilan Fin de Stage", "color": "Green"},
                {"label": "Liste des Stagiaires", "type": "DocType", "link_to": "Employee", "color": "Orange"}
            ]
        },
        {
            "name": "KYA Services",
            "title": "KYA Services",
            "module": "KYA Services",
            "parent": "",
            "icon": "clipboard",
            "shortcuts": [
                {"label": "KYA Form", "type": "DocType", "link_to": "KYA Form", "color": "Blue"},
                {"label": "KYA Form Response", "type": "DocType", "link_to": "KYA Form Response", "color": "Green"}
            ]
        }
    ]
    
    for ws_cfg in workspaces:
        if frappe.db.exists("Workspace", ws_cfg["name"]):
            frappe.delete_doc("Workspace", ws_cfg["name"], force=True)
            print(f"Cleaned up existing Workspace: {ws_cfg['name']}")
        
        doc = frappe.new_doc("Workspace")
        doc.name = ws_cfg["name"]
        doc.title = ws_cfg["title"]
        doc.module = ws_cfg["module"]
        doc.icon = ws_cfg["icon"]
        doc.parent_page = ws_cfg["parent"]
        doc.public = 1
        
        # Add shortcuts
        for sc in ws_cfg["shortcuts"]:
            doc.append("shortcuts", sc)
        
        doc.insert(ignore_permissions=True)
        print(f"Workspace {ws_cfg['name']} created.")

    print("\n--- 3. PATCHING SYSTEM WORKSPACES ---")
    # Patch Leaves for Planning
    if frappe.db.exists("Workspace", "Leaves"):
        ws = frappe.get_doc("Workspace", "Leaves")
        label = "Planning des Congés"
        if not any(x.label == label for x in ws.shortcuts):
            ws.append("shortcuts", {"label": label, "type": "DocType", "link_to": "Leave Application", "color": "Green"})
            ws.save()
            print("Planning added to Leaves.")

    print("\n--- 4. PWA CONFIGURATION ---")
    frappe.db.set_value("System Settings", "System Settings", "enable_pwa", 1)
    
    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- REPAIR COMPLETED ---")

if __name__ == "__main__":
    repair_all()

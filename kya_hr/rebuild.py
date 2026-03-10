import frappe
import json

def run():
    print("\n--- REBUILDING KYA WORKSPACES FROM SCRATCH ---")
    frappe.set_user("Administrator")
    
    workspaces_to_build = [
        {
            "name": "KYA Stagiaires",
            "title": "KYA Stagiaires",
            "icon": "contact-round",
            "module": "KYA HR",
            "category": "Modules",
            "public": 1,
            "parent_page": "",
            "content": json.dumps([
                {"id": "h1", "type": "header", "data": {"text": "Gestion des Stagiaires", "level": 4}},
                {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Permissions Sortie", "col": 3}},
                {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Bilans de Stage", "col": 3}}
            ]),
            "shortcuts": [
                {"label": "Permissions Sortie", "type": "DocType", "link_to": "Permission Sortie Stagiaire"},
                {"label": "Bilans de Stage", "type": "DocType", "link_to": "Bilan Fin de Stage"}
            ],
            "links": []
        },
        {
            "name": "KYA Services",
            "title": "KYA Services",
            "icon": "clipboard",
            "module": "KYA Services",
            "category": "Modules",
            "public": 1,
            "parent_page": "",
            "content": json.dumps([
                {"id": "h2", "type": "header", "data": {"text": "Formulaires", "level": 4}},
                {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "Gérer les Formulaires", "col": 3}}
            ]),
            "shortcuts": [
                {"label": "Gérer les Formulaires", "type": "DocType", "link_to": "KYA Form"}
            ],
            "links": []
        }
    ]

    for ws_data in workspaces_to_build:
        name = ws_data["name"]
        print(f"Purging {name}...")
        frappe.db.sql(f"DELETE FROM tabWorkspace WHERE name='{name}'")
        frappe.db.sql(f"DELETE FROM `tabWorkspace Shortcut` WHERE parent='{name}'")
        frappe.db.sql(f"DELETE FROM `tabWorkspace Link` WHERE parent='{name}'")
        frappe.db.sql(f"DELETE FROM `tabWorkspace Chart` WHERE parent='{name}'")
        frappe.db.sql(f"DELETE FROM tabWorkspace WHERE for_user='Administrator' AND name='{name}'")
        
        print(f"Recreating {name}...")
        try:
            doc = frappe.new_doc("Workspace")
            doc.name = ws_data["name"]
            doc.update(ws_data)
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True)
            print(f"Successfully created {name}")
        except Exception as e:
            print(f"Failed to create {name}: {e}")

    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- DONE REBUILDING ---")


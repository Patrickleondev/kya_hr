import frappe
import json

def run():
    print("\n--- FORCING WORKSPACE CONTENT JSON ---")
    
    # frappe.init and connect handled by bench execute
    frappe.set_user("Administrator")
    
    stagiaires_content = [
        {
            "id": "header1", "type": "header", "data": {"text": "Gestion des Stagiaires", "level": 4}
        },
        {
            "id": "shortcut1", "type": "shortcut", "data": {"shortcut_name": "Permissions Sortie", "col": 3}
        },
        {
            "id": "shortcut2", "type": "shortcut", "data": {"shortcut_name": "Bilans de Stage", "col": 4}
        }
    ]
    
    services_content = [
        {
            "id": "header2", "type": "header", "data": {"text": "Formulaires", "level": 4}
        },
        {
            "id": "shortcut3", "type": "shortcut", "data": {"shortcut_name": "Gérer les Formulaires", "col": 3}
        }
    ]
    
    workspaces = {
        "KYA Stagiaires": json.dumps(stagiaires_content),
        "KYA Services": json.dumps(services_content)
    }

    for name, content in workspaces.items():
        if frappe.db.exists("Workspace", name):
            try:
                ws = frappe.get_doc("Workspace", name)
                ws.content = content
                ws.public = 1
                # Top level workspace
                ws.parent_page = ""
                ws.is_standard = 0
                
                ws.save(ignore_permissions=True)
                print(f"Set JSON content for {name}")
            except Exception as e:
                print(f"Error for {name}: {e}")
        else:
            print(f"{name} doesn't exist to set content!")

    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- DONE ---")


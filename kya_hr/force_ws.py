import frappe
from frappe.desk.desktop import save_new_workspace

print("\n--- FORCING WORKSPACE VISIBILITY ---")

# Ensure proper Category assignment (required for v15 sidebar)
workspaces = [
    {"name": "KYA Stagiaires", "icon": "contact-round", "module": "KYA HR", "links": [
        {"label": "Permissions Sortie", "type": "Shortcut", "link_type": "DocType", "link_to": "Permission Sortie Stagiaire"},
        {"label": "Bilans de Stage", "type": "Shortcut", "link_type": "DocType", "link_to": "Bilan Fin de Stage"}
    ]},
    {"name": "KYA Services", "icon": "clipboard", "module": "KYA Services", "links": [
        {"label": "Gérer les Formulaires", "type": "Shortcut", "link_type": "DocType", "link_to": "KYA Form"}
    ]}
]

for ws_data in workspaces:
    name = ws_data["name"]
    # Check if a broken custom or standard one exists
    if frappe.db.exists("Workspace", name):
        try:
            ws = frappe.get_doc("Workspace", name)
            ws.public = 1
            ws.is_standard = 0 # Temporarily make custom so we can edit it freely
            ws.category = "Modules" # Super important for v15 sidebar!
            ws.icon = ws_data["icon"]
            
            # Clear existing links and shortcuts
            ws.set("links", [])
            ws.set("shortcuts", [])
            
            # Add new shortcuts so Frappe engine sees "content" and grants permission
            for link in ws_data["links"]:
                ws.append("shortcuts", {
                    "label": link["label"],
                    "type": link["type"],
                    "link_type": link["link_type"],
                    "link_to": link["link_to"],
                    "color": "Blue"
                })
            
            ws.save(ignore_permissions=True)
            print(f"Updated and forced visibility for {name}")
        except Exception as e:
            print(f"Error updating {name}: {e}")
    else:
        # Create it aggressively if it truly doesn't exist
        print(f"Creating missing {name} workspace from scratch...")
        try:
            ws = frappe.new_doc("Workspace")
            ws.title = name
            ws.name = name
            ws.public = 1
            ws.category = "Modules"
            ws.icon = ws_data["icon"]
            for link in ws_data["links"]:
                ws.append("shortcuts", {
                    "label": link["label"],
                    "type": link["type"],
                    "link_type": link["link_type"],
                    "link_to": link["link_to"],
                    "color": "Blue"
                })
            ws.insert(ignore_permissions=True)
        except Exception as e:
            print(f"Failed to create {name}: {e}")

frappe.db.commit()
frappe.clear_cache()
print("\n--- DONE FORCING WORKSPACES ---")

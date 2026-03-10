import frappe
import json

def run():
    frappe.init(site='frontend')
    frappe.connect()
    
    # 1. Check Apps
    installed_apps = frappe.get_installed_apps()
    print(f"Installed Apps: {installed_apps}")
    
    # Check Module Def
    for mod in ['KYA HR', 'KYA Services']:
        app = frappe.db.get_value("Module Def", mod, "app_name")
        print(f"Module '{mod}' is assigned to App: '{app}'")
    
    # 2. Check Workspaces
    for ws_name in ['KYA Stagiaires', 'KYA Services']:
        if frappe.db.exists('Workspace', ws_name):
            ws = frappe.get_doc('Workspace', ws_name)
            print(f"\n--- Workspace: {ws_name} ---")
            print(f"Module: {ws.module}")
            print(f"App: {ws.app}")
            print(f"Type: {ws.type}")
            print(f"Public: {ws.public}")
            print(f"Parent Page: {ws.parent_page}")
            print(f"Is Hidden: {ws.is_hidden}")
            
    # Also check if they appear in get_workspace_sidebar_items list for Administrator
    admin = frappe.get_doc("User", "Administrator")
    # For frappe v16, to see the workspaces for a specific user, we can execute the API as Administrator
    frappe.set_user("Administrator")
    from frappe.desk.desktop import get_workspace_sidebar_items
    items = get_workspace_sidebar_items()
    # items contains 'pages'
    pages = items.get('pages', [])
    found = [p.get('name') for p in pages if p.get('name') in ['KYA Services', 'KYA Stagiaires']]
    print(f"\nWorkspaces found in sidebar API for Administrator: {found}")
    
    # Print the raw block for KYA Stagiaires from API
    for p in pages:
        if p.get('name') == 'KYA Stagiaires':
            print(f"API dict for KYA Stagiaires: {p}")
            
    frappe.destroy()

if __name__ == '__main__':
    run()

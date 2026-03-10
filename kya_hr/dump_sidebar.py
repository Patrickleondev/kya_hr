import frappe
import json

def run():
    frappe.init(site='frontend')
    frappe.connect()
    
    frappe.set_user("Administrator")
    from frappe.desk.desktop import get_workspace_sidebar_items
    items = get_workspace_sidebar_items()
    
    with open('/home/frappe/frappe-bench/sidebar_output.json', 'w') as f:
        json.dump(items, f, indent=4)
        
    print("Sidebar API dumped to sidebar_output.json")
    
    # Let's also check the exact Module Defs for the KYA apps
    for mod in ['KYA HR', 'KYA Services']:
        try:
            m = frappe.get_doc("Module Def", mod)
            print(f"Module Def '{mod}': app_name={m.app_name}")
        except Exception as e:
            print(f"Module error {mod}: {e}")

    frappe.destroy()

if __name__ == '__main__':
    run()

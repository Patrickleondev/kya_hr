import frappe
def run():
    print("--- FIXING UI ---")
    
    # 1. KYA Workspaces
    for name, module, app, icon in [
        ("KYA Services", "KYA Services", "kya_services", "layers"),
        ("KYA Stagiaires", "KYA HR", "kya_hr", "users")
    ]:
        if frappe.db.exists("Workspace", name):
            doc = frappe.get_doc("Workspace", name)
            print(f"Found existing {name}")
        else:
            doc = frappe.new_doc("Workspace")
            doc.name = name
            print(f"Creating new {name}")
            
        doc.label = name
        doc.module = module
        doc.app = app
        doc.icon = icon
        doc.public = 1
        doc.is_standard = 1
        doc.is_hidden = 0
        doc.category = "Modules"
        
        # Shortcuts for KYA
        if not doc.shortcuts:
            if name == "KYA Services":
                doc.append("shortcuts", {"label": "Formulaires", "type": "Shortcut", "link_type": "DocType", "link_to": "KYA Form"})
            else:
                doc.append("shortcuts", {"label": "Stagiaires", "type": "Shortcut", "link_type": "DocType", "link_to": "Employee"})
        
        doc.save(ignore_permissions=True)
        print(f"Saved {name}")

    # 2. Fix Leaves (Congés)
    # Search by translation too
    for ws_name in ["Leaves", "Congés"]:
        if frappe.db.exists("Workspace", ws_name):
            doc = frappe.get_doc("Workspace", ws_name)
            doc.icon = "calendar"
            doc.save(ignore_permissions=True)
            print(f"Fixed icon for {ws_name}")

    # 3. Add shortcut to HR
    if frappe.db.exists("Workspace", "HR"):
        doc = frappe.get_doc("Workspace", "HR")
        exists = False
        for s in doc.shortcuts:
            if s.link_to == "KYA Stagiaires":
                exists = True
                break
        if not exists:
            doc.append("shortcuts", {
                "label": "Stagiaires KYA",
                "type": "Shortcut",
                "link_type": "Workspace",
                "link_to": "KYA Stagiaires",
                "color": "Blue"
            })
            doc.save(ignore_permissions=True)
            print("Added Stagiaires to HR")

    frappe.db.commit()
    frappe.clear_cache()
    print("UI FIX DONE")

import frappe
import json

def run():
    print("\n--- FORCING KYA WORKSPACES VIA SQL ---")
    
    now = frappe.utils.now()
    user = "Administrator"
    
    workspaces = [
        {
            "name": "KYA Stagiaires",
            "title": "KYA Stagiaires",
            "icon": "contact-round",
            "module": "KYA HR",
            "public": 1,
            "parent_page": "",
            "content": json.dumps([
                {"id": "h1", "type": "header", "data": {"text": "Gestion des Stagiaires", "level": 4}},
                {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Permissions Sortie", "col": 3}},
                {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Bilans de Stage", "col": 3}}
            ]),
            "shortcuts": [
                ("Permissions Sortie", "Permission Sortie Stagiaire", "DocType"),
                ("Bilans de Stage", "Bilan Fin de Stage", "DocType"),
            ]
        },
        {
            "name": "KYA Services",
            "title": "KYA Services",
            "icon": "clipboard",
            "module": "KYA Services",
            "public": 1,
            "parent_page": "",
            "content": json.dumps([
                {"id": "h2", "type": "header", "data": {"text": "Formulaires KYA", "level": 4}},
                {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "Gérer les Formulaires", "col": 3}}
            ]),
            "shortcuts": [
                ("Gérer les Formulaires", "KYA Form", "DocType"),
            ]
        }
    ]

    for w in workspaces:
        name = w["name"]
        
        # Hard purge
        for t in ["tabWorkspace", "`tabWorkspace Shortcut`", "`tabWorkspace Link`", "`tabWorkspace Chart`"]:
            frappe.db.sql(f"DELETE FROM {t} WHERE parent=%s OR name=%s", (name, name))
        
        # Direct SQL insert of the workspace
        frappe.db.sql("""
            INSERT INTO tabWorkspace (name, title, icon, module, public, parent_page, content, creation, modified, owner, modified_by, docstatus)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
        """, (name, w["title"], w["icon"], w["module"], w["public"], w["parent_page"], w["content"], now, now, user, user))
        
        # Insert shortcuts
        for i, (label, link_to, link_type) in enumerate(w["shortcuts"]):
            sc_name = frappe.generate_hash(length=10)
            frappe.db.sql("""
                INSERT INTO `tabWorkspace Shortcut` (name, parent, parenttype, parentfield, idx, label, link_to, type, creation, modified, owner, modified_by, docstatus)
                VALUES (%s, %s, 'Workspace', 'shortcuts', %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """, (sc_name, name, i + 1, label, link_to, link_type, now, now, user, user))
        
        print(f"Inserted {name} directly via SQL.")
    
    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- ALL DONE ---")

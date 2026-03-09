import frappe
import json

def run():
    print("\n--- FIXING WORKSPACE HIERARCHY ---")
    now = frappe.utils.now()
    user = "Administrator"

    # === 1. KYA Stagiaires → child of "People" ===
    print("Setting KYA Stagiaires as child of 'People'...")
    
    # Purge any existing bad version
    frappe.db.sql("DELETE FROM tabWorkspace WHERE name='KYA Stagiaires'")
    frappe.db.sql("DELETE FROM `tabWorkspace Shortcut` WHERE parent='KYA Stagiaires'")
    frappe.db.sql("DELETE FROM `tabWorkspace Link` WHERE parent='KYA Stagiaires'")

    content_stag = json.dumps([
        {"id": "h1", "type": "header", "data": {"text": "Stagiaires", "level": 4}},
        {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Permission Sortie Stagiaire", "col": 3}},
        {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Bilan Fin de Stage", "col": 3}}
    ])
    
    frappe.db.sql("""
        INSERT INTO tabWorkspace (name, title, icon, module, public, parent_page, content, creation, modified, owner, modified_by, docstatus)
        VALUES ('KYA Stagiaires', 'KYA Stagiaires', 'contact-round', 'KYA HR', 1, 'People', %s, %s, %s, %s, %s, 0)
    """, (content_stag, now, now, user, user))

    for i, (label, link_to) in enumerate([
        ("Permission Sortie Stagiaire", "Permission Sortie Stagiaire"),
        ("Bilan Fin de Stage", "Bilan Fin de Stage")
    ]):
        sc = frappe.generate_hash(length=10)
        frappe.db.sql("""
            INSERT INTO `tabWorkspace Shortcut` (name, parent, parenttype, parentfield, idx, label, link_to, type, creation, modified, owner, modified_by, docstatus)
            VALUES (%s, 'KYA Stagiaires', 'Workspace', 'shortcuts', %s, %s, %s, 'DocType', %s, %s, %s, %s, 0)
        """, (sc, i+1, label, link_to, now, now, user, user))
    print("  → KYA Stagiaires created under People")

    # === 2. KYA Services → top-level standalone icon ===
    print("Creating KYA Services as standalone Desk icon...")
    
    frappe.db.sql("DELETE FROM tabWorkspace WHERE name='KYA Services'")
    frappe.db.sql("DELETE FROM `tabWorkspace Shortcut` WHERE parent='KYA Services'")
    frappe.db.sql("DELETE FROM `tabWorkspace Link` WHERE parent='KYA Services'")

    content_svc = json.dumps([
        {"id": "h2", "type": "header", "data": {"text": "Formulaires & Enquêtes", "level": 4}},
        {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "KYA Form", "col": 3}}
    ])
    
    frappe.db.sql("""
        INSERT INTO tabWorkspace (name, title, icon, module, public, parent_page, content, creation, modified, owner, modified_by, docstatus)
        VALUES ('KYA Services', 'KYA Services', 'clipboard', 'KYA Services', 1, '', %s, %s, %s, %s, %s, 0)
    """, (content_svc, now, now, user, user))

    sc = frappe.generate_hash(length=10)
    frappe.db.sql("""
        INSERT INTO `tabWorkspace Shortcut` (name, parent, parenttype, parentfield, idx, label, link_to, type, creation, modified, owner, modified_by, docstatus)
        VALUES (%s, 'KYA Services', 'Workspace', 'shortcuts', 1, 'KYA Form', 'KYA Form', 'DocType', %s, %s, %s, %s, 0)
    """, (sc, now, now, user, user))
    print("  → KYA Services created as standalone (no parent)")

    # === 3. Add "Demande Achat KYA" link to "Buying" workspace ===
    print("Adding Demande Achat KYA to Buying workspace...")
    existing = frappe.db.sql("SELECT name FROM `tabWorkspace Link` WHERE parent='Buying' AND link_to='Demande Achat KYA'")
    if not existing:
        cnt = frappe.db.sql("SELECT MAX(idx) FROM `tabWorkspace Link` WHERE parent='Buying'")[0][0] or 0
        lk = frappe.generate_hash(length=10)
        frappe.db.sql("""
            INSERT INTO `tabWorkspace Link` (name, parent, parenttype, parentfield, idx, label, link_to, type, onboard, creation, modified, owner, modified_by, docstatus)
            VALUES (%s, 'Buying', 'Workspace', 'links', %s, 'Demande Achat KYA', 'Demande Achat KYA', 'DocType', 0, %s, %s, %s, %s, 0)
        """, (lk, cnt+1, now, now, user, user))
        print("  → Demande Achat KYA added to Buying")
    else:
        print("  → Already exists in Buying")

    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- ALL HIERARCHY FIXES DONE ---")
    print("Instructions: CTRL+F5 your browser. Click 'People' icon → you'll see KYA Stagiaires.")
    print("On the Desk home, you should see a new 'KYA Services' icon.")

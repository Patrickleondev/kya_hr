import frappe

def create_roles():
    print("Ensuring Roles exist...")
    for role_name in ["Audit Interne", "DGA"]:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
            print(f"  → Role {role_name} created.")

def run():
    print("\n--- SUPER WORKSPACE RESTORATION ---")
    frappe.set_user("Administrator")
    create_roles()
    
    now = frappe.utils.now()
    user = "Administrator"

    # 1. Purge DB version of KYA Workspaces to force clean state
    target_workspaces = ["KYA Stagiaires", "KYA Services"]
    for ws_name in target_workspaces:
        if frappe.db.exists("Workspace", ws_name):
            print(f"Purging DB version of {ws_name}...")
            frappe.delete_doc("Workspace", ws_name, force=True, ignore_permissions=True)
    
    # 2. Re-create KYA Stagiaires under People
    print("Re-creating KYA Stagiaires under People...")
    ws = frappe.new_doc("Workspace")
    ws.name = "KYA Stagiaires"
    ws.title = "KYA Stagiaires"
    ws.icon = "contact-round"
    ws.module = "KYA HR"
    ws.public = 1
    ws.parent_page = "People"
    ws.content = frappe.as_json([
        {"id": "h1", "type": "header", "data": {"text": "Gestion des Stagiaires", "level": 4}},
        {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Permission Sortie Stagiaire", "col": 3}},
        {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Bilan Fin de Stage", "col": 3}}
    ])
    ws.append("shortcuts", {"label": "Permission Sortie Stagiaire", "type": "DocType", "link_to": "Permission Sortie Stagiaire"})
    ws.append("shortcuts", {"label": "Bilan Fin de Stage", "type": "DocType", "link_to": "Bilan Fin de Stage"})
    ws.insert(ignore_permissions=True)

    # 3. Re-create KYA Services as standalone
    print("Re-creating KYA Services as standalone...")
    ws_svc = frappe.new_doc("Workspace")
    ws_svc.name = "KYA Services"
    ws_svc.title = "KYA Services"
    ws_svc.icon = "clipboard"
    ws_svc.module = "KYA Services"
    ws_svc.public = 1
    ws_svc.parent_page = "" 
    ws_svc.content = frappe.as_json([
        {"id": "h2", "type": "header", "data": {"text": "Formulaires KYA", "level": 4}},
        {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "KYA Form", "col": 3}}
    ])
    ws_svc.append("shortcuts", {"label": "KYA Form", "type": "DocType", "link_to": "KYA Form"})
    ws_svc.append("shortcuts", {"label": "KYA Form Response", "type": "DocType", "link_to": "KYA Form Response"})
    ws_svc.insert(ignore_permissions=True)

    # 4. Patch Buying
    if frappe.db.exists("Workspace", "Buying"):
        print("Updating Buying with KYA links...")
        ws_buy = frappe.get_doc("Workspace", "Buying")
        for k in [("PV Sortie Materiel", "PV Sortie Materiel"), ("Demande Achat KYA", "Demande Achat KYA")]:
            if not any(x.label == k[0] for x in ws_buy.shortcuts):
                ws_buy.append("shortcuts", {"label": k[0], "type": "DocType", "link_to": k[1]})
            if not any(x.label == k[0] for x in ws_buy.links):
                ws_buy.append("links", {"label": k[0], "type": "Link", "link_type": "DocType", "link_to": k[1]})
        ws_buy.save(ignore_permissions=True)

    # 5. Patch Leaves
    if frappe.db.exists("Workspace", "Leaves"):
        print("Updating Leaves with KYA Planning...")
        ws_lv = frappe.get_doc("Workspace", "Leaves")
        if not any(x.label == "Planning des Conges" for x in ws_lv.shortcuts):
            ws_lv.append("shortcuts", {"label": "Planning des Conges", "type": "DocType", "link_to": "Leave Application", "color": "Green"})
        ws_lv.save(ignore_permissions=True)

    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- ALL DONE ---")

run()


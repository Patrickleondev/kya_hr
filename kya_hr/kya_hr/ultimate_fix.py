import frappe
from frappe.model.docstatus import DocStatus

def run():
    print("\n--- ULTIMATE KYA ECOSYSTEM FIX ---")
    frappe.set_user("Administrator")
    
    # 1. ROLES
    for role in ["Audit Interne", "DGA"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
            print(f"Role {role} created.")

    # 2. PURGE
    for ws_name in ["KYA Stagiaires", "KYA Services"]:
        if frappe.db.exists("Workspace", ws_name):
            frappe.delete_doc("Workspace", ws_name, force=True, ignore_permissions=True)
            print(f"Purged {ws_name}")

    # 3. KYA STAGIAIRES (Child of People)
    ws_stag = frappe.new_doc("Workspace")
    ws_stag.name = "KYA Stagiaires"
    ws_stag.title = "KYA Stagiaires"
    ws_stag.icon = "contact-round"
    ws_stag.module = "KYA HR"
    ws_stag.public = 1
    ws_stag.parent_page = "People"
    ws_stag.content = frappe.as_json([
        {"id": "h1", "type": "header", "data": {"text": "Gestion des Stagiaires", "level": 4}},
        {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Permission Sortie Stagiaire", "col": 3}},
        {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Bilan Fin de Stage", "col": 3}}
    ])
    ws_stag.append("shortcuts", {"label": "Permission Sortie Stagiaire", "type": "DocType", "link_to": "Permission Sortie Stagiaire", "color": "Blue"})
    ws_stag.append("shortcuts", {"label": "Bilan Fin de Stage", "type": "DocType", "link_to": "Bilan Fin de Stage", "color": "Green"})
    ws_stag.insert(ignore_permissions=True)
    print("KYA Stagiaires created under People.")

    # 4. KYA SERVICES (Standalone)
    ws_svc = frappe.new_doc("Workspace")
    ws_svc.name = "KYA Services"
    ws_svc.title = "KYA Services"
    ws_svc.icon = "clipboard"
    ws_svc.module = "KYA Services"
    ws_svc.public = 1
    ws_svc.parent_page = "" 
    ws_svc.content = frappe.as_json([
        {"id": "h2", "type": "header", "data": {"text": "Formulaires KYA", "level": 4}},
        {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "KYA Form", "col": 3}},
        {"id": "s4", "type": "shortcut", "data": {"shortcut_name": "KYA Form Response", "col": 3}}
    ])
    ws_svc.append("shortcuts", {"label": "KYA Form", "type": "DocType", "link_to": "KYA Form", "color": "Blue"})
    ws_svc.append("shortcuts", {"label": "KYA Form Response", "type": "DocType", "link_to": "KYA Form Response", "color": "Green"})
    ws_svc.insert(ignore_permissions=True)
    print("KYA Services created as standalone.")

    # 5. PATCH BUYING
    if frappe.db.exists("Workspace", "Buying"):
        ws_buy = frappe.get_doc("Workspace", "Buying")
        for k in [("PV Sortie Materiel", "PV Sortie Materiel"), ("Demande Achat KYA", "Demande Achat KYA")]:
            if not any(x.label == k[0] for x in ws_buy.shortcuts):
                ws_buy.append("shortcuts", {"label": k[0], "type": "DocType", "link_to": k[1], "color": "Orange"})
            if not any(x.label == k[0] for x in ws_buy.links):
                ws_buy.append("links", {"label": k[0], "type": "Link", "link_type": "DocType", "link_to": k[1]})
        ws_buy.save(ignore_permissions=True)
        print("Buying workspace updated.")

    # 6. PATCH LEAVES
    if frappe.db.exists("Workspace", "Leaves"):
        ws_lv = frappe.get_doc("Workspace", "Leaves")
        if not any(x.label == "Planning des Conges" for x in ws_lv.shortcuts):
            ws_lv.append("shortcuts", {"label": "Planning des Conges", "type": "DocType", "link_to": "Leave Application", "color": "Green"})
        ws_lv.save(ignore_permissions=True)
        print("Leaves workspace updated.")

    # 7. COMMIT & CACHE
    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- ALL DONE ---")

if __name__ == "__main__":
    run()

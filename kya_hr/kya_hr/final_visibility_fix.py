import frappe

def run():
    print("--- START FIX ---")
    frappe.set_user("Administrator")
    
    # 1. KYA Services
    name1 = "KYA Services"
    if frappe.db.exists("Workspace", name1):
        frappe.delete_doc("Workspace", name1, force=True, ignore_permissions=True)
    
    doc1 = frappe.get_doc({
        "doctype": "Workspace",
        "name": name1,
        "label": name1,
        "title": name1,
        "icon": "clipboard",
        "public": 1,
        "parent_page": "",
        "module": "KYA Services"
    })
    doc1.append("shortcuts", {"label": "KYA Form", "type": "DocType", "link_to": "KYA Form", "color": "Blue"})
    doc1.insert(ignore_permissions=True)
    print(f"DONE: {name1}")

    # 2. KYA Stagiaires
    name2 = "KYA Stagiaires"
    if frappe.db.exists("Workspace", name2):
        frappe.delete_doc("Workspace", name2, force=True, ignore_permissions=True)
    
    doc2 = frappe.get_doc({
        "doctype": "Workspace",
        "name": name2,
        "label": name2,
        "title": name2,
        "icon": "contact-round",
        "public": 1,
        "parent_page": "People",
        "module": "KYA HR"
    })
    doc2.append("shortcuts", {"label": "Permission Sortie Stagiaire", "type": "DocType", "link_to": "Permission Sortie Stagiaire"})
    doc2.insert(ignore_permissions=True)
    print(f"DONE: {name2}")

    # 3. Patch Buying
    if frappe.db.exists("Workspace", "Buying"):
        b = frappe.get_doc("Workspace", "Buying")
        if not any(s.label == "PV Sortie Materiel" for s in b.shortcuts):
            b.append("shortcuts", {"label": "PV Sortie Materiel", "type": "DocType", "link_to": "PV Sortie Materiel"})
        b.save(ignore_permissions=True)
        print("DONE: Patch Buying")

    frappe.db.commit()
    frappe.clear_cache()
    print("--- SUCCESS ---")

if __name__ == "__main__":
    run()

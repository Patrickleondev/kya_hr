import frappe

def fix_workspace():
    print("Fixing KYA HR Workspace...")
    try:
        ws_name = "KYA HR"
        if frappe.db.exists("Workspace", ws_name):
            # Sometimes delete fails if linked, but usually workspaces are safe to delete
            frappe.delete_doc("Workspace", ws_name, force=1)
        
        # In Frappe v14/15, 'title' and 'label' might be required 
        frappe.get_doc({
            "doctype": "Workspace",
            "name": ws_name,
            "title": "KYA RH & Op",
            "label": "KYA RH & Op",
            "icon": "users",
            "is_standard": 0,
            "public": 1,
            "parent_page": "",
            "links": [
                {"type": "Link", "label": "Demandes d'Achat", "link_type": "DocType", "link_to": "KYA Purchase Request"},
                {"type": "Link", "label": "Tickets de Sortie", "link_type": "DocType", "link_to": "KYA Exit Ticket"},
                {"type": "Link", "label": "Planning de Congés", "link_type": "DocType", "link_to": "KYA Leave Planning"},
                {"type": "Link", "label": "Permissions (Stagiaires)", "link_type": "DocType", "link_to": "KYA Permission Request"},
                {"type": "Link", "label": "Suivi Carburant", "link_type": "DocType", "link_to": "KYA Fuel Log"}
            ]
        }).insert(ignore_permissions=True)
        print("✅ Success: Workspace KYA HR perfectly recreated.")
    except Exception as e:
        print(f"❌ Error setting up workspace: {repr(e)}")

    frappe.db.commit()

def verify():
    print("\n--- Final Verification ---")
    dts = ["KYA Purchase Request", "KYA Leave Planning", "KYA Exit Ticket", "KYA Permission Request"]
    for dt in dts:
        print(f"{dt}: {'✅ Exists' if frappe.db.exists('DocType', dt) else '❌ Missing'}")
        
    wfs = ["KYA Procurement Flow", "Flux de Sortie Employé"]
    for wf in wfs:
        print(f"{wf}: {'✅ Active' if frappe.db.exists('Workflow', {'name': wf, 'is_active': 1}) else '❌ Missing or Inactive'}")

if __name__ == "__main__":
    fix_workspace()
    verify()

import frappe

def check_status():
    print("---- DocTypes in KYA HR ----")
    doctypes = frappe.get_all('DocType', filters={'module': 'KYA HR'}, fields=['name'])
    for d in doctypes:
        print(f" - {d.name}")

    print("\n---- KYA HR Workspace Links ----")
    try:
        ws = frappe.get_doc("Workspace", "KYA HR")
        for link in ws.links:
            print(f" - {link.label} -> {link.link_to} ({link.type})")
    except Exception as e:
        print(f"Error reading workspace: {e}")

    print("\n---- Workflows ----")
    workflows = frappe.get_all('Workflow', filters={'is_active': 1}, fields=['name', 'document_type'])
    for w in workflows:
        print(f" - {w.name} (for {w.document_type})")
        
    print("\n---- Roles Check ----")
    for r in ["Chef de Service", "Responsable RH", "DGA"]:
        print(f" - {r}: {frappe.db.exists('Role', r)}")

if __name__ == "__main__":
    check_status()

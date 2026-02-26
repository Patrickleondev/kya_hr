import frappe

def configure_workspace_and_roles():
    print("Updating KYA HR Workspace to include Purchase Requests...")

    def add_link_to_workspace(workspace_name, label, link_type, link_to):
        if not frappe.db.exists("Workspace", workspace_name): 
            print(f"Workspace {workspace_name} not found.")
            return
        
        ws = frappe.get_doc("Workspace", workspace_name)
        
        # Check if a link already exists
        link_exists = False
        for link in ws.links:
            if link.label == label or link.link_to == link_to:
                link_exists = True
                break
                
        if not link_exists:
            ws.append("links", {
                "type": "Link",
                "label": label,
                "link_type": link_type,
                "link_to": link_to,
                "hidden": 0
            })
            try:
                ws.save(ignore_permissions=True)
                print(f"Added link '{label}' to Workspace '{workspace_name}'")
            except Exception as e:
                print(f"Failed to add link to {workspace_name}: {e}")

    add_link_to_workspace("KYA HR", "Demandes d'Achat", "DocType", "KYA Purchase Request")
    frappe.db.commit()

    # Ensure Roles exist
    roles = ["Chef de Service", "Responsable des Achats", "Audit Interne", "DG", "DGA", "Comptabilité"]
    for r in roles:
        if not frappe.db.exists("Role", r):
            frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(ignore_permissions=True)
            print(f"Added Role: {r}")

    print("✅ Workspace and Roles checked.")

if __name__ == "__main__":
    configure_workspace_and_roles()

import frappe

def fix_workspace_and_roles():
    print("--- Fixing Roles ---")
    roles = ["Chef de Service", "Service RH", "DGA"]
    for r in roles:
        if not frappe.db.exists("Role", r):
            try:
                frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(ignore_permissions=True)
                print(f"Created Role: {r}")
            except Exception as e:
                print(f"Could not create role {r}: {e}")

    try:
        # Assign to Administrator for testing
        admin = frappe.get_doc("User", "Administrator")
        admin_roles = [has_role.role for has_role in admin.roles]
        added = False
        for r in roles:
            # Check if role exists in DB before assigning
            if frappe.db.exists("Role", r) and r not in admin_roles:
                admin.append("roles", {"role": r})
                added = True
        if added:
            admin.save(ignore_permissions=True)
            print("Assigned test roles to Administrator.")
    except Exception as e:
        print(f"Could not assign roles to Admin: {e}")

    print("--- Fixing Workspace Visibility ---")
    try:
        ws_name = "KYA HR"
        if frappe.db.exists("Workspace", ws_name):
            frappe.delete_doc("Workspace", ws_name)

        # Bare minimum working Workspace for Frappe v14/15/16
        ws = frappe.get_doc({
            "doctype": "Workspace",
            "name": ws_name,
            "label": "KYA RH & Op",
            "title": "KYA RH & Op",
            "type": "Workspace",
            "icon": "users",
            "public": 1,
            "for_user": "",
            "module": "KYA HR",
            "roles": [{"role": "All"}],
            "links": [
                {"type": "Link", "label": "Demandes d'Achat", "link_type": "DocType", "link_to": "KYA Purchase Request"},
                {"type": "Link", "label": "Tickets de Sortie", "link_type": "DocType", "link_to": "KYA Exit Ticket"},
                {"type": "Link", "label": "Planning de Congés", "link_type": "DocType", "link_to": "KYA Leave Planning"},
                {"type": "Link", "label": "Permissions (Stagiaires)", "link_type": "DocType", "link_to": "KYA Permission Request"},
                {"type": "Link", "label": "Suivi Carburant", "link_type": "DocType", "link_to": "KYA Fuel Log"}
            ]
        })
        ws.insert(ignore_permissions=True)
        print("Workspace KYA RH & Op created and assigned to 'All' role.")
    except Exception as e:
        print(f"Could not create Workspace: {e}")

    print("--- Update Exit Ticket Workflow Roles ---")
    try:
        if frappe.db.exists("Workflow", "Flux de Sortie Employé"):
            wf = frappe.get_doc("Workflow", "Flux de Sortie Employé")
            modified = False
            for state in wf.states:
                if state.allow_edit == "Responsable RH":
                    state.allow_edit = "Service RH"
                    modified = True
            for trans in wf.transitions:
                if trans.allowed == "Responsable RH":
                    trans.allowed = "Service RH"
                    modified = True
            if modified:
                wf.save(ignore_permissions=True)
                print("Updated Flux de Sortie Employé to use 'Service RH' instead of 'Responsable RH'")
    except Exception as e:
         print(f"Could not update workflow roles: {e}")

    frappe.db.commit()
    print("✅ All fixes applied.")

if __name__ == "__main__":
    fix_workspace_and_roles()

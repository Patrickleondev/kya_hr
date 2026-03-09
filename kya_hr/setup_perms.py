import frappe

def run():
    roles_required = [
        'Employee', 'Stagiaire', 'Chef Service', 'HR Manager', 
        'HR User', 'Guérite', 'Responsable Achats', 
        'Auditeur Interne', 'DAAF', 'Directeur Général'
    ]
    
    # 1. Ensure Roles exist
    for role_name in roles_required:
        if not frappe.db.exists('Role', role_name):
            frappe.get_doc({
                'doctype': 'Role',
                'role_name': role_name,
                'desk_access': 1
            }).insert(ignore_permissions=True)
            print(f"Created Role: {role_name}")
            
    # Commit roles before proceeding
    frappe.db.commit()

    # 2. Define DocType Permissions
    docperms = [
        # Employee Leaves Workspace DocTypes
        {'parent': 'Permission Sortie Stagiaire', 'role': 'Stagiaire', 'read': 1, 'write': 1, 'create': 1, 'submit': 1},
        {'parent': 'Permission Sortie Stagiaire', 'role': 'HR Manager', 'read': 1, 'write': 1, 'create': 0, 'submit': 1},
        {'parent': 'Employee Leave Planning', 'role': 'Employee', 'read': 1, 'write': 1, 'create': 1, 'submit': 1},
        
        # Procurement
        {'parent': 'Purchase Request', 'role': 'Employee', 'read': 1, 'write': 1, 'create': 1, 'submit': 1},
        {'parent': 'Purchase Request', 'role': 'Chef Service', 'read': 1, 'write': 1, 'submit': 1},
        {'parent': 'Purchase Order', 'role': 'Responsable Achats', 'read': 1, 'write': 1, 'create': 1, 'submit': 1},
        {'parent': 'Purchase Order', 'role': 'Auditeur Interne', 'read': 1},
        {'parent': 'Purchase Order', 'role': 'DAAF', 'read': 1},
        {'parent': 'Purchase Order', 'role': 'Directeur Général', 'read': 1, 'write': 1, 'submit': 1},

        # PV Sortie Materiel
        {'parent': 'PV Sortie Materiel', 'role': 'Employee', 'read': 1, 'write': 1, 'create': 1},
        {'parent': 'PV Sortie Materiel', 'role': 'Responsable Achats', 'read': 1, 'write': 1, 'submit': 1},
        {'parent': 'PV Sortie Materiel', 'role': 'Guérite', 'read': 1},
    ]

    for perm in docperms:
        if not frappe.db.exists('Custom DocPerm', {'parent': perm['parent'], 'role': perm['role']}):
            try:
                doc = frappe.new_doc('Custom DocPerm')
                doc.update(perm)
                doc.insert(ignore_permissions=True)
                print(f"Created Custom DocPerm for {perm['parent']} -> {perm['role']}")
            except Exception as e:
                print(f"Failed to create Custom DocPerm for {perm['parent']} -> {perm['role']}: {e}")

    # 3. Define Workspace Visibility
    try:
        if frappe.db.exists('Workspace', 'KYA Services'):
            ws = frappe.get_doc('Workspace', 'KYA Services')
            ws.public = 1
            ws.save(ignore_permissions=True)
            print("Set KYA Services Workspace to public")
            
        if frappe.db.exists('Workspace', 'KYA Stagiaires'):
            ws = frappe.get_doc('Workspace', 'KYA Stagiaires')
            ws.public = 0
            if not len([x for x in ws.roles if x.role == 'Stagiaire']):
                ws.append('roles', {'role': 'Stagiaire'})
                ws.save(ignore_permissions=True)
                print("Assigned Stagiaire role to KYA Stagiaires Workspace")
    except Exception as e:
        print(f"Failed to update Workspace permissions: {e}")

    frappe.db.commit()
    print("Permissions setup complete.")

if __name__ == '__main__':
    run()

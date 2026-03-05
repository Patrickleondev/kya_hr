import frappe

def run_fixes():
    print("--- STARTING UI & ROLE FIXES ---")
    
    # 1. Rename Role
    if frappe.db.exists('Role', 'Chef de Service'):
        role = frappe.get_doc('Role', 'Chef de Service')
        role.role_name = 'Chef Service'
        # Note: Saving a DocType/Role with a new name might require a rename_doc
        frappe.rename_doc('Role', 'Chef de Service', 'Chef Service', force=True)
        print("Renamed Role: Chef de Service -> Chef Service")

    # 2. Update Workspaces
    # 2.1 Workspace: Leaves (Congés)
    if frappe.db.exists('Workspace', 'Leaves'):
        ws = frappe.get_doc('Workspace', 'Leaves')
        ws.is_standard = 0
        ws.public = 1
        
        needed_shortcuts = [
            {'type': 'DocType', 'link_to': 'Planning des Conges', 'label': 'Planning des Congés', 'icon': 'calendar'},
            {'type': 'DocType', 'link_to': 'Demande de Permission', 'label': 'Demandes de Permission', 'icon': 'clock'}
        ]
        
        for s in needed_shortcuts:
            if not any(exist.link_to == s['link_to'] for exist in ws.shortcuts):
                ws.append('shortcuts', s)
        
        ws.save()
        print("Updated Workspace: Leaves with shortcuts")

    # 2.2 Workspace: KYA Stagiaires
    if frappe.db.exists('Workspace', 'KYA Stagiaires'):
        ws = frappe.get_doc('Workspace', 'KYA Stagiaires')
        ws.is_standard = 0
        ws.public = 1
        
        needed_shortcuts = [
            {'type': 'DocType', 'link_to': 'Planning des Conges', 'label': 'Planning (Stagiaires)', 'icon': 'calendar'},
            {'type': 'DocType', 'link_to': 'Permission de Sortie', 'label': 'Mes Permissions', 'icon': 'clock'}
        ]
        
        for s in needed_shortcuts:
            if not any(exist.link_to == s['link_to'] for exist in ws.shortcuts):
                ws.append('shortcuts', s)
        
        ws.save()
        print("Updated Workspace: KYA Stagiaires with shortcuts")

    # 3. Update Workflows to use new role name
    workflows = frappe.get_all('Workflow', filters={'document_type': ['in', ['PV Sortie Materiel', 'Planning des Conges', 'Demande Achat KYA', 'Permission de Sortie']]})
    for wf_info in workflows:
        wf = frappe.get_doc('Workflow', wf_info.name)
        updated = False
        for transition in wf.transitions:
            if transition.allowed == 'Chef de Service':
                transition.allowed = 'Chef Service'
                updated = True
        for state in wf.states:
            if state.allow_edit == 'Chef de Service':
                state.allow_edit = 'Chef Service'
                updated = True
        if updated:
            wf.save()
            print(f"Updated Workflow: {wf.name} (Role mapping updated to Chef Service)")

    frappe.db.commit()
    print("--- UI & ROLE FIXES COMPLETED ---")

if __name__ == "__main__":
    run_fixes()

import frappe

def verify():
    print("\n--- HRMS v2 Deployment Verification ---")
    
    # 1. Workflows
    wf_leave = frappe.db.get_list('Workflow', {'document_type': 'KYA Leave Planning'}, 'workflow_name')
    print(f"Workflow Leave Planning: {'✅ ' + wf_leave[0].workflow_name if wf_leave else '❌ Missing'}")
    
    wf_perm = frappe.db.get_list('Workflow', {'document_type': 'KYA Permission Request'}, 'workflow_name')
    print(f"Workflow Permission Stagiaire: {'✅ ' + wf_perm[0].workflow_name if wf_perm else '❌ Missing'}")
    
    wf_exit = frappe.db.get_list('Workflow', {'document_type': 'KYA Exit Ticket'}, 'workflow_name')
    print(f"Workflow Exit Ticket: {'✅ ' + wf_exit[0].workflow_name if wf_exit else '❌ Missing'}")
    
    # 2. Workspace
    ws_name = "KYA RH & Op"
    if frappe.db.exists("Workspace", ws_name):
        ws = frappe.get_doc("Workspace", ws_name)
        labels = [l.label for l in ws.links]
        print(f"Workspace '{ws_name}' Links: {labels}")
        chart_links = [c.chart_name for c in ws.charts]
        print(f"Workspace '{ws_name}' Charts: {chart_links}")
        card_links = [n.number_card for n in ws.number_cards]
        print(f"Workspace '{ws_name}' Number Cards: {card_links}")
    else:
        print(f"❌ Workspace '{ws_name}' Missing")

    # 3. Dashboards
    db_exists = frappe.db.exists("Dashboard", "Dashboard RH KYA")
    print(f"Dashboard 'Dashboard RH KYA': {'✅ Exists' if db_exists else '❌ Missing'}")

    # 4. Roles
    roles = ["Responsable Stage", "Service RH", "Chef de Service"]
    for r in roles:
        print(f"Role '{r}': {'✅ Exists' if frappe.db.exists('Role', r) else '❌ Missing'}")

if __name__ == "__main__":
    verify()

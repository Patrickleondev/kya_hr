import frappe
import traceback

def deploy_procurement():
    print("--- 1. Procurement DocTypes ---")
    try:
        if not frappe.db.exists("DocType", "KYA Purchase Item"):
            doc = frappe.get_doc({
                "doctype": "DocType", "name": "KYA Purchase Item", "module": "KYA HR", "custom": 1, "istable": 1,
                "fields": [
                    {"fieldname": "item_name", "label": "Article", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "qty", "label": "Qté", "fieldtype": "Float", "reqd": 1, "in_list_view": 1, "default": "1"},
                    {"fieldname": "estimated_rate", "label": "PU Estimé", "fieldtype": "Currency", "in_list_view": 1},
                    {"fieldname": "estimated_amount", "label": "Total Estimé", "fieldtype": "Currency", "in_list_view": 1}
                ]
            })
            doc.insert(ignore_permissions=True)
            print("Created KYA Purchase Item")
    except Exception as e:
        print(f"Error creating KYA Purchase Item: {e}")
        traceback.print_exc()

    try:
        if not frappe.db.exists("DocType", "KYA Purchase Request"):
            frappe.get_doc({
                "doctype": "DocType", "name": "KYA Purchase Request", "module": "KYA HR", "custom": 1, 
                "autoname": "KYA-PR-.YYYY.-.####", "is_submittable": 0, "track_changes": 1, "has_web_view": 1, "allow_guest_to_view": 1,
                "fields": [
                    {"fieldname": "requester", "label": "Demandeur", "fieldtype": "Link", "options": "Employee", "reqd": 1},
                    {"fieldname": "department", "label": "Département", "fieldtype": "Link", "options": "Department", "fetch_from": "requester.department"},
                    {"fieldname": "date", "label": "Date", "fieldtype": "Date", "default": "Today"},
                    {"fieldname": "urgency", "label": "Urgence", "fieldtype": "Select", "options": "Normale\nUrgente"},
                    {"fieldname": "purpose", "label": "Objet", "fieldtype": "Data", "reqd": 1},
                    {"fieldname": "description", "label": "Description", "fieldtype": "Text Editor"},
                    {"fieldname": "items", "label": "Articles", "fieldtype": "Table", "options": "KYA Purchase Item"},
                    {"fieldname": "requester_signature", "label": "Sign Demandeur", "fieldtype": "Signature"},
                    {"fieldname": "selected_supplier", "label": "Fournisseur", "fieldtype": "Link", "options": "Supplier"},
                    {"fieldname": "total_amount", "label": "Total Devis", "fieldtype": "Currency"},
                    {"fieldname": "purchasing_signature", "label": "Sign Achats", "fieldtype": "Signature"},
                    {"fieldname": "audit_signature", "label": "Sign Audit", "fieldtype": "Signature"},
                    {"fieldname": "dg_signature", "label": "Sign DG", "fieldtype": "Signature"},
                    {"fieldname": "workflow_state", "label": "Statut", "fieldtype": "Data", "read_only": 1, "hidden": 1}
                ],
                "permissions": [
                    {"role": "Employee", "read": 1, "write": 1, "create": 1},
                    {"role": "Chef de Service", "read": 1, "write": 1},
                    {"role": "Responsable RH", "read": 1, "write": 1},
                    {"role": "Audit Interne", "read": 1, "write": 1},
                    {"role": "DG", "read": 1, "write": 1},
                    {"role": "Comptabilité", "read": 1, "write": 1}
                ]
            }).insert(ignore_permissions=True)
            print("Created KYA Purchase Request")
    except Exception as e:
        print(f"Error creating KYA Purchase Request: {e}")
        traceback.print_exc()

def deploy_procurement_workflow():
    print("--- 2. Procurement Workflow ---")
    states = ["Brouillon", "En attente Validation Chef", "En attente Sourcing", "En attente Visa Audit", "En attente Validation DG", "Approuvé (Bon à payer)", "Achat Clôturé", "Rejeté"]
    for s in states:
        if not frappe.db.exists("Workflow State", s):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s}).insert(ignore_permissions=True)

    if frappe.db.exists("Workflow", "KYA Procurement Flow"): frappe.delete_doc("Workflow", "KYA Procurement Flow")
    
    try:
        frappe.get_doc({
            "doctype": "Workflow", "workflow_name": "KYA Procurement Flow", "document_type": "KYA Purchase Request", "is_active": 1,
            "states": [
                {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee"},
                {"state": "En attente Validation Chef", "doc_status": 0, "allow_edit": "Chef de Service"},
                {"state": "En attente Sourcing", "doc_status": 0, "allow_edit": "Responsable RH"},
                {"state": "En attente Visa Audit", "doc_status": 0, "allow_edit": "Audit Interne"},
                {"state": "En attente Validation DG", "doc_status": 0, "allow_edit": "DG"},
                {"state": "Approuvé (Bon à payer)", "doc_status": 1, "allow_edit": "Comptabilité"},
                {"state": "Achat Clôturé", "doc_status": 1, "allow_edit": "Comptabilité"},
                {"state": "Rejeté", "doc_status": 0, "allow_edit": "Employee"}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente Validation Chef", "allowed": "Employee"},
                {"state": "En attente Validation Chef", "action": "Valider", "next_state": "En attente Sourcing", "allowed": "Chef de Service"},
                {"state": "En attente Validation Chef", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Chef de Service"},
                {"state": "En attente Sourcing", "action": "Transmettre Audit", "next_state": "En attente Visa Audit", "allowed": "Responsable RH"},
                {"state": "En attente Visa Audit", "action": "Viser", "next_state": "En attente Validation DG", "allowed": "Audit Interne"},
                {"state": "En attente Validation DG", "action": "Approuver", "next_state": "Approuvé (Bon à payer)", "allowed": "DG"},
                {"state": "Approuvé (Bon à payer)", "action": "Clôturer", "next_state": "Achat Clôturé", "allowed": "Comptabilité"}
            ]
        }).insert(ignore_permissions=True)
        print("Created KYA Procurement Flow")
    except Exception as e:
        print(f"Error creating workflow KYA Procurement Flow: {e}")
        traceback.print_exc()

def update_exit_workflow():
    print("--- 3. Employee Exit Workflow (Flux de Sortie Employé) ---")
    try:
        states = ["Brouillon", "En attente Chef de service", "En attente RH", "En attente DGA", "Autorisation Finale", "Approuvé", "Rejeté"]
        for s in states:
            if not frappe.db.exists("Workflow State", s):
                frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s}).insert(ignore_permissions=True)

        wf_name = "Flux de Sortie Employé"
        if frappe.db.exists("Workflow", wf_name): frappe.delete_doc("Workflow", wf_name)
        
        frappe.get_doc({
            "doctype": "Workflow", "workflow_name": wf_name, "document_type": "KYA Exit Ticket", "is_active": 1,
            "states": [
                {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee"},
                {"state": "En attente Chef de service", "doc_status": 0, "allow_edit": "Chef de Service"},
                {"state": "En attente RH", "doc_status": 0, "allow_edit": "Responsable RH"},
                {"state": "En attente DGA", "doc_status": 0, "allow_edit": "DGA"},
                {"state": "Autorisation Finale", "doc_status": 0, "allow_edit": "System Manager"}, 
                {"state": "Approuvé", "doc_status": 1, "allow_edit": "System Manager"},
                {"state": "Rejeté", "doc_status": 0, "allow_edit": "Employee"}
            ],
            "transitions": [
                {"state": "Brouillon", "action": "Déposer", "next_state": "En attente Chef de service", "allowed": "Employee"},
                {"state": "En attente Chef de service", "action": "Approuver (Chef)", "next_state": "En attente RH", "allowed": "Chef de Service"},
                {"state": "En attente Chef de service", "action": "Forcer Approbation (RH)", "next_state": "En attente RH", "allowed": "Responsable RH"},
                {"state": "En attente Chef de service", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Chef de Service"},
                {"state": "En attente RH", "action": "Approuver (RH)", "next_state": "En attente DGA", "allowed": "Responsable RH"},
                {"state": "En attente RH", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Responsable RH"},
                {"state": "En attente DGA", "action": "Approuver (DGA)", "next_state": "Autorisation Finale", "allowed": "DGA"},
                {"state": "En attente DGA", "action": "Approuver (par Délégation)", "next_state": "Autorisation Finale", "allowed": "Responsable RH"},
                {"state": "En attente DGA", "action": "Rejeter", "next_state": "Rejeté", "allowed": "DGA"},
                {"state": "Autorisation Finale", "action": "Accorder Sortie", "next_state": "Approuvé", "allowed": "System Manager"}
            ]
        }).insert(ignore_permissions=True)
        print("Updated Flux de Sortie Employé")
    except Exception as e:
        print(f"Error creating Exit Workflow: {e}")
        traceback.print_exc()

def setup_workspaces():
    print("--- 4. Workspace setup ---")
    try:
        if not frappe.db.exists("Workspace", "KYA HR"):
            ws = frappe.get_doc({
                "doctype": "Workspace", "name": "KYA HR", "label": "KYA RH & Op." , "icon": "users", "is_standard": 0, "public": 1,
                "parent_page": "",
                "links": [
                    {"type": "Link", "label": "Demandes d'Achat", "link_type": "DocType", "link_to": "KYA Purchase Request"},
                    {"type": "Link", "label": "Tickets de Sortie", "link_type": "DocType", "link_to": "KYA Exit Ticket"},
                    {"type": "Link", "label": "Planning de Congés", "link_type": "DocType", "link_to": "KYA Leave Planning"},
                    {"type": "Link", "label": "Permissions (Stagiaires)", "link_type": "DocType", "link_to": "KYA Permission Request"}
                ]
            })
            ws.insert(ignore_permissions=True)
            print("Created Workspace KYA HR")
        else:
            ws = frappe.get_doc("Workspace", "KYA HR")
            ws.label = "KYA RH & Op."
            links_to_add = ["KYA Purchase Request", "KYA Exit Ticket", "KYA Leave Planning", "KYA Permission Request"]
            existing = [l.link_to for l in ws.links]
            for l in links_to_add:
                if l not in existing:
                    ws.append("links", {"type": "Link", "label": l, "link_type": "DocType", "link_to": l})
            ws.save(ignore_permissions=True)
            print("Updated Workspace KYA HR")
    except Exception as e:
        print(f"Error setting up workspaces: {e}")
        traceback.print_exc()

if frappe.db:
    deploy_procurement()
    deploy_procurement_workflow()
    update_exit_workflow()
    setup_workspaces()
    frappe.db.commit()
    print("✅ Finished.")


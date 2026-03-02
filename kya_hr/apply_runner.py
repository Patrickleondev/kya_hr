import frappe

def deploy_procurement():
    print("--- 1. Procurement DocTypes ---")
    try:
        if not frappe.db.exists("DocType", "KYA Purchase Item"):
            frappe.get_doc({
                "doctype": "DocType", "name": "KYA Purchase Item", "module": "KYA HR", "custom": 1, "istable": 1,
                "fields": [
                    {"fieldname": "item_name", "label": "Article", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                    {"fieldname": "qty", "label": "Qté", "fieldtype": "Float", "reqd": 1, "in_list_view": 1, "default": "1"},
                    {"fieldname": "estimated_rate", "label": "PU Estimé", "fieldtype": "Currency", "in_list_view": 1},
                    {"fieldname": "estimated_amount", "label": "Total Estimé", "fieldtype": "Currency", "in_list_view": 1}
                ]
            }).insert(ignore_permissions=True)
            print("Created KYA Purchase Item")
        else:
            print("KYA Purchase Item already exists")

        if not frappe.db.exists("DocType", "KYA Purchase Request"):
            frappe.get_doc({
                "doctype": "DocType", "name": "KYA Purchase Request", "module": "KYA HR", "custom": 1, 
                "autoname": "KYA-PR-.YYYY.-.####", "is_submittable": 0, "track_changes": 1,
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
        else:
            print("KYA Purchase Request already exists")
    except Exception as e:
        print(f"Error creating DocTypes: {repr(e)}")

def create_workflow_actions(actions):
    for a in actions:
        if not frappe.db.exists("Workflow Action Master", a):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert(ignore_permissions=True)

def deploy_procurement_workflow():
    print("--- 2. Procurement Workflow ---")
    try:
        states = ["Brouillon", "En attente Validation Chef", "En attente Sourcing", "En attente Visa Audit", "En attente Validation DG", "Approuvé (Bon à payer)", "Achat Clôturé", "Rejeté"]
        for s in states:
            if not frappe.db.exists("Workflow State", s):
                frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s}).insert(ignore_permissions=True)

        create_workflow_actions(["Soumettre", "Valider", "Rejeter", "Transmettre Audit", "Viser", "Approuver", "Clôturer"])

        wf_name = "KYA Procurement Flow"
        if frappe.db.exists("Workflow", wf_name):
            frappe.delete_doc("Workflow", wf_name)
        
        frappe.get_doc({
            "doctype": "Workflow", "workflow_name": wf_name, "document_type": "KYA Purchase Request", "is_active": 1,
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
        print(f"Error creating Procurement Flow: {repr(e)}")

def update_exit_workflow():
    print("--- 3. Employee Exit Workflow (Flux de Sortie Employé) ---")
    try:
        states = ["Brouillon", "En attente Chef de service", "En attente RH", "En attente DGA", "Autorisation Finale", "Approuvé", "Rejeté"]
        for s in states:
            if not frappe.db.exists("Workflow State", s):
                frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s}).insert(ignore_permissions=True)

        create_workflow_actions(["Déposer", "Approuver (Chef)", "Forcer Approbation (RH)", "Rejeter", "Approuver (RH)", "Approuver (DGA)", "Approuver (par Délégation)", "Accorder Sortie"])

        wf_name = "Flux de Sortie Employé"
        if frappe.db.exists("Workflow", wf_name):
            frappe.delete_doc("Workflow", wf_name)
        
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
        print(f"Error creating Exit Workflow: {repr(e)}")

def setup_workspaces():
    print("--- 4. Workspace setup ---")
    try:
        ws_name = "KYA HR"
        if frappe.db.exists("Workspace", ws_name):
            frappe.delete_doc("Workspace", ws_name)
            
        frappe.get_doc({
            "doctype": "Workspace", "name": ws_name, "label": "KYA RH & Opérations", "icon": "users", "is_standard": 0, "public": 1,
            "parent_page": "",
            "links": [
                {"type": "Link", "label": "Demandes d'Achat", "link_type": "DocType", "link_to": "KYA Purchase Request"},
                {"type": "Link", "label": "Tickets de Sortie", "link_type": "DocType", "link_to": "KYA Exit Ticket"},
                {"type": "Link", "label": "Planning de Congés", "link_type": "DocType", "link_to": "KYA Leave Planning"},
                {"type": "Link", "label": "Permissions (Stagiaires)", "link_type": "DocType", "link_to": "KYA Permission Request"}
            ]
        }).insert(ignore_permissions=True)
        print("Created Workspace KYA HR")
    except Exception as e:
        print(f"Error setting up workspaces: {repr(e)}")

def fix_web_form_fields():
    print("--- 5. Fix Web Form Fields ---")
    try:
        wf_name = "KYA Purchase Request Web Form"
        if frappe.db.exists("Web Form", wf_name):
            wf = frappe.get_doc("Web Form", wf_name)
        else:
            wf = frappe.get_doc({
                "doctype": "Web Form",
                "title": "Demande d'Achat KYA",
                "route": "demande-achat-kya",
                "doc_type": "KYA Purchase Request",
                "published": 1,
                "is_standard": 0,
                "login_required": 1,
                "allow_multiple": 1,
            })

        # Clear existing fields
        wf.web_form_fields = []
        wf.route = "demande-achat-kya"
        wf.published = 1

        fields = [
            {"fieldname": "requester", "label": "Demandeur", "fieldtype": "Link", "options": "Employee", "reqd": 1},
            {"fieldname": "department", "label": "Departement", "fieldtype": "Link", "options": "Department", "reqd": 0},
            {"fieldname": "purpose", "label": "Objet de Achat", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "description", "label": "Description", "fieldtype": "Text Editor", "reqd": 0},
            {"fieldname": "urgency", "label": "Urgence", "fieldtype": "Select", "options": "Normale\nUrgente", "reqd": 0},
        ]
        for f in fields:
            wf.append("web_form_fields", f)

        if frappe.db.exists("Web Form", wf_name):
            wf.save(ignore_permissions=True)
        else:
            wf.insert(ignore_permissions=True)

        count = len(wf.web_form_fields)
        print(f"Web Form saved with {count} fields at /demande-achat-kya")
    except Exception as e:
        print(f"Error fixing web form: {repr(e)}")


def fix_intern_visibility_script():
    print("--- 6. Intern Fields Client Script ---")
    try:
        cs_name = "KYA Intern Fields Visibility"
        script_code = """frappe.ui.form.on('Employee', {
    employment_type: function(frm) {
        var is_intern = (frm.doc.employment_type === 'Intern');
        frm.set_df_property('stage_domain', 'hidden', is_intern ? 0 : 1);
        frm.set_df_property('maitre_de_stage', 'hidden', is_intern ? 0 : 1);
        frm.refresh_fields(['stage_domain', 'maitre_de_stage']);
    },
    onload: function(frm) {
        var is_intern = (frm.doc.employment_type === 'Intern');
        frm.set_df_property('stage_domain', 'hidden', is_intern ? 0 : 1);
        frm.set_df_property('maitre_de_stage', 'hidden', is_intern ? 0 : 1);
    }
});"""
        if frappe.db.exists("Client Script", cs_name):
            frappe.db.set_value("Client Script", cs_name, "script", script_code)
            frappe.db.set_value("Client Script", cs_name, "enabled", 1)
            print("Client Script updated.")
        else:
            frappe.get_doc({
                "doctype": "Client Script",
                "name": cs_name,
                "dt": "Employee",
                "view": "Form",
                "enabled": 1,
                "script": script_code,
            }).insert(ignore_permissions=True)
            print("Client Script created.")
    except Exception as e:
        print(f"Error creating client script: {repr(e)}")


def main():
    try:
        deploy_procurement()
        deploy_procurement_workflow()
        update_exit_workflow()
        setup_workspaces()
        fix_web_form_fields()
        fix_intern_visibility_script()
        frappe.db.commit()
        frappe.clear_cache()
        print("Finished.")
    except Exception as e:
        print(f"Global error: {repr(e)}")

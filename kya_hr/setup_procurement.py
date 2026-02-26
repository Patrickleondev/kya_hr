import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_doctypes():
    print("Creating KYA Purchase Item (Child Table)...")
    if not frappe.db.exists("DocType", "KYA Purchase Item"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Purchase Item",
            "module": "KYA HR",
            "custom": 1,
            "istable": 1,
            "fields": [
                {"fieldname": "item_name", "label": "Article / Description", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                {"fieldname": "qty", "label": "Quantité", "fieldtype": "Float", "reqd": 1, "in_list_view": 1, "default": "1"},
                {"fieldname": "estimated_rate", "label": "Prix Unitaire Estimé", "fieldtype": "Currency", "in_list_view": 1},
                {"fieldname": "estimated_amount", "label": "Montant Total Estimé", "fieldtype": "Currency", "in_list_view": 1, "read_only": 1}
            ]
        })
        doc.insert(ignore_permissions=True)
        print("✅ KYA Purchase Item created.")

    print("Creating KYA Purchase Request...")
    if not frappe.db.exists("DocType", "KYA Purchase Request"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": "KYA Purchase Request",
            "module": "KYA HR",
            "custom": 1,
            "autoname": "KYA-PR-.YYYY.-.####",
            "is_submittable": 0,
            "track_changes": 1,
            "has_web_view": 1,
            "allow_guest_to_view": 1,
            "fields": [
                # A. Informations Générales (Demandeur)
                {"fieldname": "sb_general", "label": "1. Informations Générales", "fieldtype": "Section Break"},
                {"fieldname": "requester", "label": "Demandeur", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
                {"fieldname": "department", "label": "Département", "fieldtype": "Link", "options": "Department", "fetch_from": "requester.department", "read_only": 1},
                {"fieldname": "cb_1", "fieldtype": "Column Break"},
                {"fieldname": "date", "label": "Date de demande", "fieldtype": "Date", "reqd": 1, "default": "Today", "in_list_view": 1},
                {"fieldname": "urgency", "label": "Niveau d'Urgence", "fieldtype": "Select", "options": "Normale\nUrgente", "default": "Normale"},
                
                {"fieldname": "sb_details", "label": "Détails de la demande", "fieldtype": "Section Break"},
                {"fieldname": "purpose", "label": "Objet de l'achat", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
                {"fieldname": "description", "label": "Description / Spécifications (Cahier des charges)", "fieldtype": "Text Editor", "reqd": 1},
                {"fieldname": "items", "label": "Articles demandés", "fieldtype": "Table", "options": "KYA Purchase Item"},
                {"fieldname": "requester_signature", "label": "Signature Demandeur", "fieldtype": "Signature"},

                # B. Traitement Sourcing (Responsable Achats)
                {"fieldname": "sb_sourcing", "label": "2. Sourcing et Devis (Service Achats)", "fieldtype": "Section Break", "depends_on": "eval:doc.workflow_state != 'Brouillon' && doc.workflow_state != 'En attente Validation Chef'"},
                {"fieldname": "selected_supplier", "label": "Fournisseur Retenu", "fieldtype": "Link", "options": "Supplier"},
                {"fieldname": "total_amount", "label": "Montant Total (Devis retenu)", "fieldtype": "Currency"},
                {"fieldname": "cb_2", "fieldtype": "Column Break"},
                {"fieldname": "proforma_attachment", "label": "Devis / Pro-forma", "fieldtype": "Attach"},
                {"fieldname": "purchasing_signature", "label": "Signature Responsable Achats", "fieldtype": "Signature"},

                # C. Visas et Validation
                {"fieldname": "sb_visas", "label": "3. Visas et Validations", "fieldtype": "Section Break", "depends_on": "eval:doc.workflow_state != 'Brouillon'"},
                {"fieldname": "dept_head_signature", "label": "Signature Chef Département", "fieldtype": "Signature"},
                {"fieldname": "audit_signature", "label": "Signature Audit Interne", "fieldtype": "Signature", "depends_on": "eval:in_list(['En attente Visa Audit', 'En attente Validation DG', 'Approuvé (Bon à payer)', 'Achat Clôturé'], doc.workflow_state)"},
                {"fieldname": "dg_signature", "label": "Signature Directeur Général", "fieldtype": "Signature", "depends_on": "eval:in_list(['En attente Validation DG', 'Approuvé (Bon à payer)', 'Achat Clôturé'], doc.workflow_state)"},

                # Workflow State hidden
                {"fieldname": "workflow_state", "label": "Statut Workflow", "fieldtype": "Data", "read_only": 1, "hidden": 1}
            ],
            "permissions": [
                {"role": "Employee", "read": 1, "write": 1, "create": 1},
                {"role": "Chef de Service", "read": 1, "write": 1},
                {"role": "Responsable des Achats", "read": 1, "write": 1},
                {"role": "Audit Interne", "read": 1, "write": 1},
                {"role": "DG", "read": 1, "write": 1},
                {"role": "DGA", "read": 1, "write": 1},
                {"role": "Comptabilité", "read": 1, "write": 1}
            ]
        })
        doc.insert(ignore_permissions=True)
        print("✅ KYA Purchase Request created.")

def create_workflow():
    print("Creating KYA Procurement Flow...")
    
    # 1. Create States
    states = [
        ("Brouillon", "Draft"),
        ("En attente Validation Chef", "Pending"),
        ("En attente Sourcing", "Pending"),
        ("En attente Visa Audit", "Pending"),
        ("En attente Validation DG", "Pending"),
        ("Approuvé (Bon à payer)", "Approved"),
        ("Achat Clôturé", "Completed"),
        ("Rejeté", "Rejected")
    ]
    for s, d in states:
        if not frappe.db.exists("Workflow State", s):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s, "icon": "check", "style": "Primary" if d in ["Draft", "Pending"] else "Success" if d in ["Approved", "Completed"] else "Danger"}).insert(ignore_permissions=True)

    # 2. Check if specific Roles exist, fallback to System Manager if missing (though the user established them earlier)
    # We assume 'Chef de Service', 'Responsable des Achats', 'Audit Interne', 'DG', 'Comptabilité' exist based on previous tasks.

    if frappe.db.exists("Workflow", "KYA Procurement Flow"):
        frappe.delete_doc("Workflow", "KYA Procurement Flow")

    doc = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": "KYA Procurement Flow",
        "document_type": "KYA Purchase Request",
        "is_active": 1,
        "states": [
            {"state": "Brouillon", "doc_status": 0, "allow_edit": "Employee"},
            {"state": "En attente Validation Chef", "doc_status": 0, "allow_edit": "Chef de Service"},
            {"state": "En attente Sourcing", "doc_status": 0, "allow_edit": "Responsable des Achats"},
            {"state": "En attente Visa Audit", "doc_status": 0, "allow_edit": "Audit Interne"},
            {"state": "En attente Validation DG", "doc_status": 0, "allow_edit": "DG"},
            {"state": "Approuvé (Bon à payer)", "doc_status": 1, "allow_edit": "Comptabilité"},
            {"state": "Achat Clôturé", "doc_status": 1, "allow_edit": "Comptabilité"},
            {"state": "Rejeté", "doc_status": 0, "allow_edit": "System Manager"}
        ],
        "transitions": [
            {"state": "Brouillon", "action": "Soumettre", "next_state": "En attente Validation Chef", "allowed": "Employee"},
            {"state": "En attente Validation Chef", "action": "Valider", "next_state": "En attente Sourcing", "allowed": "Chef de Service"},
            {"state": "En attente Validation Chef", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Chef de Service"},
            
            {"state": "En attente Sourcing", "action": "Devis joints, transmettre à l'audit", "next_state": "En attente Visa Audit", "allowed": "Responsable des Achats"},
            
            {"state": "En attente Visa Audit", "action": "Viser", "next_state": "En attente Validation DG", "allowed": "Audit Interne"},
            {"state": "En attente Visa Audit", "action": "Rejeter", "next_state": "Rejeté", "allowed": "Audit Interne"},
            
            {"state": "En attente Validation DG", "action": "Approuver (Bon à payer)", "next_state": "Approuvé (Bon à payer)", "allowed": "DG"},
            {"state": "En attente Validation DG", "action": "Rejeter", "next_state": "Rejeté", "allowed": "DG"},
            
            {"state": "Approuvé (Bon à payer)", "action": "Clôturer l'achat", "next_state": "Achat Clôturé", "allowed": "Comptabilité"}
        ]
    })
    doc.insert(ignore_permissions=True)
    print("✅ KYA Procurement Flow created and activated.")

if __name__ == "__main__":
    create_doctypes()
    create_workflow()

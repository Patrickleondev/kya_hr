import frappe

def create_web_form():
    print("Creating Web Form for KYA Purchase Request...")
    if frappe.db.exists("Web Form", "KYA Purchase Request Web Form"):
        frappe.delete_doc("Web Form", "KYA Purchase Request Web Form")
        
    doc = frappe.get_doc({
        "doctype": "Web Form",
        "title": "Fiche de Compte Rendu d'Intervention / Demande d'Achat",
        "route": "purchase-request",
        "doc_type": "KYA Purchase Request",
        "module": "KYA HR",
        "is_standard": 1,
        "published": 1,
        "login_required": 1,
        "allow_edit": 1,
        "allow_multiple": 1,
        "success_title": "Demande Enregistrée",
        "success_message": "Votre demande a été soumise avec succès et est en attente de validation.",
        "button_label": "Enregistrer la fiche",
        "web_form_fields": [
            # Auto-mapped from DocType in standard usage, but we will rely on custom HTML layout
            {"fieldname": "purpose", "fieldtype": "Data", "label": "Objet de l'achat"},
            {"fieldname": "requester", "fieldtype": "Link", "options": "Employee", "label": "Demandeur"},
            {"fieldname": "date", "fieldtype": "Date", "label": "Date"},
            {"fieldname": "description", "fieldtype": "Text Editor", "label": "Description"},
            {"fieldname": "requester_signature", "fieldtype": "Signature", "label": "Signature Demandeur"}
        ],
        "custom_html": """
<style>
    .kya-form-container { max-width: 800px; margin: auto; padding: 20px; font-family: sans-serif; }
    .kya-header { display: flex; flex-direction: column; align-items: center; text-align: center; border-bottom: 2px solid #1a5276; padding-bottom: 20px; margin-bottom: 25px; }
    .kya-logo { max-height: 70px; }
    .kya-title { margin: 0; color: #1a5276; font-size: 24px; font-weight: bold; }
    .kya-slogan { font-style: italic; color: #3498db; margin-top: 5px; }
    .kya-section { margin-bottom: 30px; }
    .kya-section-title { background: #1a5276; color: white; padding: 8px; font-weight: bold; margin-bottom: 15px; border-radius: 4px; }
    .kya-form-group { margin-bottom: 15px; }
    .kya-label { display: block; font-weight: bold; margin-bottom: 5px; }
    .kya-pad { border: 1px solid #ccc; background: #fff; border-radius: 4px; width: 100%; height: 120px; touch-action: none; }
    .kya-btn-clear { margin-top: 5px; font-size: 10px; cursor: pointer; background: none; border: 1px solid #ccc; padding: 2px 10px; border-radius: 3px; }
    /* Hide default frappe forms as we are injecting custom layout if needed, though standard layout is usually preferred for data binding */
</style>

<div class="kya-form-container">
    <div class="kya-header">
        <div class="logo-section" style="margin-bottom:15px">
            <img src="/files/kya logo.png" alt="Logo KYA" class="kya-logo">
        </div>
        <div class="title-section">
            <h2 class="kya-title">DEMANDE D'ACHAT / INTERVENTION</h2>
            <div class="kya-slogan">Move beyond the sky!</div>
        </div>
    </div>
    
    <div class="alert alert-info">
        Remplissez les informations de base ci-dessous. Le circuit de validation prendra ensuite le relais.
    </div>
    
    <!-- Standard frappe form fields will render below this HTML block -->
</div>
        """
    })
    doc.insert(ignore_permissions=True)
    print("✅ KYA Purchase Request Web Form created.")

if __name__ == "__main__":
    create_web_form()

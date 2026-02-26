import frappe

def create_email_alerts():
    print("Configuring Email Alerts for KYA Procurement...")

    # Creating an Email Template with KYA branding for Purchase Requests
    if not frappe.db.exists("Email Template", "KYA Purchase Request Alert"):
        doc = frappe.get_doc({
            "doctype": "Email Template",
            "name": "KYA Purchase Request Alert",
            "subject": "Nouvelle Action Requise : Demande d'Achat N° {{ doc.name }}",
            "response": """
<div style="font-family: Arial, sans-serif; color: #333;">
    <div style="text-align: center; border-bottom: 2px solid #1a5276; padding-bottom: 10px;">
        <img src="/files/kya logo.png" alt="KYA Energy Group" style="max-height: 50px;">
    </div>
    <h3 style="color: #1a5276;">Notification de Procédure d'Achat</h3>
    <p>Bonjour,</p>
    <p>La demande d'achat <strong>{{ doc.name }}</strong> (Objet: {{ doc.purpose }}) initiée par <strong>{{ doc.requester }}</strong> requiert votre attention.</p>
    <p><strong>Statut actuel :</strong> <span style="color: #d35400; font-weight: bold;">{{ doc.workflow_state }}</span></p>
    <p><strong>Urgence :</strong> {{ doc.urgency }}</p>
    <br>
    <p>Merci de vous connecter au portail KYA HR pour traiter cette demande.</p>
    <a href="/app/kya-purchase-request/{{ doc.name }}" style="background-color: #1a5276; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Voir la demande</a>
    <br><br>
    <div style="font-size: 11px; color: #7f8c8d; text-align: center; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;">
        <strong>KYA-Energy Group</strong> | LOMÉ - TOGO | Tél. : +228 70 45 34 81
    </div>
</div>
            """
        })
        doc.insert(ignore_permissions=True)
        print("Created Email Template: KYA Purchase Request Alert")

    # Configuring the Notification Trigger based on Workflow State
    if not frappe.db.exists("Notification", "Alerte Demande Achat KYA"):
        doc = frappe.get_doc({
            "doctype": "Notification",
            "name": "Alerte Demande Achat KYA",
            "subject": "Nouvelle Action Requise : Demande d'Achat N° {{ doc.name }}",
            "document_type": "KYA Purchase Request",
            "event": "Value Change",
            "value_changed": "workflow_state",
            "condition": "doc.workflow_state != 'Brouillon'",
            "send_to_all_assignees": 1,
            "is_standard": 1,
            "module": "KYA HR",
            "channel": "Email",
            "message": frappe.db.get_value("Email Template", "KYA Purchase Request Alert", "response")
        })
        doc.insert(ignore_permissions=True)
        print("Created Notification: Alerte Demande Achat KYA")

    frappe.db.commit()
    print("✅ Email templates and notifications configured.")

if __name__ == "__main__":
    create_email_alerts()

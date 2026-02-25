import frappe

def execute():
    # 1. Notification for Permission Request
    create_permission_notifications()
    
    # 2. Notification for Exit Ticket
    create_exit_ticket_notifications()

    frappe.db.commit()
    print("✅ Notifications for KYA Extensions created successfully!")

def create_permission_notifications():
    notif_name = "Notification Permission Stagiaire"
    if not frappe.db.exists("Notification", notif_name):
        frappe.get_doc({
            "doctype": "Notification",
            "name": notif_name,
            "subject": "Demande de Permission : {{ doc.employee_name }}",
            "document_type": "KYA Permission Request",
            "event": "Value Change",
            "value_changed": "workflow_state",
            "send_to_all_assignees": 1,
            "message": """
<p>Bonjour,</p>
<p>Une demande de permission a été déposée par <b>{{ doc.employee_name }}</b>.</p>
<p><b>Type :</b> {{ doc.permission_type }}<br>
<b>Période :</b> du {{ doc.from_date }} au {{ doc.to_date }}<br>
<b>Raison :</b> {{ doc.reason }}</p>
<p>Statut actuel : <b>{{ doc.workflow_state }}</b></p>
<p>Merci de vous connecter pour traiter cette demande.</p>
<hr>
<p><i>Ceci est un message automatique de Digital KYA.</i></p>
""",
            "enabled": 1
        }).insert()
        print(f"Notification {notif_name} created")

def create_exit_ticket_notifications():
    notif_name = "Notification Ticket de Sortie"
    if not frappe.db.exists("Notification", notif_name):
        frappe.get_doc({
            "doctype": "Notification",
            "name": notif_name,
            "subject": "Nouveau Ticket de Sortie : {{ doc.name }}",
            "document_type": "KYA Exit Ticket",
            "event": "Value Change",
            "value_changed": "workflow_state",
            "send_to_all_assignees": 1,
            "message": """
<p>Bonjour,</p>
<p>Un ticket de sortie a été créé par <b>{{ doc.employee }}</b>.</p>
<p><b>Véhicule :</b> {{ doc.vehicle }}<br>
<b>Destination :</b> {{ doc.destination }}<br>
<b>Motif :</b> {{ doc.reason }}</p>
<p>Niveau d'approbation : <b>{{ doc.workflow_state }}</b></p>
<p>Merci de valider ou rejeter cette sortie via le système.</p>
<hr>
<p><i>Ceci est un message automatique de Digital KYA.</i></p>
""",
            "enabled": 1
        }).insert()
        print(f"Notification {notif_name} created")

if __name__ == "__main__":
    execute()

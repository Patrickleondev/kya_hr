import json

LOGO = "{{ frappe.utils.get_url() }}/assets/kya_hr/images/kya_logo.png"

with open("kya_hr/fixtures/notification.json", encoding="utf-8") as f:
    notifs = json.load(f)

existing = [n["name"] for n in notifs]

new_notifs = [
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: En attente Maitre de Stage",
        "subject": "Demande de conge de {{ doc.employee_name }} a approuver",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente Maitre de Stage'",
        "channel": "Email",
        "recipients": [{"receiver_by_document_field": "report_to"}],
        "message": (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#009688,#00bcd4);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            "<img src='" + LOGO + "' width='60' style='margin-bottom:8px;'>"
            "<h2 style='color:white;margin:0;'>Demande de Congé Stagiaire</h2></div>"
            "<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            "<p>Bonjour,</p><p>Le/la stagiaire <b>{{ doc.employee_name }}</b> a soumis une demande de congé :</p>"
            "<table style='width:100%;border-collapse:collapse;margin:14px 0;'>"
            "<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;width:40%;'>Type</td><td style='padding:6px 10px;'>{{ doc.type_conge }}</td></tr>"
            "<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Du</td><td style='padding:6px 10px;'>{{ doc.date_debut }}</td></tr>"
            "<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Au</td><td style='padding:6px 10px;'>{{ doc.date_fin }}</td></tr>"
            "<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Nombre de jours</td><td style='padding:6px 10px;'>{{ doc.nombre_jours }}</td></tr>"
            "<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Motif</td><td style='padding:6px 10px;'>{{ doc.motif }}</td></tr>"
            "</table>"
            "<div style='text-align:center;margin:20px 0;'>"
            "<a href='{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}' style='display:inline-block;padding:12px 32px;background:#009688;color:white;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;'>Approuver / Rejeter</a>"
            "</div></div>{{ get_kya_email_footer() }}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: En attente Resp. Stagiaires",
        "subject": "Demande de conge {{ doc.employee_name }} - Validation Responsable Stagiaires",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente Resp. Stagiaires'",
        "channel": "Email",
        "recipients": [{"receiver_by_role": "Responsable des Stagiaires"}],
        "message": (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#009688,#00bcd4);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            "<img src='" + LOGO + "' width='60' style='margin-bottom:8px;'>"
            "<h2 style='color:white;margin:0;'>Validation Responsable Stagiaires</h2></div>"
            "<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            "<p>Bonjour,</p><p>La demande de congé du stagiaire <b>{{ doc.employee_name }}</b> "
            "({{ doc.nombre_jours }} jours - {{ doc.type_conge }}) a été validée par le Maître de Stage et nécessite votre approbation.</p>"
            "<div style='text-align:center;margin:20px 0;'>"
            "<a href='{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}' style='display:inline-block;padding:12px 32px;background:#009688;color:white;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;'>Examiner la demande</a>"
            "</div></div>{{ get_kya_email_footer() }}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: En attente DG",
        "subject": "Demande de conge {{ doc.employee_name }} - Approbation DG",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente DG'",
        "channel": "Email",
        "recipients": [{"receiver_by_role": "Directeur General"}],
        "message": (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#009688,#00bcd4);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            "<img src='" + LOGO + "' width='60' style='margin-bottom:8px;'>"
            "<h2 style='color:white;margin:0;'>Approbation DG Requise</h2></div>"
            "<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            "<p>Bonjour Monsieur le Directeur Général,</p>"
            "<p>La demande de congé du stagiaire <b>{{ doc.employee_name }}</b> ({{ doc.nombre_jours }} jours) est en attente de votre approbation finale.</p>"
            "<div style='text-align:center;margin:20px 0;'>"
            "<a href='{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}' style='display:inline-block;padding:12px 32px;background:#009688;color:white;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;'>Approuver / Rejeter</a>"
            "</div></div>{{ get_kya_email_footer() }}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: Approuvee",
        "subject": "Votre demande de conge est approuvee",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'Approuve'",
        "channel": "Email",
        "recipients": [{"receiver_by_document_field": "employee"}],
        "message": (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#2e7d32,#4caf50);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            "<img src='" + LOGO + "' width='60' style='margin-bottom:8px;'>"
            "<h2 style='color:white;margin:0;'>✅ Congé Approuvé</h2></div>"
            "<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            "<p>Bonjour <b>{{ doc.employee_name }}</b>,</p>"
            "<p>Votre demande de congé du <b>{{ doc.date_debut }}</b> au <b>{{ doc.date_fin }}</b> "
            "({{ doc.nombre_jours }} jours) a été <b style='color:#2e7d32;'>approuvée</b>.</p>"
            "<div style='text-align:center;margin:20px 0;'>"
            "<a href='{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}' style='display:inline-block;padding:12px 32px;background:#2e7d32;color:white;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;'>Voir ma demande</a>"
            "</div></div>{{ get_kya_email_footer() }}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: Rejetee",
        "subject": "Demande de conge rejetee",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'Rejete'",
        "channel": "Email",
        "recipients": [{"receiver_by_document_field": "employee"}],
        "message": (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#c62828,#e53935);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            "<img src='" + LOGO + "' width='60' style='margin-bottom:8px;'>"
            "<h2 style='color:white;margin:0;'>❌ Demande Rejetée</h2></div>"
            "<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            "<p>Bonjour <b>{{ doc.employee_name }}</b>,</p>"
            "<p>Votre demande de congé du <b>{{ doc.date_debut }}</b> au <b>{{ doc.date_fin }}</b> a été <b style='color:#c62828;'>rejetée</b>.</p>"
            "<p>Veuillez contacter votre responsable pour plus d'informations.</p>"
            "<div style='text-align:center;margin:20px 0;'>"
            "<a href='{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}' style='display:inline-block;padding:12px 32px;background:#666;color:white;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;'>Voir les détails</a>"
            "</div></div>{{ get_kya_email_footer() }}</div>"
        ),
        "enabled": 1
    }
]

added = 0
for n in new_notifs:
    if n["name"] not in existing:
        notifs.append(n)
        added += 1
        print("Added:", n["name"])

with open("kya_hr/fixtures/notification.json", "w", encoding="utf-8") as f:
    json.dump(notifs, f, ensure_ascii=False, indent=1)

print(f"Done. Added {added} notifications.")

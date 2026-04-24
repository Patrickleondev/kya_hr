"""Re-applique toutes les corrections perdues après le reset."""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
NOTIF_FILE = os.path.join(BASE, "kya_hr", "fixtures", "notification.json")
WF_FILE = os.path.join(BASE, "kya_hr", "fixtures", "workflow.json")

LOGO = "{{ frappe.utils.get_url() }}/assets/kya_hr/images/kya_logo.png"
OLD_LOGO = "https://www.kya-energy.com/wp-content/uploads/2024/02/Logo-10-ans-KYA.png"

# ──────────────────────────────────────────────
# 1. FIX NOTIFICATIONS: recipients + logo
# ──────────────────────────────────────────────
with open(NOTIF_FILE, encoding="utf-8") as f:
    notifs = json.load(f)

RECIPIENT_FIXES = {
    # Permission Stagiaire
    "KYA - Permission Stagiaire: En attente Chef":         {"receiver_by_document_field": "report_to"},
    "KYA - Permission Stagiaire: En attente Resp. Stagiaires": {"receiver_by_role": "Responsable des Stagiaires"},
    "KYA - Permission Stagiaire: En attente DG":           {"receiver_by_role": "Directeur General"},
    # Permission Employé
    "KYA - Permission Employé: En attente Chef":           {"receiver_by_document_field": "report_to"},
    "KYA - Permission Employé: En attente RH":             {"receiver_by_role": "Responsable RH"},
    "KYA - Permission Employé: En attente DGA":            {"receiver_by_role": "Directeur General"},
    # PV Matériel
    "KYA - PV Matériel: En attente Magasin":               {"receiver_by_role": "Chargé des Stocks"},
    "KYA - PV Matériel: En attente Audit":                 {"receiver_by_role": "Auditeur Interne"},
    "KYA - PV Matériel: En attente Direction":             {"receiver_by_role": "Directeur General"},
    # Planning Congé
    "KYA - Planning Congé: En attente RH":                 {"receiver_by_role": "Responsable RH"},
    "KYA - Planning Congé: En attente DG":                 {"receiver_by_role": "Directeur General"},
    # Demande Achat
    "KYA - Demande Achat: En attente DAAF":                {"receiver_by_role": "DAAF"},
    "KYA - Demande Achat: En attente DG":                  {"receiver_by_role": "Directeur General"},
}

fixed_recipients = 0
fixed_logos = 0

for n in notifs:
    name = n.get("name", "")
    # Fix recipients
    if name in RECIPIENT_FIXES:
        n["recipients"] = [RECIPIENT_FIXES[name]]
        fixed_recipients += 1
        print(f"  Fixed recipients: {name}")
    # Fix logo in message
    msg = n.get("message", "")
    if OLD_LOGO in msg:
        n["message"] = msg.replace(OLD_LOGO, LOGO)
        fixed_logos += 1
        print(f"  Fixed logo: {name}")

print(f"\nFixed {fixed_recipients} recipients, {fixed_logos} logos.")

# ──────────────────────────────────────────────
# 2. ADD 5 NOTIFICATIONS: Demande Congé Stagiaire
# ──────────────────────────────────────────────
existing = {n["name"] for n in notifs}

conge_notifs = [
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: En attente Maitre de Stage",
        "subject": "Demande de congé de {{ doc.employee_name }} à approuver",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change", "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente Maitre de Stage'",
        "channel": "Email",
        "recipients": [{"receiver_by_document_field": "report_to"}],
        "message": (
            f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            f"<div style='background:linear-gradient(135deg,#009688,#00bcd4);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            f"<img src='{LOGO}' width='60' style='margin-bottom:8px;'>"
            f"<h2 style='color:white;margin:0;'>Demande de Congé Stagiaire</h2></div>"
            f"<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            f"<p>Bonjour,</p><p>Le/la stagiaire <b>{{{{ doc.employee_name }}}}</b> a soumis une demande de congé :</p>"
            f"<table style='width:100%;border-collapse:collapse;margin:14px 0;'>"
            f"<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;width:40%;'>Type</td><td style='padding:6px 10px;'>{{{{ doc.type_conge }}}}</td></tr>"
            f"<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Du</td><td style='padding:6px 10px;'>{{{{ doc.date_debut }}}}</td></tr>"
            f"<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Au</td><td style='padding:6px 10px;'>{{{{ doc.date_fin }}}}</td></tr>"
            f"<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Jours</td><td style='padding:6px 10px;'>{{{{ doc.nombre_jours }}}}</td></tr>"
            f"<tr><td style='padding:6px 10px;background:#f5f5f5;font-weight:700;'>Motif</td><td style='padding:6px 10px;'>{{{{ doc.motif }}}}</td></tr>"
            f"</table>"
            f"<div style='text-align:center;margin:20px 0;'>"
            f"<a href='{{{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}}}' style='display:inline-block;padding:12px 32px;background:#009688;color:white;text-decoration:none;border-radius:8px;font-weight:700;'>Approuver / Rejeter</a>"
            f"</div></div>{{{{ get_kya_email_footer() }}}}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: En attente Resp. Stagiaires",
        "subject": "Demande de congé {{ doc.employee_name }} - Validation Responsable Stagiaires",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change", "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente Resp. Stagiaires'",
        "channel": "Email",
        "recipients": [{"receiver_by_role": "Responsable des Stagiaires"}],
        "message": (
            f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            f"<div style='background:linear-gradient(135deg,#009688,#00bcd4);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            f"<img src='{LOGO}' width='60' style='margin-bottom:8px;'>"
            f"<h2 style='color:white;margin:0;'>Validation Responsable Stagiaires</h2></div>"
            f"<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            f"<p>La demande de congé du stagiaire <b>{{{{ doc.employee_name }}}}</b> "
            f"({{{{ doc.nombre_jours }}}} jours - {{{{ doc.type_conge }}}}) a été validée par le Maître de Stage.</p>"
            f"<div style='text-align:center;margin:20px 0;'>"
            f"<a href='{{{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}}}' style='display:inline-block;padding:12px 32px;background:#009688;color:white;text-decoration:none;border-radius:8px;font-weight:700;'>Examiner la demande</a>"
            f"</div></div>{{{{ get_kya_email_footer() }}}}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: En attente DG",
        "subject": "Demande de congé {{ doc.employee_name }} - Approbation DG",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change", "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente DG'",
        "channel": "Email",
        "recipients": [{"receiver_by_role": "Directeur General"}],
        "message": (
            f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            f"<div style='background:linear-gradient(135deg,#009688,#00bcd4);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            f"<img src='{LOGO}' width='60' style='margin-bottom:8px;'>"
            f"<h2 style='color:white;margin:0;'>Approbation DG Requise</h2></div>"
            f"<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            f"<p>Bonjour Monsieur le Directeur Général,</p>"
            f"<p>La demande de congé du stagiaire <b>{{{{ doc.employee_name }}}}</b> ({{{{ doc.nombre_jours }}}} jours) est en attente de votre approbation finale.</p>"
            f"<div style='text-align:center;margin:20px 0;'>"
            f"<a href='{{{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}}}' style='display:inline-block;padding:12px 32px;background:#009688;color:white;text-decoration:none;border-radius:8px;font-weight:700;'>Approuver / Rejeter</a>"
            f"</div></div>{{{{ get_kya_email_footer() }}}}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: Approuvee",
        "subject": "Votre demande de congé est approuvée",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change", "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'Approuve'",
        "channel": "Email",
        "recipients": [{"receiver_by_document_field": "employee"}],
        "message": (
            f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            f"<div style='background:linear-gradient(135deg,#2e7d32,#4caf50);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            f"<img src='{LOGO}' width='60' style='margin-bottom:8px;'>"
            f"<h2 style='color:white;margin:0;'>Congé Approuvé ✓</h2></div>"
            f"<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            f"<p>Bonjour <b>{{{{ doc.employee_name }}}}</b>,</p>"
            f"<p>Votre demande de congé du <b>{{{{ doc.date_debut }}}}</b> au <b>{{{{ doc.date_fin }}}}</b> "
            f"({{{{ doc.nombre_jours }}}} jours) a été <b style='color:#2e7d32;'>approuvée</b>.</p>"
            f"<div style='text-align:center;margin:20px 0;'>"
            f"<a href='{{{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}}}' style='display:inline-block;padding:12px 32px;background:#2e7d32;color:white;text-decoration:none;border-radius:8px;font-weight:700;'>Voir ma demande</a>"
            f"</div></div>{{{{ get_kya_email_footer() }}}}</div>"
        ),
        "enabled": 1
    },
    {
        "doctype": "Notification",
        "name": "KYA - Demande Conge Stagiaire: Rejetee",
        "subject": "Demande de congé rejetée",
        "document_type": "Demande Conge Stagiaire",
        "event": "Value Change", "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'Rejete'",
        "channel": "Email",
        "recipients": [{"receiver_by_document_field": "employee"}],
        "message": (
            f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            f"<div style='background:linear-gradient(135deg,#c62828,#e53935);padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            f"<img src='{LOGO}' width='60' style='margin-bottom:8px;'>"
            f"<h2 style='color:white;margin:0;'>Demande Rejetée</h2></div>"
            f"<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
            f"<p>Bonjour <b>{{{{ doc.employee_name }}}}</b>,</p>"
            f"<p>Votre demande de congé du <b>{{{{ doc.date_debut }}}}</b> au <b>{{{{ doc.date_fin }}}}</b> a été <b style='color:#c62828;'>rejetée</b>.</p>"
            f"<p>Veuillez contacter votre responsable pour plus d'informations.</p>"
            f"<div style='text-align:center;margin:20px 0;'>"
            f"<a href='{{{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}}}' style='display:inline-block;padding:12px 32px;background:#666;color:white;text-decoration:none;border-radius:8px;font-weight:700;'>Voir les détails</a>"
            f"</div></div>{{{{ get_kya_email_footer() }}}}</div>"
        ),
        "enabled": 1
    },
]

added = 0
for n in conge_notifs:
    if n["name"] not in existing:
        notifs.append(n)
        added += 1
        print(f"  Added: {n['name']}")

with open(NOTIF_FILE, "w", encoding="utf-8") as f:
    json.dump(notifs, f, ensure_ascii=False, indent=1)
print(f"Added {added} Congé Stagiaire notifications.\n")

# ──────────────────────────────────────────────
# 3. ADD WORKFLOW: Demande Congé Stagiaire
# ──────────────────────────────────────────────
with open(WF_FILE, encoding="utf-8") as f:
    wfs = json.load(f)

if "Flux Demande Conge Stagiaire" not in [w["name"] for w in wfs]:
    wfs.append({
        "docstatus": 0, "doctype": "Workflow",
        "document_type": "Demande Conge Stagiaire",
        "enable_action_confirmation": 0, "is_active": 1,
        "modified": "2026-04-22 12:00:00",
        "name": "Flux Demande Conge Stagiaire",
        "override_status": 0, "send_email_alert": 1,
        "states": [
            {"allow_edit": "Stagiaire", "doc_status": "0", "state": "Brouillon", "send_email": 0},
            {"allow_edit": "Maitre de Stage", "doc_status": "0", "state": "En attente Maitre de Stage", "send_email": 1},
            {"allow_edit": "Responsable des Stagiaires", "doc_status": "0", "state": "En attente Resp. Stagiaires", "send_email": 1},
            {"allow_edit": "Directeur General", "doc_status": "0", "state": "En attente DG", "send_email": 1},
            {"allow_edit": "Responsable des Stagiaires", "doc_status": "1", "state": "Approuve", "send_email": 1},
            {"allow_edit": "Responsable des Stagiaires", "doc_status": "2", "state": "Rejete", "send_email": 1},
        ],
        "transitions": [
            {"action": "Soumettre", "allowed": "Stagiaire", "next_state": "En attente Maitre de Stage", "state": "Brouillon"},
            {"action": "Approuver", "allowed": "Maitre de Stage", "next_state": "En attente Resp. Stagiaires", "state": "En attente Maitre de Stage"},
            {"action": "Rejeter", "allowed": "Maitre de Stage", "next_state": "Rejete", "state": "En attente Maitre de Stage"},
            {"action": "Approuver", "allowed": "Responsable des Stagiaires", "next_state": "En attente DG", "state": "En attente Resp. Stagiaires"},
            {"action": "Rejeter", "allowed": "Responsable des Stagiaires", "next_state": "Rejete", "state": "En attente Resp. Stagiaires"},
            {"action": "Approuver", "allowed": "Directeur General", "next_state": "Approuve", "state": "En attente DG"},
            {"action": "Rejeter", "allowed": "Directeur General", "next_state": "Rejete", "state": "En attente DG"},
        ],
    })
    with open(WF_FILE, "w", encoding="utf-8") as f:
        json.dump(wfs, f, ensure_ascii=False, indent=1)
    print("Workflow 'Flux Demande Conge Stagiaire' added.")
else:
    print("Workflow already exists.")

print("\nAll done.")

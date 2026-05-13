"""Patch notification.json — adds missing notifications for new workflow states."""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "fixtures", "notification.json")

with open(PATH, encoding="utf-8") as f:
    notifs = json.load(f)

existing_names = {n["name"] for n in notifs}

SITE_URL = "{{ frappe.utils.get_url() }}"
LOGO = f"{SITE_URL}/assets/kya_hr/images/kya_logo.png"
FOOTER = "{{ get_kya_email_footer() }}"

def btn(url, label, color="#009688"):
    return (f"<div style='text-align:center;margin:20px 0;'>"
            f"<a href='{url}' style='display:inline-block;padding:12px 32px;"
            f"background:{color};color:white;text-decoration:none;border-radius:8px;"
            f"font-weight:700;font-size:15px;'>{label}</a></div>")

def header(title, bg="#009688"):
    return (f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            f"<div style='background:{bg};padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
            f"<img src='{LOGO}' width='60' style='margin-bottom:8px;'>"
            f"<h2 style='color:white;margin:0;'>{title}</h2></div>"
            f"<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>")

body_end = f"</div>{FOOTER}</div>"

NEW_NOTIFS = [
    # ── PV Entree: En attente Comptable ──────────────────────────────────────
    {
        "name": "KYA - PV Entrée Matériel: En attente Comptable",
        "doctype": "Notification", "is_standard": 0, "enabled": 1,
        "document_type": "PV Entree Materiel", "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente Comptable'",
        "channel": "Email", "message_type": "Jinja",
        "subject": "PV Réception {{ doc.name }} — Validation comptabilité requise",
        "recipients": [{"receiver_by_role": "Responsable Comptable"}],
        "message": (
            header("PV Réception de Matériels", "#1565c0") +
            "<p>Bonjour,</p>"
            "<p>Le PV de réception <b>{{ doc.name }}</b> a été validé par le magasin et nécessite maintenant votre validation comptable.</p>"
            "<p><b>Objet :</b> {{ doc.objet }}<br>"
            "<b>Fournisseur :</b> {{ doc.fournisseur or doc.fournisseur_libre or '—' }}<br>"
            "<b>Projet :</b> {{ doc.project or '—' }}</p>" +
            btn(f"{SITE_URL}/pv-entree-materiel/{{{{ doc.name }}}}", "Valider Comptabilité", "#1565c0") +
            body_end
        ),
        "modified": "2026-05-13 00:00:00.000000",
    },
    # ── PV Entree: En attente Audit ──────────────────────────────────────────
    {
        "name": "KYA - PV Entrée Matériel: En attente Audit",
        "doctype": "Notification", "is_standard": 0, "enabled": 1,
        "document_type": "PV Entree Materiel", "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente Audit'",
        "channel": "Email", "message_type": "Jinja",
        "subject": "PV Réception {{ doc.name }} — Validation audit interne",
        "recipients": [{"receiver_by_role": "Auditeur Interne"}],
        "message": (
            header("PV Réception de Matériels", "#4a148c") +
            "<p>Bonjour,</p>"
            "<p>Le PV de réception <b>{{ doc.name }}</b> a été validé par la comptabilité et est en attente de votre approbation audit.</p>"
            "<p><b>Objet :</b> {{ doc.objet }}<br>"
            "<b>Fournisseur :</b> {{ doc.fournisseur or doc.fournisseur_libre or '—' }}<br>"
            "<b>Projet :</b> {{ doc.project or '—' }}</p>" +
            btn(f"{SITE_URL}/pv-entree-materiel/{{{{ doc.name }}}}", "Approuver (Audit)", "#4a148c") +
            body_end
        ),
        "modified": "2026-05-13 00:00:00.000000",
    },
    # ── PV Entree: Approuvé ──────────────────────────────────────────────────
    # Already exists in notification.json — skip
    # ── Retour Matériel: En attente Magasin ──────────────────────────────────
    {
        "name": "KYA - Retour Matériel: En attente Magasin",
        "doctype": "Notification", "is_standard": 0, "enabled": 1,
        "document_type": "Retour Materiel KYA", "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'En attente Magasin'",
        "channel": "Email", "message_type": "Jinja",
        "subject": "Retour Matériel {{ doc.name }} — Réception magasin requise",
        "recipients": [{"receiver_by_role": "Chargé des Stocks"}],
        "message": (
            header("Retour de Matériel au Magasin", "#e65100") +
            "<p>Bonjour,</p>"
            "<p>Un retour de matériel <b>{{ doc.name }}</b> a été déclaré et nécessite votre confirmation de réception.</p>"
            "<p><b>Motif :</b> {{ doc.objet }}<br>"
            "<b>Projet :</b> {{ doc.project or '—' }}<br>"
            "<b>Client :</b> {{ doc.customer or doc.customer_libre or '—' }}<br>"
            "<b>PV Sortie origine :</b> {{ doc.pv_sortie_origine or '—' }}</p>" +
            btn(f"{SITE_URL}/retour-materiel/{{{{ doc.name }}}}", "Réceptionner le Retour", "#e65100") +
            body_end
        ),
        "modified": "2026-05-13 00:00:00.000000",
    },
    # ── Retour Matériel: Approuvé ─────────────────────────────────────────────
    {
        "name": "KYA - Retour Matériel: Approuvé",
        "doctype": "Notification", "is_standard": 0, "enabled": 1,
        "document_type": "Retour Materiel KYA", "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'Approuvé'",
        "channel": "Email", "message_type": "Jinja",
        "subject": "Retour Matériel {{ doc.name }} — Retour réceptionné, stock mis à jour",
        "recipients": [{"receiver_by_document_field": "owner"}],
        "message": (
            header("Retour de Matériel — Approuvé", "#2e7d32") +
            "<p>Bonjour,</p>"
            "<p>Le retour de matériel <b>{{ doc.name }}</b> a été réceptionné par le magasin. Les articles ont été remis en stock automatiquement.</p>"
            "<p><b>Motif :</b> {{ doc.objet }}<br>"
            "<b>Stock Entry généré :</b> {{ doc.stock_entry or 'En cours...' }}</p>" +
            btn(f"{SITE_URL}/retour-materiel/{{{{ doc.name }}}}", "Voir le PV de Retour", "#2e7d32") +
            body_end
        ),
        "modified": "2026-05-13 00:00:00.000000",
    },
    # ── Retour Matériel: Rejeté ───────────────────────────────────────────────
    {
        "name": "KYA - Retour Matériel: Rejeté",
        "doctype": "Notification", "is_standard": 0, "enabled": 1,
        "document_type": "Retour Materiel KYA", "event": "Value Change",
        "value_changed": "workflow_state",
        "condition": "doc.workflow_state == 'Rejeté'",
        "channel": "Email", "message_type": "Jinja",
        "subject": "Retour Matériel {{ doc.name }} — Rejeté par le magasin",
        "recipients": [{"receiver_by_document_field": "owner"}],
        "message": (
            header("Retour de Matériel — Rejeté", "#c62828") +
            "<p>Bonjour,</p>"
            "<p>Le retour de matériel <b>{{ doc.name }}</b> a été rejeté par le responsable magasin.</p>"
            "<p><b>Motif déclaré :</b> {{ doc.objet }}<br>"
            "<b>Veuillez contacter le responsable magasin pour plus d'informations.</b></p>" +
            btn(f"{SITE_URL}/retour-materiel/{{{{ doc.name }}}}", "Voir le PV de Retour", "#c62828") +
            body_end
        ),
        "modified": "2026-05-13 00:00:00.000000",
    },
]

added = 0
for n in NEW_NOTIFS:
    if n["name"] not in existing_names:
        notifs.append(n)
        added += 1
        print(f"  + {n['name']}")
    else:
        print(f"  = {n['name']} (already exists)")

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(notifs, f, ensure_ascii=False, indent=1)
print(f"\nAdded {added} notifications. Total: {len(notifs)}")

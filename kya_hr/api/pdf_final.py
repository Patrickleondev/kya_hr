"""PDF final signé : à la clôture d'un circuit (dernier visa), le document
officiel est généré, attaché à la pièce et envoyé par mail au créateur.

Retour terrain (compta) : « il faut qu'ils puissent télécharger le PDF à la
fin de l'accord du DFC, la version finale » — avant ce module, rien n'était
attaché et le caissier ne recevait aucun mail de clôture.

Branché via hooks.py doc_events -> on_change des doctypes de flux (fonctionne
aussi pour les doctypes custom=1 qui n'ont pas de classe Python).
"""
from __future__ import annotations

import frappe
from frappe.utils.pdf import get_pdf

from kya_hr.ensure_webform_print_formats import DOCTYPE_DEFAULT_PRINT_FORMATS

# Doctype -> état(s) de fin de circuit (dernier visa posé).
FINAL_STATES = {
    "Brouillard Caisse": {"Approuvé"},
    "Etat Recap Cheques": {"Validé DFC"},
    "Demande Achat KYA": {"Approuvé"},
    "Bon Commande KYA": {"Émis"},
    "PV Sortie Materiel": {"Approuvé"},
    "PV Entree Materiel": {"Approuvé"},
    "Retour Materiel KYA": {"Approuvé"},
    "Inventaire KYA": {"Approuvé"},
}

# Doctype -> route portail (page web form) pour le bouton du mail.
PORTAL_ROUTES = {
    "Brouillard Caisse": "brouillard-caisse",
    "Etat Recap Cheques": "etat-recap",
    "Demande Achat KYA": "demande-achat",
    "Bon Commande KYA": "bon-commande",
    "PV Sortie Materiel": "pv-sortie-materiel",
    "PV Entree Materiel": "pv-entree-materiel",
    "Retour Materiel KYA": "retour-materiel",
    "Inventaire KYA": "inventaire-kya",
}

# Doctypes dont le mail de clôture est envoyé ICI (les autres circuits ont déjà
# une Notification « Approuvé » -> créateur avec attach_print du format officiel).
CLOSURE_MAIL_DOCTYPES = {"Brouillard Caisse", "Etat Recap Cheques", "Bon Commande KYA"}

LABELS = {
    "Brouillard Caisse": "Brouillard de caisse",
    "Etat Recap Cheques": "État récapitulatif des chèques",
    "Demande Achat KYA": "Demande d'achat",
    "Bon Commande KYA": "Bon de commande",
    "PV Sortie Materiel": "PV de sortie de matériel",
    "PV Entree Materiel": "PV d'entrée de matériel",
    "Retour Materiel KYA": "Retour de matériel",
    "Inventaire KYA": "Inventaire",
}


def _pdf_filename(doc) -> str:
    return f"{doc.name.replace(' ', '-').replace('/', '-')}-signe.pdf"


def _already_attached(doc) -> bool:
    return bool(frappe.db.exists("File", {
        "attached_to_doctype": doc.doctype,
        "attached_to_name": doc.name,
        "file_name": _pdf_filename(doc),
    }))


def _render_official_pdf(doc) -> bytes | None:
    pf = DOCTYPE_DEFAULT_PRINT_FORMATS.get(doc.doctype)
    if not pf or not frappe.db.exists("Print Format", pf):
        return None
    html = frappe.get_print(doc.doctype, doc.name, pf, doc=doc)
    # même nettoyage que le téléchargement PDF (conteneur sans accès http)
    from kya_hr.api.print_format import _sanitize_print_html
    return get_pdf(_sanitize_print_html(html))


def _closure_email(doc, fname: str):
    """Mail de clôture (vert) au créateur, PDF final en pièce jointe."""
    owner_email = frappe.db.get_value("User", doc.owner, "email")
    if not owner_email or doc.owner in ("Administrator", "Guest"):
        return
    base = frappe.utils.get_url()
    route = PORTAL_ROUTES.get(doc.doctype, "")
    label = LABELS.get(doc.doctype, doc.doctype)
    link = f"{base}/{route}/{doc.name}" if route else f"{base}/app/{frappe.scrub(doc.doctype).replace('_', '-')}/{doc.name}"
    message = (
        "<div style='font-family:Arial,sans-serif;max-width:560px;margin:0 auto;'>"
        "<div style='background:linear-gradient(135deg,#2e7d32,#66bb6a);padding:24px;"
        "border-radius:12px 12px 0 0;text-align:center;'>"
        f"<img src='{base}/assets/kya_hr/images/kya_logo.png' width='60' style='margin-bottom:8px;'>"
        "<h2 style='color:white;margin:0;'>✅ Circuit terminé</h2>"
        f"<p style='color:white;margin:6px 0 0;font-size:14px;'>{label} {doc.name}</p>"
        "</div>"
        "<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
        "<p>Bonjour,</p>"
        f"<p>Votre <b>{label.lower()}</b> <b>{doc.name}</b> a reçu toutes les signatures "
        f"et est maintenant <b style='color:#2e7d32;'>{doc.get('workflow_state')}</b>.</p>"
        "<p>La <b>version finale signée (PDF)</b> est jointe à ce message et reste "
        "téléchargeable depuis le document.</p>"
        "<div style='text-align:center;margin:24px 0;'>"
        f"<a href='{link}' style='display:inline-block;padding:13px 30px;background:#009688;"
        "color:white;text-decoration:none;border-radius:8px;font-weight:700;'>"
        "📄 Consulter le document</a>"
        "</div>"
        "</div></div>"
    )
    frappe.sendmail(
        recipients=[owner_email],
        subject=f"✅ {label} {doc.name} — version finale signée",
        message=message,
        attachments=[{"fname": fname, "fcontent": doc._kya_final_pdf}],
        reference_doctype=doc.doctype,
        reference_name=doc.name,
        # envoi via la file (scheduler) : un envoi immédiat se déclenche APRÈS le
        # commit, hors de tout try/except -> un SMTP indisponible ferait un 500
        # sur le clic d'approbation du DFC (constaté en local sans SMTP).
    )


def attach_final_pdf(doc, method=None):
    """doc_events.on_change : à l'arrivée dans l'état final, attache le PDF
    officiel signé et prévient le créateur. Idempotent, jamais bloquant."""
    try:
        if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch:
            return
        if doc.docstatus == 2:  # annulé : workflow_state peut être resté à l'état final,
            return              # mais frappe.get_print refuse d'imprimer un doc annulé.
        states = FINAL_STATES.get(doc.doctype)
        if not states or (doc.get("workflow_state") or "") not in states:
            return
        if _already_attached(doc):
            return
        pdf = _render_official_pdf(doc)
        if not pdf:
            return
        fname = _pdf_filename(doc)
        frappe.get_doc({
            "doctype": "File",
            "file_name": fname,
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "is_private": 1,
            "content": pdf,
        }).insert(ignore_permissions=True)
        doc._kya_final_pdf = pdf
        try:
            _closure_email(doc, fname)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"pdf_final mail: {doc.name}")
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"pdf_final: {getattr(doc, 'name', '?')}")

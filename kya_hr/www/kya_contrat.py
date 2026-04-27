"""Portail web /kya-contrat?name=XXX&token=YYY (accès via token, pas de login)."""
import frappe
import json
import re
from frappe import _


no_cache = 1
allow_guest = True


def _split_sections(html):
    """Découpe le HTML rendu en sections délimitées par <h1>, <h2>, <h3>.
    Retourne une liste [{id, title, html}, ...]."""
    if not html:
        return []
    parts = re.split(r"(?=<h[1-3][\s>])", html, flags=re.IGNORECASE)
    sections = []
    preamble = []
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            continue
        m = re.match(r"<h([1-3])[^>]*>(.*?)</h\1>", p, flags=re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip() or f"Section {len(sections)+1}"
            sec_id = f"sec-{len(sections)+1}"
            sections.append({"id": sec_id, "title": title, "html": p})
        else:
            preamble.append(p)
    if preamble:
        sections.insert(0, {"id": "sec-0", "title": "Préambule", "html": "\n".join(preamble)})
    if not sections:
        sections.append({"id": "sec-1", "title": "Contrat", "html": html})
    return sections


def get_context(context):
    contract_id = frappe.form_dict.get("name") or frappe.form_dict.get("id")
    token = frappe.form_dict.get("token")

    if not contract_id or not token:
        context.error_msg = "Lien invalide. Veuillez utiliser le lien reçu par email."
        context.is_error = True
        context.title = "Lien invalide"
        return context

    if not frappe.db.exists("KYA Contrat", contract_id):
        context.error_msg = "Contrat introuvable."
        context.is_error = True
        context.title = "Contrat introuvable"
        return context

    doc = frappe.get_doc("KYA Contrat", contract_id)

    # Validation token
    role = None
    if doc.access_token_signataire and token == doc.access_token_signataire:
        role = "employe"
    elif doc.access_token_dg and token == doc.access_token_dg:
        role = "dg"
    else:
        context.error_msg = "Lien invalide ou expiré. Contactez la RH si le problème persiste."
        context.is_error = True
        context.title = "Accès refusé"
        return context

    # Render template Jinja
    contrat_dict = doc.as_dict(convert_dates_to_str=False)
    rendered_body = ""
    if doc.template:
        try:
            tpl = frappe.get_doc("KYA Contract Template", doc.template)
            if tpl.html_body:
                rendered_body = frappe.render_template(
                    tpl.html_body,
                    {"doc": contrat_dict, "frappe": frappe}
                )
        except Exception as e:
            rendered_body = f"<p style='color:red'>Erreur rendu template : {frappe.utils.escape_html(str(e))}</p>"

    sections = _split_sections(rendered_body)

    # Sections déjà signées
    sigs = json.loads(doc.sections_signees or "{}")
    sections_signed_for_role = sigs.get(role, [])

    peut_signer_employe = (role == "employe" and doc.workflow_state == "Envoyé Signataire")
    peut_signer_dg = (role == "dg" and doc.workflow_state == "Signé Employé")
    peut_editer_perso = peut_signer_employe and bool(doc.phone_confirmed)

    fmt = lambda v, ft="Date": frappe.format_value(v, {"fieldtype": ft}) if v else ""

    context.no_cache = 1
    context.show_sidebar = 0
    context.is_error = False
    context.contrat = contrat_dict
    context.contract_id = doc.name
    context.token = token
    context.role = role
    context.sections = sections
    context.total_sections = len(sections)
    context.sections_signed = sections_signed_for_role
    context.phone_confirmed = bool(doc.phone_confirmed)
    context.phone_hint = (doc.telephone or "")[-4:] if doc.telephone else "????"
    context.peut_signer_employe = peut_signer_employe
    context.peut_signer_dg = peut_signer_dg
    context.peut_editer_perso = peut_editer_perso
    context.is_finalized = doc.workflow_state == "Finalisé"
    context.date_signature_employe_fmt = fmt(doc.date_signature_employe, "Datetime")
    context.date_signature_dg_fmt = fmt(doc.date_signature_dg, "Datetime")
    context.title = f"Contrat {doc.name} — KYA-Energy Group"
    return context

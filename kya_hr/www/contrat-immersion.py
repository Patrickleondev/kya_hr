# pyright: reportMissingImports=false
"""Portail web /contrat-immersion?name=XXX&token=YYY (accès via token, sans
compte) — stagiaire, maître de stage et garant (tuteur légal / établissement)
lisent puis signent le Contrat Stage Immersion KYA, avant le DG."""
import json
import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.translate import print_language

no_cache = 1
allow_guest = True

_ROLE_STATE = {
    "stagiaire": "Envoyé Stagiaire",
    "maitre": "Envoyé Maître Stage",
    "garant": "Envoyé Garant",
}
FINAL_STATES = ("Signé",)


def _split_sections(html):
    if not html:
        return []
    parts = re.split(r"(?=<h[1-3][\s>])", html, flags=re.IGNORECASE)
    sections = []
    preamble = []
    for p in parts:
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
    from kya_hr.api.contrat_immersion_signature import _verify_token, _ROLE_TOKEN_FIELD

    contract_id = frappe.form_dict.get("name")
    token = frappe.form_dict.get("token")

    if not contract_id or not token:
        context.is_error = True
        context.error_msg = "Lien invalide. Veuillez utiliser le lien reçu par e-mail."
        context.title = "Lien invalide"
        return context

    if not frappe.db.exists("Contrat Stage Immersion KYA", contract_id):
        context.is_error = True
        context.error_msg = "Contrat introuvable."
        context.title = "Contrat introuvable"
        return context

    doc = frappe.get_doc("Contrat Stage Immersion KYA", contract_id)

    role = None
    for r in _ROLE_TOKEN_FIELD:
        if _verify_token(doc, token, r):
            role = r
            break
    if not role:
        context.is_error = True
        context.error_msg = "Lien invalide ou expiré. Contactez la RH si le problème persiste."
        context.title = "Accès refusé"
        return context

    rendered_body = ""
    try:
        _prev_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            with print_language("fr"):
                rendered_body = frappe.get_print(
                    "Contrat Stage Immersion KYA", doc.name,
                    print_format="Contrat Stage Immersion KYA", no_letterhead=1)
        finally:
            frappe.set_user(_prev_user)
    except Exception:
        rendered_body = ""

    sections = _split_sections(rendered_body)
    sections_signed = json.loads(doc.sections_signees or "{}").get(role, [])

    can_sign = doc.workflow_state == _ROLE_STATE.get(role)
    phone_confirmed = bool(doc.phone_confirmed_stagiaire) if role == "stagiaire" else True

    context.no_cache = 1
    context.show_sidebar = 0
    context.is_error = False
    context.contrat = doc.as_dict(convert_dates_to_str=False)
    context.contract_id = doc.name
    context.token = token
    context.role = role
    context.sections = sections
    context.total_sections = len(sections)
    context.sections_signed = sections_signed
    context.phone_confirmed = phone_confirmed
    context.can_sign = can_sign
    context.can_edit_garant_info = (
        role == "garant" and doc.type_garant == "Tuteur Légal" and can_sign
    )
    from kya_hr.api.contrat_immersion_signature import _phone_digits
    context.phone_hint = _phone_digits(doc.telephone)[-4:] or "????"
    context.is_finalized = doc.workflow_state in FINAL_STATES
    context.final_pdf_download_url = (
        "/api/method/kya_hr.api.print_format.download_pdf"
        f"?doctype=Contrat%20Stage%20Immersion%20KYA&name={quote(doc.name)}"
        "&format=Contrat%20Stage%20Immersion%20KYA&language=fr"
    ) if context.is_finalized else ""
    context.title = f"Contrat de stage {doc.name} — KYA-Energy Group"
    return context

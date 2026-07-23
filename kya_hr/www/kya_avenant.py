# pyright: reportMissingImports=false
"""Portail web /kya-avenant?name=XXX&token=YYY — signature en ligne de l'avenant.

Version allégée du portail contrat : l'avenant est UN seul document (pas de
sections multiples ni d'infos père/mère). L'accès se fait par jeton (pas de
login) ; le token fait foi de l'autorisation."""
import frappe
from urllib.parse import quote

no_cache = 1
allow_guest = True

EMPLOYEE_SIGNATURE_STATES = ("En attente Signature Salarié",)
FINAL_STATES = ("Signé",)
DT = "Avenant Contrat KYA"
PRINT_FORMAT = "Avenant Contrat KYA"


def get_context(context):
    name = frappe.form_dict.get("name") or frappe.form_dict.get("id")
    token = frappe.form_dict.get("token")

    def _err(msg, title):
        context.error_msg = msg
        context.is_error = True
        context.title = title
        return context

    if not name or not token:
        return _err("Lien invalide. Veuillez utiliser le lien reçu par email.", "Lien invalide")
    if not frappe.db.exists(DT, name):
        return _err("Avenant introuvable.", "Avenant introuvable")

    doc = frappe.get_doc(DT, name)
    role = None
    if doc.access_token_signataire and token == doc.access_token_signataire:
        role = "employe"
    elif doc.access_token_dg and token == doc.access_token_dg:
        role = "dg"
    else:
        return _err("Lien invalide ou expiré. Contactez la RH si le problème persiste.", "Accès refusé")

    # Rendu du document via le print format (fidélité au modèle). Le signataire
    # accède en Guest ; frappe.get_print exige la permission 'print' → on élève
    # temporairement au contexte système (le jeton fait foi de l'autorisation).
    rendered_body = ""
    _prev = frappe.session.user
    try:
        frappe.set_user("Administrator")
        rendered_body = frappe.get_print(DT, doc.name, print_format=PRINT_FORMAT, no_letterhead=1)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "kya-avenant — rendu")
        rendered_body = "<p style='color:#c0392b'>Le document n'a pas pu être affiché. Contactez la RH.</p>"
    finally:
        frappe.set_user(_prev)

    from kya_hr.api.kya_contracts import _normalize_phone

    peut_signer_employe = (role == "employe" and doc.workflow_state in EMPLOYEE_SIGNATURE_STATES)
    peut_signer_dg = (role == "dg" and doc.workflow_state == "En attente DG")
    fmt = lambda v, ft="Datetime": frappe.format_value(v, {"fieldtype": ft}) if v else ""

    context.no_cache = 1
    context.show_sidebar = 0
    context.is_error = False
    context.avenant = doc.as_dict(convert_dates_to_str=False)
    context.rendered_body = rendered_body
    context.name = doc.name
    context.token = token
    context.role = role
    context.phone_confirmed = bool(doc.phone_confirmed)
    context.phone_hint = (_normalize_phone(doc.telephone)[-4:] if doc.telephone else "") or "????"
    context.peut_signer_employe = peut_signer_employe
    context.peut_signer_dg = peut_signer_dg
    context.is_finalized = doc.workflow_state in FINAL_STATES
    context.final_pdf_download_url = (
        "/api/method/kya_hr.api.avenant_signature.download_final_pdf"
        f"?name={quote(doc.name)}&token={quote(token)}"
    ) if context.is_finalized else ""
    context.date_signature_employe_fmt = fmt(doc.date_signature_employe)
    context.date_signature_dg_fmt = fmt(doc.date_signature_dg)
    context.title = f"Avenant {doc.name} — KYA-Energy Group"
    return context

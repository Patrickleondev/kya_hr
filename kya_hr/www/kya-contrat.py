"""Portail web /kya-contrat?name=KYA-CTR-2026-00001."""
import frappe
from frappe import _


def get_context(context):
    contract_id = frappe.form_dict.get("name") or frappe.form_dict.get("id")
    if not contract_id:
        frappe.throw(_("Paramètre 'name' manquant"), frappe.PermissionError)

    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = f"/login?redirect-to=/kya-contrat?name={contract_id}"
        raise frappe.Redirect

    if not frappe.db.exists("KYA Contrat", contract_id):
        frappe.throw(_("Contrat introuvable"), frappe.DoesNotExistError)

    doc = frappe.get_doc("KYA Contrat", contract_id)
    user = frappe.session.user
    roles = set(frappe.get_roles())

    is_signataire = (user == doc.employee_email)
    is_dg = bool(roles & {"Directeur Général", "DG", "System Manager"})
    is_rh = bool(roles & {"HR Manager", "Responsable RH", "System Manager"})

    if not (is_signataire or is_dg or is_rh):
        frappe.throw(_("Accès non autorisé à ce contrat"), frappe.PermissionError)

    # Rendu du template Jinja stocké dans KYA Contract Template
    rendered_body = ""
    if doc.template:
        tpl = frappe.get_doc("KYA Contract Template", doc.template)
        if tpl.html_body:
            try:
                rendered_body = frappe.render_template(tpl.html_body, {"doc": doc, "frappe": frappe})
            except Exception as e:
                rendered_body = f"<p style='color:red'>Erreur de rendu du template : {e}</p>"

    context.no_cache = 1
    context.show_sidebar = 0
    context.contrat = doc
    context.html_contrat = rendered_body
    context.peut_signer_employe = is_signataire and doc.workflow_state == "Envoyé Signataire"
    context.peut_signer_dg = is_dg and doc.workflow_state == "Signé Employé"
    context.is_finalized = doc.workflow_state == "Finalisé"
    context.title = f"Contrat {doc.name} — KYA-Energy Group"
    return context

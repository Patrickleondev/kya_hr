import json

import frappe
from frappe import _

from kya_hr.kya_hr.api import rh_effectifs

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not rh_effectifs._RH_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé aux Ressources Humaines."), frappe.PermissionError)

    try:
        context.overview_json = json.dumps(rh_effectifs.dashboard_data(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "rh-effectifs: dashboard_data")
    # Les pages www ne chargent pas le bundle JS `frappe` : sans ce jeton
    # injecté à la main, tout appel POST (l'import du classeur) serait rejeté.
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.peut_importer = bool(
        {"System Manager", "Responsable RH", "HR Manager", "Assistant(e) RH"}
        & set(frappe.get_roles(frappe.session.user)))
    context.no_breadcrumbs = True
    return context

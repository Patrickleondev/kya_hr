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
        context.salaries_json = json.dumps(rh_effectifs.liste_salaries(), default=str)
    except Exception:
        context.salaries_json = "[]"
        frappe.log_error(frappe.get_traceback(), "parcours-salarie: liste")
    # Jeton CSRF : la page fait des POST (téléversement de la photo) via fetch,
    # sans le bundle JS `frappe` → on l'injecte nous-mêmes.
    try:
        context.csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        context.csrf_token = ""
    context.no_breadcrumbs = True
    return context

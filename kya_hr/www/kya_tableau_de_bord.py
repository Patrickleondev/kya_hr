"""
Contexte Python pour la page Tableau de Bord Global KYA.
Réservé aux rôles DG / Directeur Général / System Manager / Administrator.
"""
import frappe
from frappe import _


def get_context(context):
    allowed = {"DG", "DGA", "Directeur Général", "System Manager", "Administrator"}
    user_roles = set(frappe.get_roles())
    if not user_roles.intersection(allowed):
        frappe.throw(_("Accès réservé à la Direction Générale"), frappe.PermissionError)

    context.no_cache = 1
    context.title = "Tableau de Bord Global KYA"
    context.show_sidebar = False
    # CSRF token pour les fetch() POST cote frontend (sync_dashboard_entries_from_web_forms)
    try:
        from frappe.sessions import get_csrf_token
        context.csrf_token = get_csrf_token()
    except Exception:
        context.csrf_token = ""

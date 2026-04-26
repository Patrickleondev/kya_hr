"""
Contexte Python pour la page Tableau de Bord Global KYA.
Réservé aux rôles DG / Directeur Général / System Manager / Administrator.
"""
import frappe
from frappe import _


def get_context(context):
    allowed = {"DG", "Directeur Général", "System Manager", "Administrator"}
    user_roles = set(frappe.get_roles())
    if not user_roles.intersection(allowed):
        frappe.throw(_("Accès réservé à la Direction Générale"), frappe.PermissionError)

    context.no_cache = 1
    context.title = "Tableau de Bord Global KYA"
    context.show_sidebar = False

# -*- coding: utf-8 -*-
"""Page RH — génération des documents dynamiques (certificats / attestations)."""
import frappe
from frappe import _

no_cache = 1

_ALLOWED = {"Responsable RH", "HR Manager", "HR User", "Directeur Général",
            "DGA", "System Manager"}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED.intersection(roles):
        frappe.throw(_("Accès réservé à la RH et à la Direction."), frappe.PermissionError)
    context.is_dg = bool({"Directeur Général", "DGA", "System Manager"}.intersection(roles))
    context.no_breadcrumbs = True
    return context

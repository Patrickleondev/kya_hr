"""Page Dashboard Formation. Route : /formation-dashboard."""
from __future__ import annotations

import frappe

ACCESS_ROLES = {
    "System Manager", "Responsable RH", "HR Manager",
    "Directeur Général", "DG", "DGA",
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/formation-dashboard"
        raise frappe.Redirect
    if not (set(frappe.get_roles(user)) & ACCESS_ROLES):
        frappe.throw("Accès réservé à la RH et à la Direction.", frappe.PermissionError)
    context.page_title = "Dashboard Formation KYA"
    context.no_cache = 1
    return context

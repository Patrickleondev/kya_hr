"""Page Dashboard Logistique. Route : /kya-logistique-dashboard."""
from __future__ import annotations

import frappe


ACCESS_ROLES = {
    "System Manager", "Directeur General", "DG", "DGA",
    "Responsable Logistique", "Logisticien", "Chef Service",
    "Chef Service Achats", "Auditeur",
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/kya-logistique-dashboard"
        raise frappe.Redirect

    user_roles = set(frappe.get_roles(user))
    if not (user_roles & ACCESS_ROLES):
        frappe.throw(
            "Acces refuse - role Logistique requis (Logisticien, "
            "DG, DGA, ou Auditeur).",
            frappe.PermissionError,
        )

    context.page_title = "Dashboard Logistique KYA"
    context.no_cache = 1
    return context

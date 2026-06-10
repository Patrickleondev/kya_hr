"""Page : Dashboard Stocks Generalise KYA.

Route : /kya-stocks-dashboard
"""
from __future__ import annotations

import frappe


STOCK_ACCESS_ROLES = {
    "Stock User", "Stock Manager", "System Manager",
    "Directeur General", "DG", "DGA",
    "Responsable RH", "Chef Service Achats", "Auditeur",
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/kya-stocks-dashboard"
        raise frappe.Redirect

    user_roles = set(frappe.get_roles(user))
    if not (user_roles & STOCK_ACCESS_ROLES):
        frappe.throw(
            "Acces refuse - vous devez avoir un role Stock (Stock User, "
            "Stock Manager, Auditeur, DG, DGA, Responsable RH, ou Chef Service Achats).",
            frappe.PermissionError,
        )

    # Listes pour les filtres
    context.item_groups = frappe.db.sql_list(
        "SELECT name FROM `tabItem Group` WHERE is_group=0 ORDER BY name"
    )
    context.warehouses = frappe.db.sql_list(
        "SELECT name FROM `tabWarehouse` WHERE disabled=0 AND is_group=0 ORDER BY name"
    )

    context.page_title = "Dashboard Stocks KYA"
    context.no_cache = 1
    return context

# -*- coding: utf-8 -*-
"""Contrôleur de la page « Effectifs de mon équipe » (/equipe-effectifs)."""
import frappe

no_cache = 1

_ALLOWED = {"Responsable RH", "HR Manager", "HR User", "System Manager",
            "Directeur Général", "DGA", "DG"}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/equipe-effectifs"
        raise frappe.Redirect

    roles = set(frappe.get_roles(frappe.session.user))
    emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    is_rh = bool(_ALLOWED.intersection(roles))
    is_chef = bool(emp) and bool(
        frappe.get_all("Equipe KYA", filters={"chef_equipe": emp}, limit=1))

    if not (is_rh or is_chef):
        context.no_access = True
    context.no_access = not (is_rh or is_chef)
    context.is_rh = is_rh
    context.is_chef = is_chef
    return context

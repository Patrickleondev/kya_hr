# -*- coding: utf-8 -*-
"""Contrôleur de la page RH « Avenants au contrat » (/avenants-rh)."""
import frappe

no_cache = 1

_RH = {"Responsable RH", "HR Manager", "HR User", "System Manager",
       "Directeur Général", "DGA"}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/avenants-rh"
        raise frappe.Redirect
    roles = set(frappe.get_roles(frappe.session.user))
    context.no_access = not bool(_RH.intersection(roles))
    context.is_dg = bool({"Directeur Général", "DGA"}.intersection(roles))
    return context

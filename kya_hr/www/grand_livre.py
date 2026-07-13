# -*- coding: utf-8 -*-
"""Page /grand-livre — consultation du Grand Livre KYA (Comptabilité)."""
import frappe
from frappe.utils import getdate, today

from kya_hr.api.grand_livre import RH_COMPTA_ROLES, get_grand_livre, liste_comptes

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Veuillez vous connecter", frappe.AuthenticationError)
    if not (RH_COMPTA_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw("Accès réservé à la Comptabilité et à la Direction.",
                     frappe.PermissionError)

    year = getdate(today()).year
    fd = frappe.form_dict.get("from") or f"{year}-01-01"
    td = frappe.form_dict.get("to") or f"{year}-12-31"
    compte = frappe.form_dict.get("compte") or None

    data = get_grand_livre(fd, td, compte)
    context.no_cache = 1
    context.gl = data
    context.from_date = fd
    context.to_date = td
    context.compte = compte or ""
    context.comptes_dispo = liste_comptes()
    context.year = year
    context.no_breadcrumbs = True
    return context

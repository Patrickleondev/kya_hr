# -*- coding: utf-8 -*-
"""Page RH /gestion-conges — pilotage simple des congés (adossé HRMS natif)."""
import frappe
from frappe.utils import getdate, today

from kya_hr.api.conges import RH_ROLES, get_overview

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Veuillez vous connecter", frappe.AuthenticationError)

    roles = set(frappe.get_roles(frappe.session.user))
    if not (RH_ROLES & roles):
        frappe.throw(
            "Accès réservé aux rôles RH (Responsable RH, HR Manager/User, DAAF, Direction).",
            frappe.PermissionError,
        )

    year = getdate(today()).year
    data = get_overview(year=year)

    context.no_cache = 1
    context.year = year
    context.years = list(range(year - 3, year + 2))
    context.overview = data
    context.rows = data["rows"]
    context.totals = data["totals"]
    context.leave_type = data["leave_type"]
    context.leave_types = data["leave_types"]
    context.count = data["count"]
    context.en_conge = data["en_conge"]
    return context

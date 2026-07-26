# -*- coding: utf-8 -*-
import frappe

_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "System Manager",
             "Directeur Général", "DGA"}


def get_context(context):
    context.no_cache = 1
    user = frappe.session.user
    if user == "Guest":
        context.no_access = True
        return

    roles = set(frappe.get_roles(user))
    is_rh = bool(_RH_ROLES & roles)
    me = frappe.db.get_value("Employee", {"user_id": user}, "name")
    is_chef = bool(frappe.get_all("Equipe KYA", filters={"chef_equipe": me}, limit=1)) if me else False

    context.is_rh = is_rh
    context.is_chef = is_chef
    context.has_employee = bool(me)
    context.no_access = not (is_rh or me or is_chef)
    return context

# -*- coding: utf-8 -*-
"""Page /planning-equipe : le chef d'équipe saisit, en début d'année, le
planning de congé prévisionnel de ses collègues, puis le soumet à la RH."""
import frappe
from frappe import _

_ALLOWED = {
    "Chef Service", "Chef Equipe", "Chef d'Équipe", "Supérieur Immédiat",
    "Responsable RH", "HR Manager", "HR User", "System Manager",
    "Directeur Général", "DGA",
}


def _is_team_chef(user):
    """Un chef est identifié par Equipe KYA.chef_equipe (peut ne pas avoir de rôle)."""
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return bool(emp and frappe.db.exists("Equipe KYA", {"chef_equipe": emp}))


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not (_ALLOWED.intersection(set(frappe.get_roles(frappe.session.user)))
            or _is_team_chef(frappe.session.user)):
        frappe.throw(_("Accès réservé aux chefs d'équipe et à la RH."), frappe.PermissionError)
    context.no_cache = 1
    return context

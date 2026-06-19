# -*- coding: utf-8 -*-
"""Page /calendrier-conges : calendrier annuel visuel des congés planifiés
par équipe (alimenté par les Planning de Congé d'Équipe)."""
import frappe
from frappe import _

_ALLOWED = {
    "Chef Service", "Chef Equipe", "Chef d'Équipe", "Supérieur Immédiat",
    "Responsable RH", "HR Manager", "HR User", "System Manager",
    "Directeur Général", "DGA", "Maître de Stage", "Responsable des Stagiaires",
}


def _is_team_chef(user):
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    return bool(emp and frappe.db.exists("Equipe KYA", {"chef_equipe": emp}))


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not (_ALLOWED.intersection(set(frappe.get_roles(frappe.session.user)))
            or _is_team_chef(frappe.session.user)):
        frappe.throw(_("Accès réservé à l'encadrement et à la RH."), frappe.PermissionError)
    context.no_cache = 1
    return context

# -*- coding: utf-8 -*-
"""Page /rapport-presence : rapport de présence PAR EMPLOYÉ (jours travaillés,
heures, retards, absences) sur semaine / mois / trimestre, exportable.
Les données sont chargées côté client via kya_hr.api.attendance.get_attendance_report."""
import frappe
from frappe import _

_VIEW_ROLES = {
    "Responsable RH", "HR Manager", "HR User", "Maître de Stage",
    "Responsable des Stagiaires", "System Manager",
    "Directeur Général", "DGA", "Chef Service",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not _VIEW_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la RH et à la Direction."), frappe.PermissionError)
    context.no_cache = 1
    return context

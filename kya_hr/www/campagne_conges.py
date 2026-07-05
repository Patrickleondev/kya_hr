# -*- coding: utf-8 -*-
"""Page RH /campagne-conges — cockpit de la campagne annuelle de planning
des congés : la RH définit la période, ouvre la campagne (brouillons +
liens aux chefs) et suit les soumissions.

La donnée est chargée côté client via kya_hr.api.campagne_conges.
"""
import frappe
from frappe import _

from kya_hr.api.campagne_conges import RH_ROLES

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not (RH_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la RH et à la Direction."), frappe.PermissionError)
    context.no_cache = 1
    return context

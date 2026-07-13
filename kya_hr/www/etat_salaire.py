# -*- coding: utf-8 -*-
"""Page /etat-salaire — livre de paie KYA (Comptabilité)."""
import frappe
from frappe.utils import getdate, today

from kya_hr.api.etat_salaire import (MOIS, RH_COMPTA_ROLES, get_etat_salaire,
                                     kpis_paie)

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Veuillez vous connecter", frappe.AuthenticationError)
    if not (RH_COMPTA_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw("Accès réservé à la Comptabilité et à la Direction.",
                     frappe.PermissionError)

    year = getdate(today()).year
    annee = int(frappe.form_dict.get("annee") or year)
    mois = frappe.form_dict.get("mois") or None

    context.no_cache = 1
    context.data = get_etat_salaire(annee, mois)
    context.kpis = kpis_paie(annee)
    context.annee = annee
    context.mois = mois or ""
    context.mois_dispo = MOIS
    context.annees = list(range(year + 1, year - 4, -1))
    context.no_breadcrumbs = True
    return context

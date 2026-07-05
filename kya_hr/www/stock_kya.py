# -*- coding: utf-8 -*-
"""Page /stock-kya — cockpit du stock maison (grand livre Mouvement Stock KYA).

Soldes temps réel par magasin (total / bon état / en réparation), export de
l'inventaire, import « template » d'articles classés par magasin, derniers
mouvements. Données chargées côté client via kya_hr.api.stock_kya.
"""
import frappe
from frappe import _

from kya_hr.api.stock_kya import _STOCK_ROLES

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not (_STOCK_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé au magasin / stock."), frappe.PermissionError)
    context.no_cache = 1
    return context

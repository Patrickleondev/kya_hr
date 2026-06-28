"""Page /stock-etat : vue consolidée du stock par état (disponible / à réparer /
endommagé), tous magasins confondus. Données via kya_hr.stock_etats.get_stock_par_etat.

Accès : Responsable Stock / magasiniers + Direction (pas d'équipe inventaire dédiée).
"""
import frappe
from frappe import _

_VIEW_ROLES = {
    "Responsable Stock", "Chargé des Stocks", "Stock Manager", "Stock User",
    "Magasinier", "System Manager", "Directeur Général", "DG", "DGA",
    "DAAF", "Auditeur Interne",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not _VIEW_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé au magasin et à la Direction."),
                     frappe.PermissionError)
    context.no_cache = 1
    context.no_breadcrumbs = True
    return context

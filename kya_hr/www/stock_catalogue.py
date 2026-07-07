"""Catalogue du stock consultable par les demandeurs (chefs d'équipe,
personnel) avant une demande de sortie. Lecture seule, sans détails
sensibles. Accessible à tout utilisateur connecté — pensé mobile d'abord."""
import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/stock-catalogue"
        raise frappe.Redirect
    context.title = "Catalogue du stock"
    return context

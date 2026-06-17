import frappe


def get_context(context):
    """Web Form Entretien véhicule — accès Gestionnaire de Flotte / RH / admin."""
    context.user_roles = frappe.get_roles(frappe.session.user)

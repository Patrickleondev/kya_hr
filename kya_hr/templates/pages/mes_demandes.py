import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Vous devez être connecté pour accéder à cette page.", frappe.PermissionError)

    context.no_breadcrumbs = False
    context.title = "Mes Demandes"

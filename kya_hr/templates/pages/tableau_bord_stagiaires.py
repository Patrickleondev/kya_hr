import frappe


def get_context(context):
    allowed_roles = {"System Manager", "HR Manager", "HR User", "Resp. Stagiaires"}
    user_roles = set(frappe.get_roles(frappe.session.user))
    if frappe.session.user == "Guest" or not (user_roles & allowed_roles):
        frappe.throw(
            "Accès réservé au personnel RH et responsables stagiaires.",
            frappe.PermissionError,
        )

    context.no_breadcrumbs = False
    context.title = "Tableau de Bord — Stagiaires"

import frappe


def get_context(context):
    allowed_roles = {"System Manager", "HR Manager", "HR User", "Accounts Manager", "Purchase Manager"}
    user_roles = set(frappe.get_roles(frappe.session.user))
    if frappe.session.user == "Guest":
        frappe.throw(
            "Connexion requise.",
            frappe.PermissionError,
        )

    if not (user_roles & allowed_roles):
        # Employé standard: expérience recentrée sur le portail personnel.
        frappe.local.flags.redirect_location = "/mon-espace"
        raise frappe.Redirect

    context.no_breadcrumbs = False
    context.title = "Tableau de Bord — Employés"

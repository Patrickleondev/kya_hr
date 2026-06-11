import frappe


def get_context(context):
    # Noms de roles REELS (verifies en BD). Le code utilisait
    # "Resp. Stagiaires" qui n'existe pas -> 403 pour les vrais
    # responsables. On accepte tous les libelles equivalents.
    allowed_roles = {
        "System Manager", "HR Manager", "HR User",
        "Responsable RH", "Responsable des Stagiaires", "Maître de Stage",
        "Directeur Général", "DG", "DGA",
    }
    user_roles = set(frappe.get_roles(frappe.session.user))
    if frappe.session.user == "Guest" or not (user_roles & allowed_roles):
        frappe.throw(
            "Accès réservé au personnel RH et responsables stagiaires.",
            frappe.PermissionError,
        )

    context.no_breadcrumbs = False
    context.title = "Tableau de Bord — Stagiaires"

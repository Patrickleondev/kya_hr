import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Connexion requise.", frappe.PermissionError)

    emp = frappe.db.get_value(
        "Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
    )
    is_rh = bool(
        {"Responsable RH", "HR Manager", "HR User", "System Manager"}.intersection(
            set(frappe.get_roles(frappe.session.user))
        )
    )
    is_chef = bool(frappe.db.exists("Equipe KYA", {"chef_equipe": emp})) if emp else False

    if not (is_rh or is_chef):
        frappe.throw(
            "Accès réservé aux chefs d'équipe et à la RH.", frappe.PermissionError
        )

    context.no_cache = 1

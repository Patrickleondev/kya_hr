import frappe


def get_context(context):
    """Web Form Besoin de Formation — soumission par le chef d'équipe."""
    context.user_roles = frappe.get_roles(frappe.session.user)
    # Employé du chef connecté (pour pré-remplissage côté client)
    emp = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        ["name", "department"],
        as_dict=True,
    )
    context.current_employee = emp.name if emp else None
    context.current_department = emp.department if emp else None

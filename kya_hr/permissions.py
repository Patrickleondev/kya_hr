import frappe


PRIVILEGED_ROLES = {
    "System Manager",
    "HR Manager",
    "HR User",
    "Chef Service",
    "DG",
    "DGA",
}


def _is_privileged(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    roles = set(frappe.get_roles(user))
    return bool(roles & PRIVILEGED_ROLES)


def employee_query_condition(user=None):
    user = user or frappe.session.user
    if _is_privileged(user):
        return ""

    employee_name = frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"}, "name"
    )
    if not employee_name:
        return "1=0"

    return f"`tabEmployee`.name = {frappe.db.escape(employee_name)}"


def employee_has_permission(doc, user=None, ptype=None):
    user = user or frappe.session.user
    if _is_privileged(user):
        return True

    employee_name = frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"}, "name"
    )
    if not employee_name:
        return False

    if not doc:
        return True

    return doc.name == employee_name

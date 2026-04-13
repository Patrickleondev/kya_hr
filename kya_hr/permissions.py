import frappe


def employee_query_condition(user=None):
    """Permission query for Employee DocType.

    Stagiaires (users who ONLY have the Stagiaire role and no HR/management role)
    can only see their own Employee record.  All other users see the full list.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # These roles grant full Employee list access
    elevated_roles = {
        "HR User", "HR Manager", "System Manager",
        "Administrator", "DG", "DGA", "DAAF",
        "Responsable des Stagiaires", "Maître de Stage",
        "Chef Service", "Chef Equipe",
    }

    if "Stagiaire" in roles and not elevated_roles.intersection(roles):
        # Restrict to the employee whose user_id matches the logged-in user
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if employee:
            # Sanitize: employee name is an internal ID, but escape single quotes to be safe
            safe_name = employee.replace("'", "\\'")
            return f"`tabEmployee`.`name` = '{safe_name}'"
        # No employee record linked → show nothing
        return "`tabEmployee`.`name` IS NULL"

    return ""

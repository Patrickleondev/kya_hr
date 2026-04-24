import frappe


def get_context(context):
    """Controller Web Form Planning Congé.
    Circuit: Employé -> Responsable RH -> Directeur Général.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    context.can_sign_employe = True
    context.can_sign_rh = False
    context.can_sign_dg = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles

    context.can_sign_employe = state == "Brouillon"
    context.can_sign_rh      = (state == "En attente RH") and ("Responsable RH" in roles or is_admin)
    context.can_sign_dg      = (state == "En attente DG") and ("Directeur Général" in roles or is_admin)

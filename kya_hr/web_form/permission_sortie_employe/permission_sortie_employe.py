import frappe


def get_context(context):
    """Controller Web Form Permission Sortie Employé.
    Circuit: Employé -> Chef Service -> Responsable RH -> DGA (ou DG si DGA absent).
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    context.can_sign_employe = True
    context.can_sign_chef = False
    context.can_sign_rh = False
    context.can_sign_dga = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles

    context.can_sign_employe = state == "Brouillon"
    context.can_sign_chef    = (state == "En attente Chef")      and ("Chef Service"  in roles or is_admin)
    context.can_sign_rh      = (state == "En attente RH")        and ("Responsable RH" in roles or is_admin)
    context.can_sign_dga     = (state == "En attente Direction") and (
        "DGA" in roles or "Directeur Général" in roles or is_admin
    )

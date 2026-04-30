import frappe


def get_context(context):
    """Controller Web Form Inventaire KYA.
    Circuit: Responsable inventaire -> Magasin (Chargé des Stocks ou Responsable Stock).
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    context.can_sign_responsable = True
    context.can_sign_magasin = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles

    context.can_sign_responsable = state == "Brouillon"
    context.can_sign_magasin = (state == "En attente Magasin") and (
        "Chargé des Stocks" in roles or "Responsable Stock" in roles or is_admin
    )

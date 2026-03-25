import frappe


def get_context(context):
    user = frappe.session.user
    context.user_roles = frappe.get_roles(user)

    # Provide the list of possible delegates (employees other than the current user)
    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    if context.doc:
        doc = context.doc
        state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
        roles = context.user_roles

        # Determine which signature sections are editable for this user
        context.can_sign_demandeur = state == "Brouillon"
        context.can_sign_chef = (state == "En attente Chef" and
            any(r in roles for r in ["Purchase User", "Purchase Manager", "Stock Manager",
                                     "Stock User", "System Manager"]))
        context.can_sign_audit = (state == "En attente Audit" and
            any(r in roles for r in ["Purchase Manager", "Accounts Manager",
                                     "HR Manager", "System Manager"]))
        context.can_sign_dga = (state == "En attente DGA" and
            any(r in roles for r in ["HR Manager", "System Manager"]))
        context.can_sign_magasin = (state == "En attente Magasin" and
            any(r in roles for r in ["Stock Manager", "Stock User", "System Manager"]))

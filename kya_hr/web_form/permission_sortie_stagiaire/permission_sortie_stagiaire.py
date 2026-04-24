import frappe


def get_context(context):
    """Controller Web Form Permission Sortie Stagiaire.
    Circuit: Stagiaire -> Maître de Stage -> Responsable des Stagiaires -> Directeur Général.
    Permission peut couvrir plusieurs jours non-consécutifs (jours de permission).
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    context.can_sign_stagiaire = True
    context.can_sign_chef = False
    context.can_sign_resp_stagiaires = False
    context.can_sign_dg = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles

    context.can_sign_stagiaire        = state == "Brouillon"
    context.can_sign_chef             = (state == "En attente Chef")             and ("Maître de Stage" in roles or is_admin)
    context.can_sign_resp_stagiaires  = (state == "En attente Resp. Stagiaires") and ("Responsable des Stagiaires" in roles or is_admin)
    context.can_sign_dg               = (state == "En attente DG")               and ("Directeur Général" in roles or is_admin)

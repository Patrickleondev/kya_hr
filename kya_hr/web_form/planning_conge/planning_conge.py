import frappe


def get_context(context):
    """Controller Web Form Planning Congé.
    Circuit: Employé -> Chef de Service (Supérieur Immédiat) -> Directeur Général.
    La RH peut intervenir en override sur l'étape Chef de Service.

    Restriction d'accès : la CRÉATION est réservée à l'encadrement + RH (le chef
    saisit le planning de son équipe via /planning-equipe). Le web form ne peut
    pas bloquer le rendu de /new via get_context (Frappe n'y vérifie les droits
    que pour un document EXISTANT) ; le blocage réel se fait au SUBMIT par la
    permission `create` du DocType Planning Conge, retirée au rôle Employee
    (cf. kya_hr.ensure_workflow_perms) — la saisie d'équipe passe outre via
    ignore_permissions.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    context.can_sign_employe = True
    context.can_sign_chef = False
    context.can_sign_rh = False
    context.can_sign_dg = False
    context.is_chef_of_doc = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles
    is_rh = ("Responsable RH" in roles) or ("HR Manager" in roles) or is_admin

    report_to_user = doc.get("report_to_user") or ""
    context.is_chef_of_doc = (user == report_to_user)

    context.can_sign_employe = state == "Brouillon"
    context.can_sign_chef = (state == "En attente Chef de Service") and (
        context.is_chef_of_doc or "Supérieur Immédiat" in roles
    )
    context.can_sign_rh = (state == "En attente Chef de Service") and is_rh
    context.can_sign_dg = (state == "En attente DG") and (
        "Directeur Général" in roles or is_admin
    )

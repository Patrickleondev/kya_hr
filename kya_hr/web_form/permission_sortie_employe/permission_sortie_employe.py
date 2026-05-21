import frappe


def get_context(context):
    """Controller Web Form Permission Sortie Employé.
    Circuit: Employé -> Chef Service -> Responsable RH -> DGA (ou DG si DGA absent).
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employment_type"],
        as_dict=True,
    )

    if employee and employee.employment_type == "Stage" and not context.doc:
        frappe.local.flags.redirect_location = "/permission-sortie-stagiaire/new"
        raise frappe.Redirect

    context.current_employee = employee.name if employee else None

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
    # Le palier 'En attente Chef' accepte AUSSI le role 'Superieur Immediat'
    # (cas Chef Service Informatique qui est sup immediat d'un employe sans
    # avoir le role 'Chef Service' explicite). HR Manager / Responsable RH
    # peuvent egalement valider en absence du chef.
    context.can_sign_chef    = (state == "En attente Chef") and (
        "Chef Service" in roles
        or "Supérieur Immédiat" in roles
        or "Responsable RH" in roles
        or "HR Manager" in roles
        or is_admin
    )
    context.can_sign_rh      = (state == "En attente RH")        and ("Responsable RH" in roles or "HR Manager" in roles or is_admin)
    context.can_sign_dga     = (state == "En attente Direction") and (
        "DGA" in roles or "Directeur Général" in roles or is_admin
    )

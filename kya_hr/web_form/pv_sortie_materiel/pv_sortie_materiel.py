import frappe


def get_context(context):
    """Controller du Web Form PV Sortie Matériel.
    Circuit KYA: Demandeur -> Chef Service -> Auditeur Interne -> Directeur Général -> Chargé des Stocks
    Les rôles ci-dessous proviennent strictement de la liste des rôles actifs en prod (Rôle.csv).
    System Manager = override admin pour les tests uniquement.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    # Valeurs par défaut (nouvelle fiche)
    context.can_sign_demandeur = True
    context.can_sign_chef = False
    context.can_sign_audit = False
    context.can_sign_dga = False
    context.can_sign_magasin = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles

    context.can_sign_demandeur = state == "Brouillon"
    context.can_sign_chef    = (state == "En attente Chef")      and ("Chef Service"       in roles or is_admin)
    context.can_sign_audit   = (state == "En attente Audit")     and ("Auditeur Interne"   in roles or is_admin)
    context.can_sign_dga     = (state == "En attente Direction") and ("Directeur Général"  in roles or is_admin)
    context.can_sign_magasin = (state == "En attente Magasin")   and ("Chargé des Stocks"  in roles or is_admin)

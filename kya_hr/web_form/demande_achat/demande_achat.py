import frappe


def get_context(context):
    """Controller Web Form Demande Achat KYA.
    Circuit: Demandeur -> Chef Service -> DAAF -> Directeur Général (selon palier).
    Paliers (XOF): < 100k = Chef seul; >= 100k = + DAAF; >= 2M = + DG.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    context.can_sign_demandeur = True
    context.can_sign_chef = False
    context.can_sign_daaf = False
    context.can_sign_dg = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles
    montant = doc.get("montant_total") or 0

    context.can_sign_demandeur = state == "Brouillon"
    context.can_sign_chef = (state == "En attente Chef") and ("Chef Service" in roles or is_admin)
    context.can_sign_daaf = (state == "En attente DAAF") and ("DAAF" in roles or is_admin)
    context.can_sign_dg = (state == "En attente DG") and ("Directeur Général" in roles or is_admin)

    if montant >= 2000000:
        context.palier_label = "Palier 3 — Directeur Général requis (≥ 2 000 000 XOF)"
        context.palier_color = "danger"
    elif montant >= 100000:
        context.palier_label = "Palier 2 — DAAF requis (≥ 100 000 XOF)"
        context.palier_color = "warning"
    else:
        context.palier_label = "Palier 1 — Chef Service uniquement"
        context.palier_color = "info"

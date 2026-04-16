import frappe


def get_context(context):
    user = frappe.session.user
    context.user_roles = frappe.get_roles(user)

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    if context.doc:
        doc = context.doc
        state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
        roles = context.user_roles
        montant = doc.get("montant_total") or 0

        context.can_sign_demandeur = state == "Brouillon"
        context.can_sign_chef = (state == "En attente Chef" and
            any(r in roles for r in ["Chef Service", "System Manager"]))
        context.can_sign_dga = (state == "En attente DAAF" and
            any(r in roles for r in ["DAAF", "Responsable Achats", "System Manager"]))
        context.can_sign_dg = (state == "En attente DG" and
            any(r in roles for r in ["Directeur Général", "System Manager"]))

        # Palier info for display
        if montant >= 2000000:
            context.palier_label = "Palier 3 — Chef + DAAF + DG requis (≥ 2 000 000 XOF)"
            context.palier_color = "danger"
        elif montant >= 100000:
            context.palier_label = "Palier 2 — Chef + DAAF + DG requis (≥ 100 000 XOF)"
            context.palier_color = "warning"
        else:
            context.palier_label = "Palier 1 — Chef + DAAF requis (< 100 000 XOF)"
            context.palier_color = "info"

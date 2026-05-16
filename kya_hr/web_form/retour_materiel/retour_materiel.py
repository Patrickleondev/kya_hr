import frappe


def get_context(context):
    """Controller du Web Form Retour Matériel.

    Circuit : Retourneur (Brouillon) -> Responsable Magasin (En attente Magasin)
              -> Approuvé / Rejeté.

    L'auto-fill de `retourneur_nom`, `project`, `customer` depuis le PV Sortie
    d'origine est géré côté DocType (`RetourMaterielKYA.validate`) et côté JS
    (client_script du Web Form).
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    context.user_roles = roles

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    context.current_employee = employee

    context.can_sign_retourneur = True
    context.can_sign_magasin = False

    if not context.doc:
        return

    doc = context.doc
    state = doc.get("workflow_state") or doc.get("statut") or "Brouillon"
    is_admin = "System Manager" in roles
    is_stock_role = any(r in roles for r in ("Stock Manager", "Stock User", "Chargé des Stocks"))

    context.can_sign_retourneur = state == "Brouillon"
    context.can_sign_magasin = (state == "En attente Magasin") and (is_stock_role or is_admin)

# -*- coding: utf-8 -*-
"""Setup du Planning de Congé d'Équipe : workflow Chef → RH → DG → Approuvé.

Idempotent et migrable (appelé depuis safe_migrations.AFTER_MIGRATE).
Crée/aligne le workflow « Flux Planning Équipe » sur le DocType
« Planning Conge Equipe ». Le champ d'état est `workflow_state`.
"""
import frappe

WORKFLOW_NAME = "Flux Planning Équipe"
DOCTYPE = "Planning Conge Equipe"

# (state, doc_status, allow_edit role)
STATES = [
    ("Brouillon", 0, "Chef Service"),
    ("En attente RH", 0, "Responsable RH"),
    ("En attente DG", 0, "Directeur Général"),
    ("Approuvé", 1, "HR Manager"),
    ("Rejeté", 2, "HR Manager"),
]

# (state, action, next_state, allowed role, condition)
TRANSITIONS = [
    # Soumission par le chef (plusieurs rôles possibles selon le paramétrage)
    ("Brouillon", "Soumettre à la RH", "En attente RH", "Chef Service", ""),
    ("Brouillon", "Soumettre à la RH", "En attente RH", "Chef Equipe", ""),
    ("Brouillon", "Soumettre à la RH", "En attente RH", "Chef d'Équipe", ""),
    ("Brouillon", "Soumettre à la RH", "En attente RH", "Supérieur Immédiat", ""),
    ("Brouillon", "Soumettre à la RH", "En attente RH", "Responsable RH", ""),
    # RH vise -> DG
    ("En attente RH", "Viser (RH)", "En attente DG", "Responsable RH", ""),
    ("En attente RH", "Viser (RH)", "En attente DG", "HR Manager", ""),
    ("En attente RH", "Rejeter (RH)", "Rejeté", "Responsable RH", ""),
    ("En attente RH", "Rejeter (RH)", "Rejeté", "HR Manager", ""),
    # DG approuve -> Approuvé
    ("En attente DG", "Approuver", "Approuvé", "Directeur Général", ""),
    ("En attente DG", "Approuver", "Approuvé", "DGA", ""),
    ("En attente DG", "Rejeter", "Rejeté", "Directeur Général", ""),
]


def _ensure_workflow_states():
    """Crée les Workflow State manquants (sinon Frappe refuse le workflow)."""
    styles = {
        "Brouillon": "Warning", "En attente RH": "Info",
        "En attente DG": "Info", "Approuvé": "Success", "Rejeté": "Danger",
    }
    for state, _ds, _ae in STATES:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": state,
                "style": styles.get(state, ""),
            }).insert(ignore_permissions=True)


def _ensure_actions():
    actions = {t[1] for t in TRANSITIONS}
    for act in actions:
        if not frappe.db.exists("Workflow Action Master", act):
            frappe.get_doc({
                "doctype": "Workflow Action Master",
                "workflow_action_name": act,
            }).insert(ignore_permissions=True)


def execute():
    if not frappe.db.exists("DocType", DOCTYPE):
        # Le DocType n'est pas encore synchronisé : on sortira proprement,
        # la prochaine migration rejouera ce setup.
        return

    _ensure_workflow_states()
    _ensure_actions()

    existing = frappe.db.exists("Workflow", WORKFLOW_NAME)
    wf = frappe.get_doc("Workflow", WORKFLOW_NAME) if existing else frappe.new_doc("Workflow")
    wf.workflow_name = WORKFLOW_NAME
    wf.document_type = DOCTYPE
    wf.workflow_state_field = "workflow_state"
    wf.is_active = 1
    wf.send_email_alert = 0
    wf.override_status = 0

    wf.set("states", [])
    for state, ds, allow_edit in STATES:
        wf.append("states", {
            "state": state, "doc_status": ds, "allow_edit": allow_edit,
        })

    wf.set("transitions", [])
    for state, action, nxt, allowed, cond in TRANSITIONS:
        wf.append("transitions", {
            "state": state, "action": action, "next_state": nxt,
            "allowed": allowed, "condition": cond, "allow_self_approval": 1,
        })

    wf.flags.ignore_permissions = True
    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"[setup_planning_equipe] Workflow '{WORKFLOW_NAME}' OK "
          f"({len(STATES)} états, {len(TRANSITIONS)} transitions).")
    return {"workflow": WORKFLOW_NAME, "states": len(STATES), "transitions": len(TRANSITIONS)}


if __name__ == "__main__":
    execute()

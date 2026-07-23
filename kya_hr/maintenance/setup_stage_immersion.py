# -*- coding: utf-8 -*-
"""Circuit du contrat de stage d'immersion — Flux Stage Immersion KYA
(Brouillon → En attente DG → Signé ; Rejeter/Reprendre). Idempotent, AFTER_MIGRATE.
"""
import frappe

WF = "Flux Stage Immersion KYA"
DT = "Contrat Stage Immersion KYA"

STATES = [
    ("Brouillon", 0, ""),
    ("En attente DG", 0, "Warning"),
    ("Signé", 1, "Success"),
    ("Rejeté", 1, "Danger"),
]
RH_ROLES = ["Responsable RH", "HR Manager", "HR User", "System Manager"]
DG_ROLES = ["Directeur Général", "DGA", "System Manager"]
TRANSITIONS = [
    ("Brouillon", "Soumettre au DG", "En attente DG", RH_ROLES, 1),
    ("En attente DG", "Signer", "Signé", DG_ROLES, 1),
    ("En attente DG", "Rejeter", "Rejeté", DG_ROLES, 1),
    ("Rejeté", "Reprendre", "Brouillon", RH_ROLES, 1),
]


def _ensure_masters():
    for name, _ds, style in STATES:
        if not frappe.db.exists("Workflow State", name):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": name,
                            "style": style}).insert(ignore_permissions=True)
    for _s, action, _n, _r, _sa in TRANSITIONS:
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc({"doctype": "Workflow Action Master",
                            "workflow_action_name": action}).insert(ignore_permissions=True)


def _ensure_workflow():
    exists = frappe.db.exists("Workflow", WF)
    doc = frappe.get_doc("Workflow", WF) if exists else frappe.new_doc("Workflow")
    doc.workflow_name = WF
    doc.document_type = DT
    doc.is_active = 1
    doc.workflow_state_field = "workflow_state"
    doc.send_email_alert = 0
    doc.set("states", [])
    for name, ds, style in STATES:
        doc.append("states", {"state": name, "doc_status": ds, "style": style,
                              "allow_edit": "Responsable RH" if name in ("Brouillon", "Rejeté") else "Directeur Général"})
    doc.set("transitions", [])
    for state, action, nxt, roles, sa in TRANSITIONS:
        for role in roles:
            doc.append("transitions", {"state": state, "action": action, "next_state": nxt,
                                       "allowed": role, "allow_self_approval": sa})
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)


def execute():
    frappe.set_user("Administrator")
    if not frappe.db.exists("DocType", DT):
        print("[setup_stage_immersion] DocType absent (migrate d'abord) — skip.")
        return {"status": "skip-no-doctype"}
    _ensure_masters()
    _ensure_workflow()
    frappe.db.commit()
    print("[setup_stage_immersion] Flux Stage Immersion KYA OK.")
    return {"status": "ok"}


run = execute

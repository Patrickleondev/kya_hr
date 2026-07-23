# -*- coding: utf-8 -*-
"""Phase 1 RH — Documents dynamiques (certificats / attestations) + signature DG.

Installe / garantit (idempotent, AFTER_MIGRATE) :
  • le circuit « Flux Document RH KYA » : Brouillon → (RH) En attente DG →
    (DG) Signé, avec Rejeter/Reprendre ;
  • les Workflow State / Action Master requis ;
  • les valeurs par défaut du Single « Signature Direction KYA ».

Les DocTypes (Document RH KYA, Signature Direction KYA) et le Print Format
« Document RH KYA » sont standard (custom=0) → synchronisés par `bench migrate`.
"""
from __future__ import annotations

import frappe

WF = "Flux Document RH KYA"
DT = "Document RH KYA"

STATES = [
    ("Brouillon", 0, ""),
    ("En attente DG", 0, "Warning"),
    ("Signé", 1, "Success"),
    ("Rejeté", 1, "Danger"),
]

RH_ROLES = ["Responsable RH", "HR Manager", "HR User", "System Manager"]
DG_ROLES = ["Directeur Général", "DGA", "System Manager"]

# (state, action, next_state, [roles], allow_self_approval)
TRANSITIONS = [
    ("Brouillon", "Soumettre au DG", "En attente DG", RH_ROLES, 1),
    ("En attente DG", "Signer", "Signé", DG_ROLES, 1),
    ("En attente DG", "Rejeter", "Rejeté", DG_ROLES, 1),
    ("Rejeté", "Reprendre", "Brouillon", RH_ROLES, 1),
]


def _ensure_state_masters():
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
            doc.append("transitions", {
                "state": state, "action": action, "next_state": nxt,
                "allowed": role, "allow_self_approval": sa,
            })
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)


def _ensure_signature_single():
    """Valeurs par défaut du signataire (sans écraser une signature déjà posée)."""
    try:
        single = frappe.get_single("Signature Direction KYA")
    except Exception:
        return
    changed = False
    if not single.signataire_nom:
        single.signataire_nom = "Prof. Yao Kétowoglo AZOUMAH"; changed = True
    if not single.signataire_titre:
        single.signataire_titre = "Directeur Général"; changed = True
    if changed:
        single.flags.ignore_permissions = True
        single.save(ignore_permissions=True)


def execute():
    frappe.set_user("Administrator")
    if not frappe.db.exists("DocType", DT):
        print("[setup_documents_rh] DocType absent (migrate d'abord) — skip.")
        return {"status": "skip-no-doctype"}
    _ensure_state_masters()
    _ensure_workflow()
    _ensure_signature_single()
    frappe.db.commit()
    print("[setup_documents_rh] circuit + états + signataire OK.")
    return {"status": "ok"}


run = execute

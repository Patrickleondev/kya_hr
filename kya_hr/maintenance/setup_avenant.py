# -*- coding: utf-8 -*-
"""Circuit de l'avenant au contrat — Flux Avenant KYA.

Comme le contrat (KYA Contrat), l'avenant se signe EN LIGNE : la RH envoie un
lien à l'employé(e), qui confirme son identité (téléphone), lit le document et
signe « lu et approuvé » de son côté ; la RH le transmet ensuite au DG qui
co-signe. Un repli « sans e-mail » permet la signature papier (l'employé n'a pas
d'adresse) : la RH imprime, fait signer à la main, puis soumet directement au DG.

    Brouillon
      ├─(RH: Envoyer au salarié)──▶ En attente Signature Salarié
      │                                 └─(salarié via lien token)──▶ Signé Salarié
      │                                            └─(RH: Soumettre au DG)──▶ En attente DG
      └─(RH: Soumettre au DG — sans portail)──────────────────────────────▶ En attente DG
                                                   └─(DG: Signer)──▶ Signé
                                                   └─(DG: Rejeter)─▶ Rejeté ─(RH: Reprendre)─▶ Brouillon

Idempotent, AFTER_MIGRATE. Ne crée que le Workflow propre au DocType.
"""
import frappe

WF = "Flux Avenant KYA"
DT = "Avenant Contrat KYA"

STATES = [
    ("Brouillon", 0, ""),
    ("En attente Signature Salarié", 0, "Warning"),
    ("Signé Salarié", 0, "Info"),
    ("En attente DG", 0, "Warning"),
    ("Signé", 1, "Success"),
    ("Rejeté", 1, "Danger"),
]
RH_ROLES = ["Responsable RH", "HR Manager", "HR User", "System Manager"]
DG_ROLES = ["Directeur Général", "DGA", "System Manager"]
# Le passage 'En attente Signature Salarié' → 'Signé Salarié' est déclenché par le
# salarié via le portail token (l'API s'élève en Administrator). Frappe valide
# malgré tout le graphe des transitions : on DOIT donc déclarer cette transition,
# autorisée à System Manager (rôle que possède l'Administrator élevé).
TRANSITIONS = [
    ("Brouillon", "Envoyer au salarié", "En attente Signature Salarié", RH_ROLES, 1),
    ("Brouillon", "Soumettre au DG (sans portail)", "En attente DG", RH_ROLES, 1),
    ("En attente Signature Salarié", "Signer (salarié)", "Signé Salarié", ["System Manager"], 1),
    ("En attente Signature Salarié", "Reprendre", "Brouillon", RH_ROLES, 1),
    ("Signé Salarié", "Soumettre au DG", "En attente DG", RH_ROLES, 1),
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
    # États côté RH (rédaction / relecture avant DG) : éditables par la RH.
    # États côté DG (attente co-signature / signé) : édition réservée au DG.
    RH_EDIT_STATES = ("Brouillon", "Rejeté", "En attente Signature Salarié", "Signé Salarié")
    doc.set("states", [])
    for name, ds, style in STATES:
        doc.append("states", {"state": name, "doc_status": ds, "style": style,
                              "allow_edit": "Responsable RH" if name in RH_EDIT_STATES else "Directeur Général"})
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
        print("[setup_avenant] DocType absent (migrate d'abord) — skip.")
        return {"status": "skip-no-doctype"}
    _ensure_masters()
    _ensure_workflow()
    frappe.db.commit()
    print("[setup_avenant] Flux Avenant KYA OK.")
    return {"status": "ok"}


run = execute

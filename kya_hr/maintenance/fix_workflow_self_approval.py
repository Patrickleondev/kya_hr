# -*- coding: utf-8 -*-
"""Corrige le self-approval des transitions de SOUMISSION (créateur).

BUG détecté par le harnais multi-rôles : les transitions de PREMIÈRE
soumission portaient `allow_self_approval = 0`. Or l'auteur d'une fiche en est
le `owner` (web form = soumission par l'utilisateur connecté). Frappe bloque
alors « Self approval is not allowed » : un caissier ne pouvait PAS soumettre
son propre brouillard, un comptable son propre état de chèques, un employé sa
propre permission de sortie, etc.

RÈGLE (sûre) : une transition partant de l'ÉTAT INITIAL du workflow (ou de
« Rejeté » = re-soumission) est toujours « l'auteur qui soumet sa fiche » →
`allow_self_approval = 1`. Les étapes d'APPROBATION (Viser/Valider/Approuver…)
ne partent jamais de l'état initial : elles gardent `0` (séparation des tâches).

Idempotent. Wrappé dans safe_migrations.AFTER_MIGRATE (réappliqué après
l'import du fixture workflow.json qui, lui, garde les valeurs d'origine).
"""
from __future__ import annotations

import frappe

# états depuis lesquels une transition = (re)soumission par l'auteur
SUBMIT_FROM_STATES_EXTRA = {"Rejeté"}


def execute() -> dict:
    fixed = []
    for wf in frappe.get_all("Workflow", filters={"is_active": 1}, pluck="name"):
        init = frappe.db.get_value(
            "Workflow Document State", {"parent": wf}, "state", order_by="idx asc")
        if not init:
            continue
        from_states = {init} | SUBMIT_FROM_STATES_EXTRA
        rows = frappe.get_all(
            "Workflow Transition",
            filters={"parent": wf, "state": ["in", list(from_states)], "allow_self_approval": 0},
            fields=["name", "state", "action", "allowed"],
        )
        for t in rows:
            frappe.db.set_value("Workflow Transition", t.name,
                                "allow_self_approval", 1, update_modified=False)
            fixed.append("%s | %s --%s--> [%s]" % (wf, t.state, t.action, t.allowed))

    if fixed:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workflow")
    print("[fix_workflow_self_approval] %d transition(s) corrigée(s)" % len(fixed))
    for f in fixed:
        print("   +", f)
    return {"fixed": fixed, "count": len(fixed)}

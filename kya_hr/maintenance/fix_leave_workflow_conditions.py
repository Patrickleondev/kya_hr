# -*- coding: utf-8 -*-
"""Corrige les conditions de transition du workflow « Flux RH Unifié »
(Leave Application) qui faisaient PLANTER toute soumission de congé.

BUG : les conditions utilisaient `frappe.get_roles(...)`. Or l'évaluateur des
conditions de workflow (`frappe.model.workflow.get_workflow_safe_globals`)
n'expose QUE `frappe.db.get_value`, `frappe.db.get_list`, `frappe.session` et
quelques utils — PAS `frappe.get_roles`. Comme `frappe` y est un `_dict`,
`frappe.get_roles` vaut None → `None(...)` → « 'NoneType' object is not
callable » à chaque insert/submit d'une Leave Application (donc « Congé pris »
du dashboard /gestion-conges tournait sans fin / échouait).

FIX : remplacer par un test d'existence du rôle via `frappe.db.get_list` sur
« Has Role » (autorisé en safe-eval). Logique inchangée : si l'utilisateur lié
à l'employé a le rôle « Supérieur Immédiat » → l'aiguillage saute directement à
« En attente RH », sinon → « En attente du Supérieur Immédiat ».

Idempotent. Wrappé dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe

_HAS_SUP = (
    "frappe.db.get_list('Has Role', filters={'parenttype': 'User', "
    "'parent': frappe.db.get_value('Employee', doc.employee, 'user_id') or '__none__', "
    "'role': 'Supérieur Immédiat'}, limit=1)"
)

# next_state -> nouvelle condition (safe-eval)
_NEW_CONDITION = {
    "En attente RH": _HAS_SUP,
    "En attente du Supérieur Immédiat": "not " + _HAS_SUP,
}


def execute() -> dict:
    fixed = []
    rows = frappe.get_all(
        "Workflow Transition",
        filters={"condition": ["like", "%get_roles%"]},
        fields=["name", "parent", "next_state", "condition"],
    )
    for r in rows:
        new = _NEW_CONDITION.get(r.next_state)
        if new and new != r.condition:
            frappe.db.set_value("Workflow Transition", r.name, "condition", new,
                                update_modified=False)
            fixed.append("%s --> %s" % (r.parent, r.next_state))

    if fixed:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workflow")
    print("[fix_leave_workflow_conditions] %d condition(s) corrigée(s)" % len(fixed))
    return {"fixed": fixed}

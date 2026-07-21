# -*- coding: utf-8 -*-
"""Garantit qu'un « Workflow Action Master » existe pour CHAQUE action de
transition des workflows actifs.

PIÈGE RÉCURRENT (retour prod 07/2026, erreur UI « Impossible de trouver
Ligne #N: Action: … » au save d'un Workflow). Frappe valide, à
l'enregistrement d'un Workflow, que chaque `action` de transition possède une
fiche `Workflow Action Master` du même nom. Nos workflows ont été insérés par
fixtures/scripts SANS créer ces masters → au moindre ré-enregistrement du
workflow dans l'UI (ex. ajouter un rôle), le save échoue.

Ex. concret : « Soumettre au DFC » (flux État Récap Chèques) n'avait pas de
master → impossible d'ajouter le rôle Caissier à la transition.

Ce module (idempotent, AFTER_MIGRATE) crée les masters manquants. Il lit les
actions réellement utilisées par les Workflow Transition, donc couvre TOUS les
workflows (kya_hr, kya_services, natifs), pas seulement l'État Récap.
"""
from __future__ import annotations

import frappe


def execute() -> dict:
    res = {"scanned": 0, "created": [], "existants": 0}
    try:
        # Actions réellement référencées par les transitions des workflows actifs.
        actions = frappe.db.sql(
            """SELECT DISTINCT wt.action
               FROM `tabWorkflow Transition` wt
               JOIN `tabWorkflow` wf ON wf.name = wt.parent
               WHERE wf.is_active = 1
                 AND IFNULL(wt.action, '') != ''""",
            pluck=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ensure_workflow_action_masters")
        return res

    for action in actions:
        res["scanned"] += 1
        # exists() de Frappe est insensible à la casse sur MariaDB (_ci) —
        # cohérent avec la validation du Workflow, on ne recrée pas les doublons
        # de casse (« valider » vs « Valider »).
        if frappe.db.exists("Workflow Action Master", action):
            res["existants"] += 1
            continue
        try:
            frappe.get_doc({
                "doctype": "Workflow Action Master",
                "workflow_action_name": action,
            }).insert(ignore_permissions=True, ignore_if_duplicate=True)
            res["created"].append(action)
        except frappe.DuplicateEntryError:
            res["existants"] += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"ensure_workflow_action_masters: {action}")

    frappe.db.commit()
    if res["created"]:
        print("[ensure_workflow_action_masters] créés : %s" % res["created"])
    else:
        print("[ensure_workflow_action_masters] rien à créer (%d actions OK)"
              % res["existants"])
    return res

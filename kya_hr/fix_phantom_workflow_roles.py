"""Remappe les rôles FANTÔMES référencés dans les transitions de workflow.

CONSTAT du diagnostic : le 'Flux PV Entrée Matériel' a deux transitions
(état 'En attente Comptable') dont le rôle autorisé est 'Responsable
Comptable' — un rôle qui N'EXISTE PAS dans le système. Résultat : à
l'étape comptable, le validateur prévu ne peut rien faire (transition
morte, "non autorisé dans le flux").

Stratégie sûre : pour chaque Workflow Transition (workflows actifs) dont
le rôle 'allowed' n'existe pas comme Role, on le remplace par son
équivalent métier réel (table ALIAS), puis on garantit que ce rôle
équivalent a bien read+write(+submit) sur le DocType cible.

Idempotent : si le rôle existe déjà ou n'est pas dans la table d'alias,
on ne touche rien. Wrappé dans safe_migrations.AFTER_MIGRATE AVANT
ensure_workflow_perms (pour que les perms suivent le remap).
"""
from __future__ import annotations

import frappe


# Rôle fantôme -> rôle métier réel équivalent.
# (DAAF = DFC = Responsable Comptable dans l'organisation KYA ; on route
#  'Responsable Comptable' vers 'Comptable' qui existe et porte l'étape.)
ALIAS = {
    "Responsable Comptable": "Comptable",
    "Resp. Comptable": "Comptable",
    "Responsable Logistique": "DST - Responsable Logistique",
    "Responsable Stagiaires": "Responsable des Stagiaires",
    "Resp. Stagiaires": "Responsable des Stagiaires",
}


def _grant_rws(doctype: str, role: str) -> None:
    """read+write(+submit) sur le DocType cible pour le rôle remappé."""
    if not (frappe.db.exists("Role", role) and frappe.db.exists("DocType", doctype)):
        return
    from frappe.permissions import add_permission, update_permission_property
    custom = frappe.db.get_value(
        "Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}, "name")
    try:
        if not custom:
            add_permission(doctype, role, 0)
        update_permission_property(doctype, role, 0, "read", "1")
        update_permission_property(doctype, role, 0, "write", "1")
        update_permission_property(doctype, role, 0, "if_owner", "0")
        if frappe.db.get_value("DocType", doctype, "is_submittable"):
            update_permission_property(doctype, role, 0, "submit", "1")
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(),
                             f"fix_phantom_workflow_roles: grant {doctype}/{role}")
        except Exception:
            pass


def execute() -> dict:
    summary = {"remapped": [], "skipped_unknown": [], "total": 0}

    workflows = frappe.get_all("Workflow", filters={"is_active": 1},
                               fields=["name", "document_type"])
    for wf in workflows:
        dt = wf.document_type
        transitions = frappe.get_all(
            "Workflow Transition", filters={"parent": wf.name},
            fields=["name", "allowed", "state", "action"])
        for t in transitions:
            role = (t.allowed or "").strip()
            if not role or frappe.db.exists("Role", role):
                continue  # rôle OK
            target = ALIAS.get(role)
            if not target or not frappe.db.exists("Role", target):
                summary["skipped_unknown"].append(f"{wf.name}: '{role}'")
                continue
            try:
                frappe.db.set_value("Workflow Transition", t.name, "allowed",
                                    target, update_modified=False)
                _grant_rws(dt, target)
                summary["remapped"].append(
                    f"{wf.name} [{t.state}/{t.action}] '{role}' -> '{target}'")
                summary["total"] += 1
            except Exception:
                try:
                    frappe.log_error(frappe.get_traceback(),
                                     f"fix_phantom_workflow_roles: {wf.name}/{role}")
                except Exception:
                    pass

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[fix_phantom_workflow_roles] remapped={summary['total']} "
          f"unknown={len(summary['skipped_unknown'])}")
    if summary["skipped_unknown"]:
        print(f"  rôles fantômes sans alias : {summary['skipped_unknown']}")
    return summary

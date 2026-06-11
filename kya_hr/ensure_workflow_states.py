"""Blinde le système contre l'erreur "État du Flux de Travail X introuvable".

CONTEXTE (retour terrain) :
- État Récap Chèques  -> "En attente Validation DFC introuvable"
- Permission Sortie Stagiaire -> "En attente Maitre de Stage introuvable"

Cause : Frappe résout chaque état de workflow via un *master* `Workflow State`.
Si un état utilisé (dans un Workflow OU porté par un document existant) n'a pas
son master, l'affichage du document plante avec un 404 "introuvable". Cela arrive
quand :
  * un fixture Workflow State n'a pas été synchronisé sur l'instance, ou
  * un workflow a été renommé (ex. "En attente Maitre de Stage" -> "En attente
    Chef") mais d'anciens documents portent encore l'ancien nom d'état.

Ce module rend le déploiement idempotent et sûr :
  1. Crée TOUT master Workflow State manquant, qu'il soit référencé par un
     Workflow (states/transitions) ou simplement porté par un document existant.
  2. Remappe les anciens états orphelins connus vers leur équivalent courant,
     uniquement si la cible est un état VALIDE du workflow actif (sinon on se
     contente de créer le master, ce qui suffit à empêcher le 404).

Aucune suppression. Re-jouable sans effet de bord.
"""
from __future__ import annotations

import frappe


# Anciens noms d'état -> nom courant. Le remap n'est appliqué que si la cible
# est un état valide du workflow actif du doctype concerné.
KNOWN_RENAMES = {
    "En attente Maitre de Stage": "En attente Chef",
    "En attente Maître de Stage": "En attente Chef",
}


def _style_for(state_name: str) -> str:
    s = (state_name or "").lower()
    # L'ordre compte : "En attente Validation DFC" contient "valid" ET "attente"
    # -> c'est un état d'attente, donc Warning. On teste rejet puis attente AVANT
    # les mots de succès pour éviter les faux positifs.
    if any(k in s for k in ("rejet", "annul", "refus")):
        return "Danger"
    if "attente" in s or "cours" in s:
        return "Warning"
    if any(k in s for k in ("approuv", "valid", "archiv", "terminé", "termine", "clôtur", "clotur")):
        return "Success"
    if "brouillon" in s:
        return "Primary"
    return "Primary"


def _ensure_master(state_name: str, created: list) -> None:
    if not state_name:
        return
    if frappe.db.exists("Workflow State", state_name):
        return
    try:
        doc = frappe.new_doc("Workflow State")
        doc.workflow_state_name = state_name
        doc.style = _style_for(state_name)
        doc.insert(ignore_permissions=True)
        created.append(state_name)
    except frappe.DuplicateEntryError:
        pass
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), f"ensure_workflow_states: {state_name}")
        except Exception:
            pass


def execute() -> dict:
    summary = {"created_masters": [], "remapped_docs": [], "scanned_workflows": 0}

    # ── 1. États référencés par les Workflows (states + transitions) ──
    workflows = frappe.get_all("Workflow", fields=["name", "document_type", "is_active"])
    valid_states_by_doctype: dict[str, set] = {}
    for wf in workflows:
        summary["scanned_workflows"] += 1
        try:
            wdoc = frappe.get_doc("Workflow", wf.name)
        except Exception:
            continue
        states = set()
        for st in (wdoc.states or []):
            if st.state:
                states.add(st.state)
                _ensure_master(st.state, summary["created_masters"])
        for tr in (wdoc.transitions or []):
            for nm in (tr.state, tr.next_state):
                if nm:
                    states.add(nm)
                    _ensure_master(nm, summary["created_masters"])
        if wf.is_active:
            valid_states_by_doctype[wf.document_type] = states

    # ── 2. États portés par des documents existants (catch des orphelins) ──
    # Pour chaque doctype ayant un workflow, on lit les valeurs distinctes de
    # workflow_state réellement présentes en base et on garantit leur master.
    doctypes = {wf.document_type for wf in workflows if wf.document_type}
    for dt in doctypes:
        if not frappe.db.has_column(dt, "workflow_state"):
            continue
        try:
            rows = frappe.db.sql(
                f"SELECT DISTINCT workflow_state FROM `tab{dt}` "
                f"WHERE IFNULL(workflow_state,'') <> ''"
            )
        except Exception:
            continue
        for (state_value,) in rows:
            _ensure_master(state_value, summary["created_masters"])
            # Remap connu si l'état porté n'est plus valide mais a un équivalent
            if (state_value in KNOWN_RENAMES
                    and state_value not in valid_states_by_doctype.get(dt, set())):
                target = KNOWN_RENAMES[state_value]
                if target in valid_states_by_doctype.get(dt, set()):
                    try:
                        n = frappe.db.sql(
                            f"UPDATE `tab{dt}` SET workflow_state=%s WHERE workflow_state=%s",
                            (target, state_value),
                        )
                        frappe.db.commit()
                        summary["remapped_docs"].append(f"{dt}: {state_value} -> {target}")
                    except Exception:
                        frappe.log_error(frappe.get_traceback(),
                                         f"ensure_workflow_states remap {dt}")

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[ensure_workflow_states] workflows={summary['scanned_workflows']} "
          f"masters_crees={len(summary['created_masters'])} "
          f"docs_remappes={len(summary['remapped_docs'])}")
    if summary["created_masters"]:
        print("  + " + " | ".join(summary["created_masters"]))
    if summary["remapped_docs"]:
        print("  ~ " + " | ".join(summary["remapped_docs"]))
    return summary

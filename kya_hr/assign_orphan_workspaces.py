# -*- coding: utf-8 -*-
"""Donne un workspace d'accueil aux DocTypes KYA HR "orphelins".

PROBLEME : un DocType du module KYA HR qui n'a AUCUN `Workspace Link` retombe,
côté Desk v16, dans le workspace de plus basse séquence du module — ici
'Espace Stagiaires' (sequence_id 5.0). Résultat : des fiches Direction / RH /
Stock (Visites, Réunions, Formation, Équipes, Retours matériel...) polluaient
la barre latérale des stagiaires.

FIX : on garantit qu'à chaque orphelin correspond AU MOINS un Workspace Link
dans le workspace métier logique. Dès qu'un lien curaté existe, le DocType
quitte le fallback 'Espace Stagiaires'.

Insertion DIRECTE des child rows (Workspace Link), comme
`ensure_workspace_roles` le fait pour 'Has Role' : on évite le save() complet
du Workspace qui re-valide toutes les lignes (et plante sur d'anciennes lignes
douteuses). Idempotent.

Les workspaces KYA sont is_standard (rechargés depuis le JSON à chaque
migrate, ce qui efface les liens ajoutés en base) : ce script est donc wrappé
dans safe_migrations.AFTER_MIGRATE et re-applique les liens après chaque
migration.
"""
from __future__ import annotations

import frappe


# workspace cible -> (libellé de la carte, [DocTypes])
ASSIGNMENTS: dict[str, tuple[str, list[str]]] = {
    "Espace RH": (
        "Formation & Organisation",
        [
            "Besoin de Formation",
            "Plan de Formation",
            "Equipe KYA",
            "KYA Contract Template",
            "KYA Import RH",
        ],
    ),
    "Direction Generale": (
        "Réunions, Visites & Pilotage",
        [
            "KYA Guest Visit",
            "KYA Indicator",
        ],
    ),
    "Espace Stock": (
        "Mouvements & Retours",
        [
            "Retour Materiel KYA",
            # Doctypes maison du stock : sinon ils retombent dans le fallback
            # « Espace Stagiaires » (plus basse séquence du module KYA HR).
            "Article KYA",
            "Categorie Article KYA",
            "Saisie Stock KYA",
            "Client KYA",
            "Projet KYA",
            "Mouvement Stock KYA",
        ],
    ),
}


def _next_idx(ws_name: str) -> int:
    mx = frappe.db.sql(
        "SELECT COALESCE(MAX(idx), 0) FROM `tabWorkspace Link` WHERE parent=%s",
        (ws_name,),
    )[0][0]
    return (mx or 0) + 1


def _ensure_card_break(ws_name: str, label: str) -> bool:
    """Garantit un 'Card Break' (en-tête de carte) dans le workspace."""
    if frappe.db.exists("Workspace Link", {
        "parent": ws_name, "type": "Card Break", "label": label,
    }):
        return False
    row = frappe.new_doc("Workspace Link")
    row.parent = ws_name
    row.parenttype = "Workspace"
    row.parentfield = "links"
    row.idx = _next_idx(ws_name)
    row.type = "Card Break"
    row.label = label
    row.link_type = "DocType"
    row.hidden = 0
    row.onboard = 0
    row.insert(ignore_permissions=True)
    return True


def _ensure_link(ws_name: str, doctype: str) -> bool:
    """Garantit un 'Link' vers `doctype` dans le workspace."""
    if frappe.db.exists("Workspace Link", {
        "parent": ws_name, "type": "Link", "link_to": doctype,
    }):
        return False
    row = frappe.new_doc("Workspace Link")
    row.parent = ws_name
    row.parenttype = "Workspace"
    row.parentfield = "links"
    row.idx = _next_idx(ws_name)
    row.type = "Link"
    row.label = doctype
    row.link_to = doctype
    row.link_type = "DocType"
    row.hidden = 0
    row.onboard = 0
    row.insert(ignore_permissions=True)
    return True


def execute() -> dict:
    summary = {"added_breaks": [], "added_links": [], "skipped": []}

    for ws_name, (card_label, doctypes) in ASSIGNMENTS.items():
        if not frappe.db.exists("Workspace", ws_name):
            summary["skipped"].append(f"workspace absent: {ws_name}")
            continue

        break_made = False
        for dt in doctypes:
            if not frappe.db.exists("DocType", dt):
                summary["skipped"].append(f"doctype absent: {dt}")
                continue
            # carte créée à la demande (seulement si au moins un DocType existe)
            if not break_made:
                if _ensure_card_break(ws_name, card_label):
                    summary["added_breaks"].append(f"{ws_name} / {card_label}")
                break_made = True
            if _ensure_link(ws_name, dt):
                summary["added_links"].append(f"{ws_name} <- {dt}")

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
        frappe.clear_cache(doctype="Workspace Link")
    except Exception:
        pass

    print(f"[assign_orphan_workspaces] +{len(summary['added_links'])} liens, "
          f"+{len(summary['added_breaks'])} cartes")
    return summary

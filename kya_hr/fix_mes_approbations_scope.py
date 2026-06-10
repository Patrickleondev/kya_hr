"""Purge les shortcuts 'Mes Approbations' / 'A valider' des espaces metier mutualises.

Architecture KYA :
- Les espaces metier (Espace RH, Espace Achats, Espace Stock, Espace
  Comptabilite) sont MUTUALISES : toute l'equipe metier les voit. Ils
  doivent montrer des donnees collectives, pas personnelles.
- L'espace personnel = Espace Employes (vu uniquement par le user
  connecte).

Bug : un shortcut 'A valider (mes approbations)' avait ete ajoute aux
workspaces metier. Resultat : un membre de l'equipe Stock voyait les
approbations de SON chef (et inversement). C'est une fuite + une
incoherence (Mes = personnel).

Fix : supprime tous les Workspace Shortcut dont le label evoque les
approbations personnelles ('mes approbations', 'a valider', 'mes
validations') dans les workspaces metier. Les fixtures JSON sont aussi
nettoyees en parallele pour empecher la re-creation au prochain sync.

Idempotent. Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


# Workspaces mutualises ou les approbations personnelles ne devraient PAS apparaitre.
COLLECTIVE_WORKSPACES = (
    "Espace RH",
    "Espace Achats",
    "Espace Stock",
    "Espace Comptabilité",
    "Espace Comptabilite",
    "Espace Direction",
)

# Labels qui denotent un widget personnel (a purger des workspaces collectifs).
PERSONAL_LABEL_PATTERNS = (
    "mes approbations",
    "à valider (mes",
    "a valider (mes",
    "mes validations",
    "ma to-do",
    "mes taches a valider",
    "mes tâches à valider",
)


def _label_is_personal(label: str) -> bool:
    if not label:
        return False
    norm = label.lower().strip()
    return any(p in norm for p in PERSONAL_LABEL_PATTERNS)


def execute() -> dict:
    summary = {"shortcuts_deleted": [], "workspaces_scanned": 0, "errors": []}

    for ws_name in COLLECTIVE_WORKSPACES:
        if not frappe.db.exists("Workspace", ws_name):
            continue
        summary["workspaces_scanned"] += 1

        shortcuts = frappe.db.get_all(
            "Workspace Shortcut",
            filters={"parent": ws_name},
            fields=["name", "label", "url", "link_to"],
        )
        for sc in shortcuts:
            if not _label_is_personal(sc.label):
                continue
            try:
                frappe.delete_doc(
                    "Workspace Shortcut", sc.name,
                    force=1, ignore_permissions=True,
                )
                summary["shortcuts_deleted"].append({
                    "workspace": ws_name,
                    "shortcut": sc.name,
                    "label": sc.label,
                })
            except Exception as exc:
                summary["errors"].append({
                    "workspace": ws_name,
                    "shortcut": sc.name,
                    "error": str(exc),
                })
                try:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"fix_mes_approbations: {ws_name}/{sc.name}",
                    )
                except Exception:
                    pass

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
        frappe.clear_cache(doctype="Workspace Shortcut")
    except Exception:
        pass

    print(f"[fix_mes_approbations_scope] {summary}")
    return summary

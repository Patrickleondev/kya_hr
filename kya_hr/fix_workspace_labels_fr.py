"""Ajoute les accents francais aux labels des workspaces KYA.

Bug : les workspaces 'Espace Comptabilite', 'Espace Employes',
'Espace Stagiaires' et 'Direction Generale' s'affichent sans accents
dans la sidebar Frappe -> ergonomie/orthographe.

Le 'name' du Workspace est la PK et ne doit pas etre modifie (clé
de foreign key dans tabWorkspace Link.parent, etc.). On modifie
uniquement le 'label' qui est ce qui apparait dans l'UI.

Mapping name -> label francais correct :
- Espace Comptabilite -> Espace Comptabilité
- Espace Employes -> Espace Employés
- Espace Stagiaires -> Espace Stagiaires (deja OK)
- Direction Generale -> Direction Générale
- Logistique -> Logistique (deja OK)

Idempotent. Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


KYA_WORKSPACE_LABELS: dict[str, str] = {
    "Espace Comptabilite": "Espace Comptabilité",
    "Espace Employes": "Espace Employés",
    "Espace Stagiaires": "Espace Stagiaires",
    "Direction Generale": "Direction Générale",
    "Espace RH": "Espace RH",
    "Espace Achats": "Espace Achats",
    "Espace Stock": "Espace Stock",
    "Logistique": "Logistique",
}


def execute() -> dict:
    summary = {"updated": [], "unchanged": [], "missing": []}

    for name, fr_label in KYA_WORKSPACE_LABELS.items():
        if not frappe.db.exists("Workspace", name):
            summary["missing"].append(name)
            continue
        current = frappe.db.get_value("Workspace", name, "label")
        if current == fr_label:
            summary["unchanged"].append(name)
            continue
        try:
            frappe.db.set_value(
                "Workspace", name, "label", fr_label,
                update_modified=False,
            )
            summary["updated"].append({"name": name, "from": current, "to": fr_label})
        except Exception:
            try:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"fix_workspace_labels_fr: {name}",
                )
            except Exception:
                pass

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass

    print(f"[fix_workspace_labels_fr] {summary}")
    return summary

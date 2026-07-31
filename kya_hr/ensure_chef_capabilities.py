"""Aligne les capacités des rôles "chef" (Chef Service = Chef d'Équipe = Chef Equipe).

CONSTAT : les capacités d'un chef sont éclatées sur 3 rôles :
- 'Chef Service'  : approbateur des workflows (Demande Achat, Permission, PV)
  MAIS ne peut PAS créer/assigner de tâches d'équipe.
- 'Chef Equipe'   : peut créer/assigner Tache Equipe + Plan Trimestriel
  MAIS n'est pas l'approbateur des workflows métier.
- "Chef d'Équipe" : quasi vide (doublon orthographique).

Métier (confirmé) : ces 3 désignent LE MÊME rôle "chef" qui doit pouvoir
À LA FOIS approuver SES workflows ET assigner des tâches + voir le
dashboard équipe. Plutôt qu'une fusion destructive (risquée en migration),
on ALIGNE les capacités : chacun des 3 rôles reçoit read+write+create sur
les DocTypes de gestion d'équipe. Résultat : peu importe l'orthographe du
rôle porté par l'employé, le chef a tout ce qu'il lui faut.

Idempotent. Wrappé dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe

CHEF_ROLES = ["Chef Service", "Chef Equipe", "Chef d'Équipe"]

# DocTypes de gestion d'équipe : un chef doit pouvoir créer/éditer.
TEAM_DOCTYPES = ["Tache Equipe", "Plan Trimestriel", "Equipe KYA"]


def _sanitize_stale_import_flag(doctype: str) -> None:
    """Corrige un import=1 orphelin sur une permission existante du doctype.

    Frappe revalide TOUTES les lignes DocPerm/Custom DocPerm du doctype des
    qu'on modifie UNE propriete (validate_permissions -> check_if_importable).
    Si une ligne historique (ex: System Manager) porte import=1 sur un
    doctype qui n'autorise pas l'import (allow_import=0, cas frequent pour
    un custom=1), TOUT update_permission_property plante -> bloque
    definitivement l'alignement des roles chef. On desactive ce flag orphelin
    directement en base (bypass validation, pas de risque : on ne fait que
    corriger une incoherence pre-existante, jamais de vraie fonctionnalite
    d'import utilisee ici)."""
    meta_allow_import = frappe.db.get_value("DocType", doctype, "allow_import")
    if meta_allow_import:
        return
    for dt in ("Custom DocPerm", "DocPerm"):
        rows = frappe.get_all(dt, filters={"parent": doctype, "import": 1}, pluck="name")
        for name in rows:
            frappe.db.set_value(dt, name, "import", 0, update_modified=False)


def _ensure_perm(doctype: str, role: str) -> str:
    if not (frappe.db.exists("Role", role) and frappe.db.exists("DocType", doctype)):
        return "skip"
    _sanitize_stale_import_flag(doctype)
    from frappe.permissions import add_permission, update_permission_property

    has_custom = frappe.db.exists("Custom DocPerm",
                                  {"parent": doctype, "role": role, "permlevel": 0})
    cur = frappe.db.get_value(
        "Custom DocPerm" if has_custom else "DocPerm",
        {"parent": doctype, "role": role, "permlevel": 0},
        ["read", "write", "create"], as_dict=True,
    )
    if cur and cur.read and cur.write and cur.create:
        return "unchanged"
    try:
        if not has_custom:
            add_permission(doctype, role, 0)
        update_permission_property(doctype, role, 0, "read", "1")
        update_permission_property(doctype, role, 0, "write", "1")
        update_permission_property(doctype, role, 0, "create", "1")
        return "updated"
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(),
                             f"ensure_chef_capabilities: {doctype}/{role}")
        except Exception:
            pass
        return "error"


def execute() -> dict:
    summary = {"updated": 0, "unchanged": 0, "skip": 0, "error": 0, "details": []}
    for doctype in TEAM_DOCTYPES:
        for role in CHEF_ROLES:
            action = _ensure_perm(doctype, role)
            summary[action] = summary.get(action, 0) + 1
            if action in ("updated",):
                summary["details"].append(f"{doctype} <- {role}")
    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass
    print(f"[ensure_chef_capabilities] updated={summary['updated']} "
          f"unchanged={summary['unchanged']} {summary['details']}")
    return summary

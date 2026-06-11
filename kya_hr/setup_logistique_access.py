"""Accès Logistique : Sortie Véhicule visible par la Direction + visibilité
de l'espace Logistique pour les vrais rôles logistiques.

CONSTAT du diagnostic (system_diagnostic.run) :
- 'Sortie Vehicule' : seuls Employee / System Manager / Gestionnaire de
  Flotte ont des droits. Le DG et le DGA n'ont AUCUNE perm -> ils ne
  peuvent ni voir ni tracer les sorties de véhicules. Or le besoin métier
  (confirmé) est : PAS de workflow, mais la Direction (DG + DGA) TRACE et
  VOIT toutes les sorties.
- Workspace 'Logistique' : n'expose que Chef Service / DGA / DG / SysMgr.
  Ni 'Gestionnaire de Flotte' ni 'DST - Responsable Logistique' n'y sont
  -> un logisticien se connecte et ne voit "rien".

Ce module (idempotent, sans danger) :
1. Donne READ (lecture seule) sur 'Sortie Vehicule' à la Direction et aux
   rôles logistiques, via Custom DocPerm (add_permission +
   update_permission_property), SANS toucher la classe DocType standard
   (évite CannotCreateStandardDoctypeError en prod).
2. Ajoute les rôles logistiques au workspace 'Logistique'.

Wrappé dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


# Sortie Véhicule : qui peut VOIR / TRACER (lecture seule, pas de workflow).
SORTIE_VEHICULE_VIEWERS = [
    "Directeur Général", "DGA", "DG", "DAAF",
    "Gestionnaire de Flotte", "DST - Responsable Logistique", "Chef Service",
]

# Rôles à exposer sur l'espace Logistique (en plus de ceux déjà présents).
LOGISTIQUE_WORKSPACE_ROLES = [
    "Gestionnaire de Flotte", "DST - Responsable Logistique",
    "Directeur Général", "DGA", "DG", "System Manager",
]


def _ensure_read_perm(doctype: str, role: str) -> str:
    """Garantit au minimum read=1 (lecture seule) pour un rôle via Custom DocPerm."""
    if not frappe.db.exists("Role", role):
        return "role_missing"
    if not frappe.db.exists("DocType", doctype):
        return "doctype_missing"

    from frappe.permissions import add_permission, update_permission_property

    custom = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": doctype, "role": role, "permlevel": 0},
        ["name", "read"], as_dict=True,
    )
    std = frappe.db.get_value(
        "DocPerm",
        {"parent": doctype, "role": role, "permlevel": 0},
        ["read"], as_dict=True,
    )
    if (custom and custom.read) or (std and std.read):
        return "unchanged"

    try:
        if not custom:
            add_permission(doctype, role, 0)
        update_permission_property(doctype, role, 0, "read", "1")
        return "created" if not custom else "updated"
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(),
                             f"setup_logistique_access: {doctype}/{role}")
        except Exception:
            pass
        return "error"


def _add_role_to_workspace(ws_name: str, role: str) -> bool:
    if not frappe.db.exists("Role", role):
        return False
    if not frappe.db.exists("Workspace", ws_name):
        return False
    if frappe.db.exists("Has Role", {
        "parent": ws_name, "parenttype": "Workspace", "role": role,
    }):
        return False
    try:
        hr = frappe.new_doc("Has Role")
        hr.parent = ws_name
        hr.parenttype = "Workspace"
        hr.parentfield = "roles"
        hr.role = role
        hr.insert(ignore_permissions=True)
        return True
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(),
                             f"setup_logistique_access: ws {ws_name}/{role}")
        except Exception:
            pass
        return False


def execute() -> dict:
    summary = {"sortie_vehicule": {}, "workspace_roles_added": [],
               "total_perms": 0, "total_ws": 0}

    # 1. Sortie Véhicule : lecture pour la Direction + logistique
    for role in SORTIE_VEHICULE_VIEWERS:
        action = _ensure_read_perm("Sortie Vehicule", role)
        summary["sortie_vehicule"][role] = action
        if action in ("created", "updated"):
            summary["total_perms"] += 1

    # 2. Visibilité de l'espace Logistique
    for role in LOGISTIQUE_WORKSPACE_ROLES:
        if _add_role_to_workspace("Logistique", role):
            summary["workspace_roles_added"].append(role)
            summary["total_ws"] += 1

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[setup_logistique_access] perms_sortie_vehicule={summary['total_perms']} "
          f"ws_roles_added={summary['total_ws']} {summary['workspace_roles_added']}")
    return summary

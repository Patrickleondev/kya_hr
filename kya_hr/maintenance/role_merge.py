# -*- coding: utf-8 -*-
"""Migration des rôles KYA — fusion des doublons.

Fusionne plusieurs rôles vers un rôle canonique en :
1. Migrant les Users (`tabHas Role`)
2. Migrant les permissions DocType (`tabDocPerm` et `tabCustom DocPerm`)
3. Migrant les références dans Workflow Transition et Workflow Document State
4. Migrant les Notification Recipients (`receiver_by_role`)
5. Supprimant l'ancien rôle

Usage CLI :
    bench --site frontend execute kya_hr.maintenance.role_merge.run_dry_run
    bench --site frontend execute kya_hr.maintenance.role_merge.run_migrations

Migrations actives (décidées avec le métier) :
- Chef d'Équipe        → Chef Equipe   (sans apostrophe, plus utilisé)
- DG                   → Directeur Général
- DAAF                 → Responsable Comptable  (créé si absent)
- DFC                  → Responsable Comptable
"""
import frappe


KYA_ROLE_MIGRATIONS = [
    # (old, new, create_new_if_missing)
    ("Chef d'Équipe", "Chef Equipe", False),
    ("DG", "Directeur Général", False),
    ("DAAF", "Responsable Comptable", True),
    ("DFC", "Responsable Comptable", True),
]


def _audit_old_role(old: str) -> dict:
    """Compte toutes les références à un rôle existant.

    Couvre Has Role pour tous les parenttypes (User, Employee, Workspace, Report, ...),
    DocPerm, Custom DocPerm, Workflow Transition/State et Notification Recipient.
    """
    if not frappe.db.exists("Role", old):
        return {"exists": False}
    return {
        "exists": True,
        "users": frappe.db.sql_list(
            "SELECT parent FROM `tabHas Role` WHERE role=%s AND parenttype='User'",
            old,
        ),
        "employees": frappe.db.sql_list(
            "SELECT parent FROM `tabHas Role` WHERE role=%s AND parenttype='Employee'",
            old,
        ),
        # Toutes les autres affectations Has Role (Workspace, Report, etc.)
        "has_role_other": frappe.db.sql(
            "SELECT name, parent, parenttype, parentfield "
            "FROM `tabHas Role` WHERE role=%s AND parenttype NOT IN ('User','Employee')",
            old, as_dict=True,
        ),
        "docperms": frappe.db.sql(
            "SELECT name, parent, permlevel FROM `tabDocPerm` WHERE role=%s",
            old, as_dict=True,
        ),
        "custom_docperms": frappe.db.sql(
            "SELECT name, parent, permlevel FROM `tabCustom DocPerm` WHERE role=%s",
            old, as_dict=True,
        ),
        "wf_transitions": frappe.db.sql(
            "SELECT name, parent, state, action FROM `tabWorkflow Transition` WHERE allowed=%s",
            old, as_dict=True,
        ),
        "wf_states": frappe.db.sql(
            "SELECT name, parent, state FROM `tabWorkflow Document State` WHERE allow_edit=%s",
            old, as_dict=True,
        ),
        "notif_recipients": frappe.db.sql(
            "SELECT name, parent FROM `tabNotification Recipient` WHERE receiver_by_role=%s",
            old, as_dict=True,
        ),
    }


def _ensure_role(name: str, dry_run: bool) -> bool:
    """Crée le rôle s'il n'existe pas. Retourne True si déjà présent ou créé."""
    if frappe.db.exists("Role", name):
        return True
    if dry_run:
        print(f"  [DRY-RUN] Créerait le rôle: {name}")
        return False
    role = frappe.new_doc("Role")
    role.role_name = name
    role.desk_access = 1
    role.insert(ignore_permissions=True)
    print(f"  → Rôle créé: {name}")
    return True


def _migrate_users(old: str, new: str, audit: dict, dry_run: bool) -> int:
    """Pour chaque User ayant old, lui ajouter new (s'il ne l'a pas) puis retirer old."""
    n = 0
    for user in audit["users"]:
        has_new = frappe.db.exists("Has Role", {"parent": user, "role": new, "parenttype": "User"})
        action = "remove_old"
        if not has_new:
            action = "add_new+remove_old"
        if dry_run:
            print(f"  [DRY-RUN] User {user}: {action}")
        else:
            if not has_new:
                hr = frappe.new_doc("Has Role")
                hr.parent = user
                hr.parenttype = "User"
                hr.parentfield = "roles"
                hr.role = new
                hr.insert(ignore_permissions=True)
            frappe.db.sql(
                "DELETE FROM `tabHas Role` WHERE parent=%s AND role=%s AND parenttype='User'",
                (user, old),
            )
        n += 1
    return n


def _migrate_docperms(old: str, new: str, audit: dict, dry_run: bool) -> int:
    """Migrer DocPerm: éviter les doublons (parent, permlevel, role)."""
    n = 0
    for perm in audit["docperms"]:
        exists_new = frappe.db.exists("DocPerm", {
            "parent": perm.parent, "permlevel": perm.permlevel, "role": new,
        })
        if dry_run:
            mode = "delete (dup)" if exists_new else "rename"
            print(f"  [DRY-RUN] DocPerm {perm.name} ({perm.parent} permlevel={perm.permlevel}): {mode}")
        else:
            if exists_new:
                frappe.db.sql("DELETE FROM `tabDocPerm` WHERE name=%s", perm.name)
            else:
                frappe.db.sql("UPDATE `tabDocPerm` SET role=%s WHERE name=%s", (new, perm.name))
        n += 1
    return n


def _migrate_custom_docperms(old: str, new: str, audit: dict, dry_run: bool) -> int:
    n = 0
    for perm in audit["custom_docperms"]:
        exists_new = frappe.db.exists("Custom DocPerm", {
            "parent": perm.parent, "permlevel": perm.permlevel, "role": new,
        })
        if dry_run:
            mode = "delete (dup)" if exists_new else "rename"
            print(f"  [DRY-RUN] Custom DocPerm {perm.name} ({perm.parent}): {mode}")
        else:
            if exists_new:
                frappe.db.sql("DELETE FROM `tabCustom DocPerm` WHERE name=%s", perm.name)
            else:
                frappe.db.sql("UPDATE `tabCustom DocPerm` SET role=%s WHERE name=%s", (new, perm.name))
        n += 1
    return n


def _migrate_workflow_transitions(old: str, new: str, audit: dict, dry_run: bool) -> int:
    n = 0
    for t in audit["wf_transitions"]:
        if dry_run:
            print(f"  [DRY-RUN] WF Transition {t.parent} [{t.state}→{t.action}]: allowed {old}→{new}")
        else:
            frappe.db.sql("UPDATE `tabWorkflow Transition` SET allowed=%s WHERE name=%s", (new, t.name))
        n += 1
    return n


def _migrate_workflow_states(old: str, new: str, audit: dict, dry_run: bool) -> int:
    n = 0
    for s in audit["wf_states"]:
        if dry_run:
            print(f"  [DRY-RUN] WF Document State {s.parent} [{s.state}]: allow_edit {old}→{new}")
        else:
            frappe.db.sql("UPDATE `tabWorkflow Document State` SET allow_edit=%s WHERE name=%s", (new, s.name))
        n += 1
    return n


def _migrate_other_has_role(old: str, new: str, audit: dict, dry_run: bool) -> int:
    """Migrer les Has Role attachés à Workspace / Report / autres parenttypes.

    Évite les doublons (parent, parenttype, role).
    """
    n = 0
    for row in audit["has_role_other"]:
        exists_new = frappe.db.exists("Has Role", {
            "parent": row.parent, "parenttype": row.parenttype, "role": new,
        })
        if dry_run:
            mode = "delete (dup)" if exists_new else "rename"
            print(f"  [DRY-RUN] Has Role {row.parenttype}/{row.parent}: {mode}")
        else:
            if exists_new:
                frappe.db.sql("DELETE FROM `tabHas Role` WHERE name=%s", row.name)
            else:
                frappe.db.sql("UPDATE `tabHas Role` SET role=%s WHERE name=%s", (new, row.name))
        n += 1
    return n


def _migrate_notifications(old: str, new: str, audit: dict, dry_run: bool) -> int:
    n = 0
    for r in audit["notif_recipients"]:
        if dry_run:
            print(f"  [DRY-RUN] Notification {r.parent}: receiver_by_role {old}→{new}")
        else:
            frappe.db.sql(
                "UPDATE `tabNotification Recipient` SET receiver_by_role=%s WHERE name=%s",
                (new, r.name),
            )
        n += 1
    return n


def _delete_role(old: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  [DRY-RUN] Supprimerait le rôle: {old}")
        return
    frappe.db.sql("DELETE FROM `tabRole` WHERE name=%s", old)
    print(f"  → Rôle supprimé: {old}")


def migrate_role(old: str, new: str, create_new: bool = False, dry_run: bool = True) -> dict:
    """Migration complète d'un rôle vers un autre.

    Retourne un dict avec les compteurs par catégorie.
    """
    print(f"\n=== Migration: {old} → {new} (dry_run={dry_run}) ===")

    if not _ensure_role(new, dry_run) and not create_new:
        return {"error": f"Rôle cible '{new}' n'existe pas et create_new=False"}
    if create_new and not _ensure_role(new, dry_run):
        # En dry-run, _ensure_role retourne False ; on continue le dry-run en faisant
        # comme si le rôle existait.
        if not dry_run:
            return {"error": f"Échec création rôle '{new}'"}

    audit = _audit_old_role(old)
    if not audit["exists"]:
        print(f"  → Rôle source '{old}' n'existe pas. Skip.")
        return {"skipped": True}

    stats = {
        "users": _migrate_users(old, new, audit, dry_run),
        "employees": len(audit["employees"]),
        "has_role_other": _migrate_other_has_role(old, new, audit, dry_run),
        "docperms": _migrate_docperms(old, new, audit, dry_run),
        "custom_docperms": _migrate_custom_docperms(old, new, audit, dry_run),
        "wf_transitions": _migrate_workflow_transitions(old, new, audit, dry_run),
        "wf_states": _migrate_workflow_states(old, new, audit, dry_run),
        "notif_recipients": _migrate_notifications(old, new, audit, dry_run),
    }

    if audit["employees"]:
        print(f"  ⚠️ ATTENTION : {len(audit['employees'])} Employees ont aussi ce rôle "
              f"(non migré automatiquement, à voir manuellement)")
        for emp in audit["employees"]:
            print(f"     - {emp}")

    _delete_role(old, dry_run)

    return stats


def _run(dry_run: bool) -> dict:
    """Exécute toutes les migrations KYA configurées."""
    print(f"\n{'='*60}")
    print(f"  ROLE MERGE — {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"{'='*60}")

    results = {}
    for old, new, create_new in KYA_ROLE_MIGRATIONS:
        results[old] = migrate_role(old, new, create_new=create_new, dry_run=dry_run)

    if not dry_run:
        frappe.db.commit()
        frappe.clear_cache()
        print("\n✓ Commit + cache cleared.")
    else:
        print("\nℹ DRY-RUN : aucune modification écrite en DB.")

    print(f"\n=== RÉCAP ===")
    for old, stats in results.items():
        print(f"  {old}: {stats}")
    return results


def run_dry_run():
    """À invoquer via : bench --site <site> execute kya_hr.maintenance.role_merge.run_dry_run"""
    return _run(dry_run=True)


def run_migrations():
    """À invoquer via : bench --site <site> execute kya_hr.maintenance.role_merge.run_migrations"""
    return _run(dry_run=False)

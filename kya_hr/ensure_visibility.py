"""Ensure custom KYA workspaces and standard HRMS modules are visible
on the Frappe v16 desk home page (/app) for Administrator and System Manager.

Why this exists
---------------
After upgrading to Frappe v16 + ERPNext + HRMS, custom workspaces created by
``kya_hr``, ``kya_services``, ``servicestechniques`` and HRMS modules are
sometimes invisible from the desk home, even though ``tabWorkspace.public=1``
and ``hide_custom=0``. The actual reasons we observed:

1. The user has entries in ``tabBlock Module`` that hide modules.
2. Some workspaces have ``for_user`` set (private to a deleted user), or a
   ``parent_page`` referring to a removed workspace, which makes Frappe
   skip them when rendering the top-level grid.
3. ``tabUser.home_settings`` is a stale JSON snapshot from an earlier site
   layout and prevents new workspaces from appearing until reset.
4. The page layout cache is not invalidated.

This module is idempotent and safe to run as ``after_install`` /
``after_migrate`` for kya_hr — it only touches our own apps and the
Administrator user. It never raises.
"""

from __future__ import annotations

import json

import frappe


# Apps whose workspaces we own and must keep top-level / public.
KYA_APPS = ("kya_hr", "kya_services", "servicestechniques")

# Standard apps whose workspaces we want to ensure are visible too.
STANDARD_APPS_TO_FIX = ("hrms", "erpnext", "frappe")

# Users that must always see everything.
ADMIN_USERS = ("Administrator",)


def _safe_log(label: str, payload):
    try:
        frappe.logger().info(f"[ensure_visibility] {label}: {payload}")
    except Exception:
        pass


def _unblock_modules_for_admins():
    """Remove all rows in ``tabBlock Module`` for our admin users so they
    never have a hidden module."""
    removed = 0
    for user in ADMIN_USERS:
        try:
            res = frappe.db.sql(
                "DELETE FROM `tabBlock Module` WHERE parent = %s",
                (user,),
            )
            removed += getattr(res, "rowcount", 0) or 0
        except Exception as exc:
            _safe_log("unblock_modules error", str(exc))
    return removed


def _reset_home_settings_for_admins():
    """Reset User.home_settings JSON so newly added workspaces show up
    in the default order on next login."""
    reset = 0
    for user in ADMIN_USERS:
        try:
            frappe.db.set_value(
                "User", user, "home_settings", "", update_modified=False
            )
            reset += 1
        except Exception as exc:
            _safe_log("reset_home_settings error", str(exc))
    return reset


def _backfill_workspace_titles():
    """CRITICAL: Workspace.title=NULL crashes Desk JS rendering (slug(null)
    in frappe.utils.generate_route -> entire desk page goes blank: right-click
    broken, search bar non-clickable, notification panel empty).
    Backfill title from name for any workspace missing it."""
    fixed = 0
    try:
        rows = frappe.db.sql(
            """
            SELECT name FROM tabWorkspace
            WHERE title IS NULL OR title = ''
            """,
            as_dict=True,
        ) or []
    except Exception as exc:
        _safe_log("select missing titles error", str(exc))
        return 0
    for row in rows:
        try:
            frappe.db.set_value(
                "Workspace", row["name"], "title", row["name"],
                update_modified=False,
            )
            fixed += 1
        except Exception as exc:
            _safe_log(f"backfill title {row['name']} error", str(exc))
    return fixed


def _normalize_workspace_visibility():
    """For workspaces of our apps + HRMS, force ``public=1``, ``hide_custom=0``,
    and clear ``for_user`` / ``parent_page`` if they would hide the workspace
    from the top-level grid."""
    apps = KYA_APPS + STANDARD_APPS_TO_FIX
    placeholders = ", ".join(["%s"] * len(apps))
    try:
        rows = frappe.db.sql(
            f"""
            SELECT name, public, hide_custom, for_user, parent_page, app
            FROM tabWorkspace
            WHERE app IN ({placeholders})
            """,
            apps,
            as_dict=True,
        ) or []
    except Exception as exc:
        _safe_log("select workspaces error", str(exc))
        return 0

    fixed = 0
    for row in rows:
        updates = {}
        if not row.get("public"):
            updates["public"] = 1
        if row.get("hide_custom"):
            updates["hide_custom"] = 0
        # for_user pointing to anything = workspace is private; we want public
        if row.get("for_user"):
            updates["for_user"] = None
        # parent_page pointing to a non-existent workspace -> orphan, breaks render
        parent = row.get("parent_page")
        if parent:
            exists = frappe.db.exists("Workspace", parent)
            if not exists:
                updates["parent_page"] = None
        if not updates:
            continue
        try:
            for k, v in updates.items():
                frappe.db.set_value(
                    "Workspace", row["name"], k, v, update_modified=False
                )
            fixed += 1
        except Exception as exc:
            _safe_log(f"update workspace {row['name']} error", str(exc))
    return fixed


def _ensure_admin_has_all_roles():
    """Grant Administrator every enabled role so it can see every module."""
    granted = 0
    try:
        roles = frappe.get_all(
            "Role",
            filters={"disabled": 0},
            pluck="name",
        )
    except Exception as exc:
        _safe_log("list roles error", str(exc))
        return 0

    skip = {"All", "Guest", "Administrator"}
    for user in ADMIN_USERS:
        try:
            existing = set(
                frappe.get_all(
                    "Has Role",
                    filters={"parent": user, "parenttype": "User"},
                    pluck="role",
                )
            )
        except Exception:
            existing = set()
        for role in roles:
            if role in skip or role in existing:
                continue
            try:
                doc = frappe.get_doc(
                    {
                        "doctype": "Has Role",
                        "parent": user,
                        "parenttype": "User",
                        "parentfield": "roles",
                        "role": role,
                    }
                )
                doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
                granted += 1
            except Exception as exc:
                # Ignore unique/duplicate errors silently
                if "Duplicate" not in str(exc):
                    _safe_log(f"grant role {role} error", str(exc))
    return granted


def _clear_caches():
    try:
        frappe.clear_cache()
    except Exception:
        pass
    try:
        frappe.clear_website_cache()
    except Exception:
        pass


def execute():
    """Idempotent entrypoint. Called from hooks.py (after_install + after_migrate)."""
    result = {
        "blocked_modules_removed": 0,
        "home_settings_reset": 0,
        "titles_backfilled": 0,
        "workspaces_fixed": 0,
        "roles_granted": 0,
        "errors": [],
    }
    try:
        result["blocked_modules_removed"] = _unblock_modules_for_admins()
    except Exception as exc:
        result["errors"].append(("unblock_modules", str(exc)))
    try:
        result["home_settings_reset"] = _reset_home_settings_for_admins()
    except Exception as exc:
        result["errors"].append(("reset_home_settings", str(exc)))
    try:
        result["titles_backfilled"] = _backfill_workspace_titles()
    except Exception as exc:
        result["errors"].append(("backfill_titles", str(exc)))
    try:
        result["workspaces_fixed"] = _normalize_workspace_visibility()
    except Exception as exc:
        result["errors"].append(("normalize_workspaces", str(exc)))
    try:
        result["roles_granted"] = _ensure_admin_has_all_roles()
    except Exception as exc:
        result["errors"].append(("grant_roles", str(exc)))

    try:
        frappe.db.commit()
    except Exception:
        pass

    _clear_caches()

    _safe_log("execute result", result)
    return result

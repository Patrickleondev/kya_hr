"""Purge les Desktop Icon dupliques (Direction Generale, Espace Employes...).

Bug recurrent en prod : certains icones apparaissent en double/triple
sur /desk (ex: 'Direction Generale' x 3, 'Espace Employes' x 2). Cause :
plusieurs scripts (desktop_icons.py, force_sync_workspaces, etc.) creent
chacun un Desktop Icon pour le meme module sans verifier les doublons
prealables, ou les Desktop Icons globaux + user se cumulent.

Ce script :
1. Detecte les Desktop Icon ayant le meme module_name ou app pour le
   meme owner (Administrator ou par-user).
2. Garde le premier (par creation date) et supprime les autres.
3. Idempotent : si pas de doublon, ne touche rien.

Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


def _purge_doc_dups(table: str, keep_field: str = "creation", group_fields: list = None) -> dict:
    """Pour chaque cle composee de group_fields, garde un seul record.

    Le 'gagnant' = celui avec le min(keep_field) (= le plus ancien cree).
    Les autres sont supprimes.
    """
    if not group_fields:
        return {"deleted": 0}

    group_cols = ", ".join(f"`{c}`" for c in group_fields)
    rows = frappe.db.sql(
        f"""
        SELECT {group_cols}, COUNT(*) AS n
        FROM `tab{table}`
        GROUP BY {group_cols}
        HAVING COUNT(*) > 1
        """,
        as_dict=True,
    ) or []

    deleted = 0
    details = []
    for row in rows:
        # Construire le where dynamique
        where_clauses = []
        params: dict = {}
        for i, col in enumerate(group_fields):
            val = row.get(col)
            if val is None:
                where_clauses.append(f"`{col}` IS NULL")
            else:
                where_clauses.append(f"`{col}` = %(p{i})s")
                params[f"p{i}"] = val
        where = " AND ".join(where_clauses)

        records = frappe.db.sql(
            f"SELECT name FROM `tab{table}` WHERE {where} ORDER BY `{keep_field}` ASC",
            params,
            as_dict=True,
        ) or []

        # Garder le premier, supprimer les autres
        for r in records[1:]:
            try:
                frappe.delete_doc(table, r.name, force=1, ignore_permissions=True)
                deleted += 1
                details.append({"table": table, "name": r.name, "key": {c: row.get(c) for c in group_fields}})
            except Exception:
                try:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"fix_duplicate_desktop_icons: delete {table}/{r.name}",
                    )
                except Exception:
                    pass

    return {"deleted": deleted, "details": details}


def execute() -> dict:
    summary = {}

    # 1. Desktop Icon : doublons par (module_name, owner)
    # NB : la colonne module_name a disparu du schema Desktop Icon dans les
    # versions recentes de Frappe -> on verifie sa presence avant de l'utiliser
    # (sinon "Unknown column 'module_name'" a chaque migrate, log_error mais
    # jamais reellement corrige).
    if frappe.db.exists("DocType", "Desktop Icon") and frappe.db.has_column("Desktop Icon", "module_name"):
        try:
            summary["desktop_icon"] = _purge_doc_dups(
                "Desktop Icon", "creation",
                ["module_name", "owner"],
            )
        except Exception:
            try:
                frappe.log_error(frappe.get_traceback(), "fix_duplicate_desktop_icons: Desktop Icon")
            except Exception:
                pass

    # 2. Workspace Link : doublons par (parent, label, link_to)
    try:
        summary["workspace_link"] = _purge_doc_dups(
            "Workspace Link", "creation",
            ["parent", "label", "link_to"],
        )
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), "fix_duplicate_desktop_icons: Workspace Link")
        except Exception:
            pass

    # 3. Workspace Shortcut : doublons par (parent, label, link_to)
    try:
        summary["workspace_shortcut"] = _purge_doc_dups(
            "Workspace Shortcut", "creation",
            ["parent", "label", "link_to"],
        )
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), "fix_duplicate_desktop_icons: Workspace Shortcut")
        except Exception:
            pass

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Desktop Icon")
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass

    print(f"[fix_duplicate_desktop_icons] {summary}")
    return summary

"""Fix sidebar : clic sur 'Equipe KYA' redirigeait vers 'Espace Stagiaires'.

Origine probable du bug :
- Un Workspace Link avec label='Equipe KYA' mais link_to='Espace Stagiaires'
  (mauvaise saisie initiale).
- OU le Workspace 'Equipe KYA' lui-meme a un parent_page qui pointe vers
  'Espace Stagiaires', creant une boucle visuelle.

Ce script :
1. Detecte les Workspace Link dont le label contient 'Equipe KYA' mais le
   link_to vise 'Espace Stagiaires' -> recible sur le DocType 'Equipe KYA'
2. Si un Workspace 'Equipe KYA' existe avec parent_page=Espace Stagiaires,
   on vide le parent_page (workspace racine).

Idempotent. Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


TARGET_LABEL_PATTERNS = ("Equipe KYA", "Équipe KYA", "equipe-kya", "Equipe-KYA")
WRONG_LINK_TO = ("Espace Stagiaires", "espace-stagiaires", "Espace stagiaires")


def _fix_workspace_links() -> dict:
    """Corrige les Workspace Link qui ont un label Equipe KYA mais ciblent Espace Stagiaires."""
    fixed = []
    rows = frappe.db.sql(
        """
        SELECT name, parent, label, link_to, link_type, type
        FROM `tabWorkspace Link`
        WHERE label IS NOT NULL AND label != ''
        """,
        as_dict=True,
    ) or []

    for row in rows:
        label = (row.label or "").strip()
        link_to = (row.link_to or "").strip()
        if not any(p.lower() in label.lower() for p in TARGET_LABEL_PATTERNS):
            continue
        if not any(w.lower() in link_to.lower() for w in WRONG_LINK_TO):
            continue
        # Mauvaise cible -> on essaie de pointer sur le DocType 'Equipe KYA'
        # uniquement s'il existe (sinon on ne touche pas)
        if not frappe.db.exists("DocType", "Equipe KYA"):
            continue
        try:
            frappe.db.set_value(
                "Workspace Link", row.name,
                {
                    "link_to": "Equipe KYA",
                    "link_type": "DocType",
                    "type": "Link",
                },
                update_modified=False,
            )
            fixed.append({"link": row.name, "parent_workspace": row.parent})
        except Exception:
            try:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"fix_sidebar: link {row.name}",
                )
            except Exception:
                pass

    return {"links_fixed": fixed, "count": len(fixed)}


def _fix_workspace_parent_page() -> dict:
    """Si Workspace 'Equipe KYA' existe avec parent_page=Espace Stagiaires, on vide."""
    fixed = []
    for ws_name in ("Equipe KYA", "Équipe KYA"):
        if not frappe.db.exists("Workspace", ws_name):
            continue
        parent_page = frappe.db.get_value("Workspace", ws_name, "parent_page")
        if not parent_page:
            continue
        if "stagiaires" in parent_page.lower():
            try:
                frappe.db.set_value(
                    "Workspace", ws_name, "parent_page", "",
                    update_modified=False,
                )
                fixed.append(ws_name)
            except Exception:
                try:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"fix_sidebar: parent_page {ws_name}",
                    )
                except Exception:
                    pass
    return {"workspaces_fixed": fixed, "count": len(fixed)}


def execute() -> dict:
    summary = {}
    try:
        summary["links"] = _fix_workspace_links()
        summary["parent_pages"] = _fix_workspace_parent_page()
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
        frappe.clear_cache(doctype="Workspace Link")
    except Exception as exc:
        summary["error"] = str(exc)
        try:
            frappe.log_error(frappe.get_traceback(), "fix_sidebar_equipe_kya")
        except Exception:
            pass

    print(f"[fix_sidebar_equipe_kya] {summary}")
    return summary

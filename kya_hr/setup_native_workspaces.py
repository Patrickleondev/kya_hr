"""Restaure les workspaces natifs Frappe/ERPNext/HRMS vides.

Bug recurrent : apres certaines migrations v16, les workspaces natifs
(HR, Accounting, Stock, etc.) perdent leur contenu (Workspace.content =
null/[], plus aucun Workspace Link / Workspace Shortcut). Cliquer sur
l'icone donne une page vide, les sous-icones (sub-folders) disparaissent.

Solution : on detecte les workspaces critiques dont le content est vide
et on les re-pose via frappe.reload_doc qui lit le JSON natif et upserte.

force=True : on ecrase le record vide par celui du JSON. Pas de risque
de perte car le record est deja vide.

Idempotent : si le workspace est non-vide, on ne touche pas.
"""
from __future__ import annotations

import frappe


# Liste des workspaces a restaurer (s'ils sont vides en BD).
# Format : (workspace_name_db, app_name, module_folder, doc_name_lower)
# Le JSON est cherche sous apps/{app}/{app}/{module}/workspace/{doc_name}/{doc_name}.json
NATIVE_WORKSPACES: list[tuple[str, str, str, str]] = [
    ("HR", "hrms", "hr", "hr"),
    ("Accounting", "erpnext", "accounts", "accounting"),
    ("Stock", "erpnext", "stock", "stock"),
    ("Buying", "erpnext", "buying", "buying"),
    ("Selling", "erpnext", "selling", "selling"),
    ("Payroll", "hrms", "payroll", "payroll"),
]


def _is_workspace_empty(ws_name: str) -> bool:
    """Renvoie True si le workspace existe en BD mais est sans contenu."""
    if not frappe.db.exists("Workspace", ws_name):
        return False
    content = frappe.db.get_value("Workspace", ws_name, "content")
    has_content = bool(content) and len(content) > 100
    n_links = frappe.db.count("Workspace Link", {"parent": ws_name})
    n_shortcuts = frappe.db.count("Workspace Shortcut", {"parent": ws_name})
    return not has_content and n_links == 0 and n_shortcuts == 0


def _reload_workspace(app: str, module: str, dn: str) -> bool:
    """Re-pose le workspace depuis le JSON natif de l'app."""
    try:
        base_path = frappe.get_app_path(app)
        frappe.reload_doc(module, "workspace", dn, base_path=base_path, force=True)
        return True
    except Exception:
        try:
            frappe.log_error(
                frappe.get_traceback(),
                f"setup_native_workspaces: reload {app}/{module}/{dn}",
            )
        except Exception:
            pass
        return False


def execute() -> dict:
    """Idempotent : restaure les workspaces vides parmi NATIVE_WORKSPACES."""
    summary = {"restored": [], "already_ok": [], "missing_in_db": [], "failed": []}

    for ws_name, app, module, dn in NATIVE_WORKSPACES:
        # App pas installee -> on saute silencieusement
        try:
            frappe.get_app_path(app)
        except Exception:
            continue

        if not frappe.db.exists("Workspace", ws_name):
            summary["missing_in_db"].append(ws_name)
            continue

        if not _is_workspace_empty(ws_name):
            summary["already_ok"].append(ws_name)
            continue

        ok = _reload_workspace(app, module, dn)
        if ok:
            summary["restored"].append(ws_name)
        else:
            summary["failed"].append(ws_name)

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass

    print(f"[setup_native_workspaces] {summary}")
    return summary

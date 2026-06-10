"""Cree 2 workspaces parents 'Frappe HR' et 'Comptabilité' qui groupent
les sous-workspaces natifs ERPNext/HRMS v16.

Probleme : en v16, ERPNext et HRMS ont decompose HR et Accounting en
multiples sous-workspaces (Leaves, Recruitment, Performance, etc. pour
HR ; Financial Reports, Invoicing pour Accounting). Resultat : la
sidebar montre les sous-workspaces a plat sans regroupement, et les
users qui s'attendent a voir 'Frappe HR' ou 'Comptabilité' comme
entrees principales ne les voient pas (l'app switcher en haut les
affiche mais c'est moins visible).

Solution : creer 2 workspaces parents KYA qui ont :
- parent_page = NULL (workspaces racines visibles dans la sidebar)
- les sous-workspaces natifs reassocies avec parent_page = ce parent
  (la sidebar les affiche alors en arborescence)

Idempotent. Si les workspaces existent deja avec ce nom, on les
laisse intacts.
"""
from __future__ import annotations

import frappe


NATIVE_HR_CHILDREN = [
    "Leaves",
    "Recruitment",
    "Performance",
    "Shift & Attendance",
    "HR Setup",
    "Payroll",
    "Tenure",
    "Expenses",
    "Tax & Benefits",
]

NATIVE_ACCOUNTING_CHILDREN = [
    "Financial Reports",
    "Invoicing",
]


def _ensure_parent_workspace(name: str, label: str, icon: str, sequence: float) -> str:
    """Cree un workspace parent KYA si absent. Retourne 'created' ou 'exists'."""
    if frappe.db.exists("Workspace", name):
        return "exists"

    try:
        doc = frappe.new_doc("Workspace")
        doc.name = name
        doc.label = label
        doc.title = label
        doc.icon = icon
        doc.public = 1
        doc.is_hidden = 0
        doc.parent_page = ""
        doc.sequence_id = sequence
        doc.module = "KYA HR"
        doc.app = "kya_hr"
        doc.content = "[]"
        doc.insert(ignore_permissions=True)
        return "created"
    except Exception:
        try:
            frappe.log_error(
                frappe.get_traceback(),
                f"setup_native_parents: create {name}",
            )
        except Exception:
            pass
        return "error"


def _reparent_children(parent_name: str, children: list[str]) -> dict:
    """Associe parent_page=parent_name pour chaque child existant."""
    stats = {"reparented": 0, "missing": 0, "already_set": 0, "errors": 0}
    for child in children:
        if not frappe.db.exists("Workspace", child):
            stats["missing"] += 1
            continue
        current_parent = frappe.db.get_value("Workspace", child, "parent_page") or ""
        if current_parent == parent_name:
            stats["already_set"] += 1
            continue
        try:
            frappe.db.set_value(
                "Workspace", child, "parent_page", parent_name,
                update_modified=False,
            )
            stats["reparented"] += 1
        except Exception:
            stats["errors"] += 1
            try:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"setup_native_parents: reparent {child}",
                )
            except Exception:
                pass
    return stats


def execute() -> dict:
    summary = {}

    # Cree les 2 workspaces parents
    summary["hr_parent"] = _ensure_parent_workspace(
        name="Frappe HR",
        label="Frappe HR",
        icon="users",
        sequence=8.0,
    )
    summary["accounting_parent"] = _ensure_parent_workspace(
        name="Comptabilité",
        label="Comptabilité",
        icon="bank",
        sequence=13.0,
    )

    # Reparente les sous-workspaces seulement si le parent existe
    if frappe.db.exists("Workspace", "Frappe HR"):
        summary["hr_children"] = _reparent_children("Frappe HR", NATIVE_HR_CHILDREN)
    if frappe.db.exists("Workspace", "Comptabilité"):
        summary["accounting_children"] = _reparent_children("Comptabilité", NATIVE_ACCOUNTING_CHILDREN)

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass

    print(f"[setup_native_parents] {summary}")
    return summary

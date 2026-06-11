"""Cree 2 workspaces parents 'Frappe HR' et 'Comptabilité' REMPLIS,
qui groupent et exposent les fonctions natives ERPNext/HRMS v16.

Contexte v16 (verifie sur les sources officielles + l'instance) :
- HRMS v16 n'a PAS de workspace 'HR' unique : il est eclate en
  Leaves, Recruitment, Performance, Shift & Attendance, HR Setup,
  Payroll, Tenure, Expenses, Tax & Benefits. La gestion Employee
  (People) est dans 'Tenure'.
- ERPNext v16 n'a PAS de workspace 'Accounting' : tout est dans
  'Invoicing' (Plan de comptes, Ecritures, Paiements, Banque, Taxes,
  Centres de cout) + 'Financial Reports' (rapports). Le label
  'Invoicing' masque la richesse du contenu.

Ces 2 parents NE REMPLACENT PAS les espaces KYA (Espace RH,
Espace Comptabilité) qui restent les interfaces simplifiees pour les
utilisateurs metier. Les parents ici sont pour les power-users
(comptable, RH avancee) qui ont besoin des fonctions natives completes.

Idempotent : reconstruit le content + les shortcuts a chaque run.
"""
from __future__ import annotations

import json

import frappe


# ---- Definition des raccourcis (label, doctype/report, type, couleur) ----
# type : 'DocType' | 'Report' | 'Workspace'
HR_SHORTCUTS = [
    {"label": "Employés (People)", "link_to": "Employee", "type": "DocType", "color": "Blue"},
    {"label": "Demandes de congé", "link_to": "Leave Application", "type": "DocType", "color": "Green"},
    {"label": "Présences", "link_to": "Attendance", "type": "DocType", "color": "Cyan"},
    {"label": "Pointages", "link_to": "Employee Checkin", "type": "DocType", "color": "Cyan"},
    {"label": "Bulletins de paie", "link_to": "Salary Slip", "type": "DocType", "color": "Orange"},
    {"label": "Onboarding", "link_to": "Employee Onboarding", "type": "DocType", "color": "Purple"},
]

# Sous-workspaces HRMS natifs a lier comme cards
HR_SUBWORKSPACES = [
    "Leaves", "Shift & Attendance", "Payroll", "Recruitment",
    "Performance", "Tenure", "Expenses", "Tax & Benefits", "HR Setup",
]

COMPTA_SHORTCUTS = [
    {"label": "Plan de comptes", "link_to": "Account", "type": "DocType", "color": "Blue"},
    {"label": "Écriture comptable", "link_to": "Journal Entry", "type": "DocType", "color": "Green"},
    {"label": "Paiement", "link_to": "Payment Entry", "type": "DocType", "color": "Green"},
    {"label": "Facture de vente", "link_to": "Sales Invoice", "type": "DocType", "color": "Orange"},
    {"label": "Facture d'achat", "link_to": "Purchase Invoice", "type": "DocType", "color": "Orange"},
    {"label": "Grand livre", "link_to": "General Ledger", "type": "Report", "color": "Purple"},
]

COMPTA_SUBWORKSPACES = ["Invoicing", "Financial Reports"]


def _ensure_parent_workspace(name: str, label: str, icon: str, sequence: float) -> str:
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
        frappe.log_error(frappe.get_traceback(), f"setup_native_parents: create {name}")
        return "error"


def _rebuild_shortcuts(ws_name: str, shortcuts: list[dict]) -> None:
    """Supprime puis recree les Workspace Shortcut du parent (idempotent)."""
    # Supprimer les anciens shortcuts KYA de ce parent
    frappe.db.delete("Workspace Shortcut", {"parent": ws_name})

    ws = frappe.get_doc("Workspace", ws_name)
    ws.shortcuts = []
    for sc in shortcuts:
        ws.append("shortcuts", {
            "type": sc["type"],
            "label": sc["label"],
            "link_to": sc["link_to"],
            "color": sc.get("color", "Grey"),
            "doc_view": "List" if sc["type"] == "DocType" else "",
        })
    ws.save(ignore_permissions=True)


def _build_content(title: str, emoji: str, subtitle: str,
                   shortcuts: list[dict], subworkspaces: list[str]) -> str:
    """Construit le content JSON (blocks editorjs) du workspace parent."""
    blocks = [
        {"id": "hero", "type": "header",
         "data": {"text": f"<div class='ellipsis' title='{title}'>{emoji} {title}</div>",
                  "level": 3, "col": 12}},
        {"id": "sub", "type": "paragraph",
         "data": {"text": f"<i>{subtitle}</i>", "col": 12}},
        {"id": "sp0", "type": "spacer", "data": {"col": 12}},
        {"id": "h_acc", "type": "header",
         "data": {"text": "<b>⚡ Accès rapides</b>", "level": 4, "col": 12}},
    ]
    # Shortcuts (3 colonnes chacun)
    for i, sc in enumerate(shortcuts):
        blocks.append({
            "id": f"sc{i}", "type": "shortcut",
            "data": {"shortcut_name": sc["label"], "col": 4},
        })
    # Spacer + section sous-workspaces
    blocks.append({"id": "sp1", "type": "spacer", "data": {"col": 12}})
    blocks.append({"id": "h_sub", "type": "header",
                   "data": {"text": "<b>📂 Modules détaillés</b>", "level": 4, "col": 12}})
    for i, sw in enumerate(subworkspaces):
        blocks.append({
            "id": f"cd{i}", "type": "card",
            "data": {"card_name": sw, "col": 4},
        })
    return json.dumps(blocks, ensure_ascii=False)


def _reparent_children(parent_name: str, children: list[str]) -> dict:
    stats = {"reparented": 0, "missing": 0, "already_set": 0}
    for child in children:
        if not frappe.db.exists("Workspace", child):
            stats["missing"] += 1
            continue
        current = frappe.db.get_value("Workspace", child, "parent_page") or ""
        if current == parent_name:
            stats["already_set"] += 1
            continue
        try:
            frappe.db.set_value("Workspace", child, "parent_page", parent_name,
                                update_modified=False)
            stats["reparented"] += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"setup_native_parents: reparent {child}")
    return stats


def execute() -> dict:
    summary = {}

    # 1. Frappe HR
    summary["hr_parent"] = _ensure_parent_workspace("Frappe HR", "Frappe HR", "users", 8.0)
    if frappe.db.exists("Workspace", "Frappe HR"):
        try:
            # Garder seulement les shortcuts dont le doctype existe
            valid_hr = [s for s in HR_SHORTCUTS
                        if frappe.db.exists("DocType", s["link_to"]) or s["type"] == "Report"]
            _rebuild_shortcuts("Frappe HR", valid_hr)
            content = _build_content(
                "Frappe HR", "👥",
                "Accès aux fonctions RH natives (People, congés, paie...). "
                "Pour les opérations courantes, utilisez plutôt l'Espace RH.",
                valid_hr, HR_SUBWORKSPACES,
            )
            frappe.db.set_value("Workspace", "Frappe HR", "content", content, update_modified=False)
            summary["hr_children"] = _reparent_children("Frappe HR", HR_SUBWORKSPACES)
            summary["hr_shortcuts"] = len(valid_hr)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "setup_native_parents: HR build")

    # 2. Comptabilité
    summary["compta_parent"] = _ensure_parent_workspace("Comptabilité", "Comptabilité", "bank", 13.0)
    if frappe.db.exists("Workspace", "Comptabilité"):
        try:
            valid_compta = [s for s in COMPTA_SHORTCUTS
                            if frappe.db.exists("DocType", s["link_to"]) or s["type"] == "Report"]
            _rebuild_shortcuts("Comptabilité", valid_compta)
            content = _build_content(
                "Comptabilité", "🏦",
                "Comptabilité complète : plan de comptes, écritures, paiements, "
                "banque, taxes. Pour la caisse simplifiée, voyez l'Espace Comptabilité.",
                valid_compta, COMPTA_SUBWORKSPACES,
            )
            frappe.db.set_value("Workspace", "Comptabilité", "content", content, update_modified=False)
            summary["compta_children"] = _reparent_children("Comptabilité", COMPTA_SUBWORKSPACES)
            summary["compta_shortcuts"] = len(valid_compta)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "setup_native_parents: Compta build")

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass

    print(f"[setup_native_parents] {summary}")
    return summary

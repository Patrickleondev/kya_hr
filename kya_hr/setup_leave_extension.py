"""KYA Leave Application : champs pour prolongation exceptionnelle DG.

Code du Travail Togolais : les delais de conges peuvent etre prolonges
sous ordre du DG (ex : maternite 14 sem + 3 sem supplementaires, conge
annuel 30j + N jours selon situation, etc.).

Ce script ajoute 3 Custom Fields sur Leave Application :
- kya_demande_prolongation (Check) : l'employe coche pour demander
- kya_nouvelle_date_fin (Date)   : nouvelle date_fin proposee
- kya_motif_prolongation (Small Text) : justification

Le workflow proprement dit (transition 'En attente DG Prolongation' ->
'Prolongation Approuvee') sera configure dans Desk par la RH apres ce
deploiement. Voir GUIDE_SOLUTIONS_DESK.md section congs prolongation.

Idempotent. Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


KYA_LEAVE_EXTENSION_FIELDS: list[dict] = [
    {
        "doctype": "Custom Field",
        "dt": "Leave Application",
        "fieldname": "kya_section_prolongation",
        "label": "Prolongation exceptionnelle (sous ordre DG)",
        "fieldtype": "Section Break",
        "insert_after": "kya_motif_detail",
        "collapsible": 1,
        "description": "A remplir uniquement si une prolongation est demandee au DG.",
    },
    {
        "doctype": "Custom Field",
        "dt": "Leave Application",
        "fieldname": "kya_demande_prolongation",
        "label": "Demander une prolongation au DG",
        "fieldtype": "Check",
        "insert_after": "kya_section_prolongation",
        "default": "0",
    },
    {
        "doctype": "Custom Field",
        "dt": "Leave Application",
        "fieldname": "kya_nouvelle_date_fin",
        "label": "Nouvelle date de fin proposee",
        "fieldtype": "Date",
        "insert_after": "kya_demande_prolongation",
        "depends_on": "eval:doc.kya_demande_prolongation==1",
        "description": "La date_fin de la demande sera mise a jour automatiquement a l'approbation DG.",
    },
    {
        "doctype": "Custom Field",
        "dt": "Leave Application",
        "fieldname": "kya_motif_prolongation",
        "label": "Motif de la prolongation",
        "fieldtype": "Small Text",
        "insert_after": "kya_nouvelle_date_fin",
        "depends_on": "eval:doc.kya_demande_prolongation==1",
        "mandatory_depends_on": "eval:doc.kya_demande_prolongation==1",
    },
]


def _upsert_custom_field(cf: dict) -> str:
    cf_name = f"{cf['dt']}-{cf['fieldname']}"
    if frappe.db.exists("Custom Field", cf_name):
        doc = frappe.get_doc("Custom Field", cf_name)
        changed = False
        for k, v in cf.items():
            if k in ("doctype", "dt", "fieldname"):
                continue
            if getattr(doc, k, None) != v:
                setattr(doc, k, v)
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
            return "updated"
        return "unchanged"

    new_doc = frappe.get_doc(cf)
    new_doc.insert(ignore_permissions=True)
    return "created"


def execute() -> dict:
    """Idempotent. Pose les Custom Fields prolongation sur Leave Application."""
    summary = {"created": 0, "updated": 0, "unchanged": 0, "errors": []}

    if not frappe.db.has_table("Leave Application"):
        summary["skipped"] = "Leave Application table absent"
        print(f"[setup_leave_extension] {summary}")
        return summary

    for cf in KYA_LEAVE_EXTENSION_FIELDS:
        try:
            action = _upsert_custom_field(cf)
            summary[action] = summary.get(action, 0) + 1
        except Exception as exc:
            summary["errors"].append({"field": cf["fieldname"], "error": str(exc)})
            try:
                frappe.log_error(frappe.get_traceback(), f"setup_leave_extension {cf['fieldname']}")
            except Exception:
                pass

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Leave Application")
    except Exception:
        pass

    print(f"[setup_leave_extension] {summary}")
    return summary

"""Auto-synchronisation du compteur de membres des Équipes KYA.

PROBLÈME : Equipe KYA.nombre_membres n'est recalculé qu'au `before_save`
de l'Équipe (cf. equipe_kya.py:update_membres_count). Donc quand la RH
assigne un employé à une équipe via Employee.custom_kya_equipe, le
compteur de l'équipe reste périmé (souvent 0) tant que l'Équipe n'est pas
ré-enregistrée manuellement.

SOLUTION : ce module recalcule nombre_membres dès qu'un Employee change
d'équipe (assignation, changement, désassignation). Hooké sur les
doc_events Employee (after_insert + on_update). Défensif : ne lève jamais.

`recompute_all()` : recalcule TOUTES les équipes en une passe (idempotent,
appelable en migration). Corrige les compteurs périmés existants.
"""
from __future__ import annotations

import frappe


def _recount(equipe: str) -> None:
    if not equipe or not frappe.db.exists("Equipe KYA", equipe):
        return
    count = frappe.db.count("Employee", {"custom_kya_equipe": equipe,
                                         "status": "Active"})
    frappe.db.set_value("Equipe KYA", equipe, "nombre_membres", count,
                        update_modified=False)


def sync_on_employee_change(doc, method=None) -> None:
    """Recalcule le compteur de l'équipe quittée ET de l'équipe rejointe."""
    try:
        equipes: set[str] = set()
        current = doc.get("custom_kya_equipe")
        if current:
            equipes.add(current)
        # Équipe précédente (si changement)
        before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
        if before and before.get("custom_kya_equipe"):
            equipes.add(before.get("custom_kya_equipe"))
        for eq in equipes:
            _recount(eq)
        if equipes:
            frappe.db.commit()
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), "equipe_member_sync")
        except Exception:
            pass


@frappe.whitelist()
def recompute_all() -> dict:
    """Recalcule nombre_membres de toutes les Équipes (corrige les périmés)."""
    summary = {"equipes": 0, "updated": 0}
    try:
        equipes = frappe.get_all("Equipe KYA", pluck="name")
        for eq in equipes:
            summary["equipes"] += 1
            old = frappe.db.get_value("Equipe KYA", eq, "nombre_membres") or 0
            count = frappe.db.count("Employee", {"custom_kya_equipe": eq,
                                                 "status": "Active"})
            if int(old) != int(count):
                frappe.db.set_value("Equipe KYA", eq, "nombre_membres", count,
                                    update_modified=False)
                summary["updated"] += 1
        frappe.db.commit()
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), "equipe_member_sync.recompute_all")
        except Exception:
            pass
    print(f"[equipe_member_sync] equipes={summary['equipes']} updated={summary['updated']}")
    return summary

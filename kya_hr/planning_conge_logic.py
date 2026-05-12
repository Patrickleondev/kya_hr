# -*- coding: utf-8 -*-
"""Logique serveur pour Planning Conge.

Wired comme hook doc_events.before_save dans hooks.py.
Nécessaire car le DocType est marqué `custom: 1`, ce qui empêche
Frappe de charger la classe controller Python.
"""
import frappe
from frappe.utils import date_diff, getdate


def compute(doc, method=None):
    """Calcule total_jours, solde_disponible, solde_final.

    Validations associées:
    - Date fin >= date début pour chaque période
    - jours_monetisation >= 0
    - solde_final >= 0
    """
    _set_employee_details(doc)
    _calculate_total_days(doc)
    _validate_periods(doc)
    _calculate_solde(doc)
    _validate_monetisation(doc)


def _set_employee_details(doc):
    if getattr(doc, "employee", None) and not getattr(doc, "employee_name", None):
        doc.employee_name = frappe.db.get_value(
            "Employee", doc.employee, "employee_name"
        )


def _calculate_total_days(doc):
    total = 0
    for row in doc.get("periodes") or []:
        if row.date_debut and row.date_fin:
            days = date_diff(row.date_fin, row.date_debut) + 1
            row.nb_jours = max(days, 0)
            total += row.nb_jours
    doc.total_jours = total


def _validate_periods(doc):
    for row in doc.get("periodes") or []:
        if row.date_debut and row.date_fin:
            if getdate(row.date_fin) < getdate(row.date_debut):
                frappe.throw(
                    f"Ligne {row.idx} : la date de fin doit être postérieure "
                    f"à la date de début."
                )


def _calculate_solde(doc):
    solde_n1 = float(doc.get("solde_n1") or 0)
    jours_acquis = float(doc.get("jours_acquis") or 0)
    conges_obligatoires = int(doc.get("conges_obligatoires") or 0)
    total_jours = int(doc.get("total_jours") or 0)
    jours_monetisation = int(doc.get("jours_monetisation") or 0)

    doc.solde_disponible = solde_n1 + jours_acquis - conges_obligatoires
    doc.solde_final = doc.solde_disponible - total_jours - jours_monetisation


def _validate_monetisation(doc):
    jours_monetisation = int(doc.get("jours_monetisation") or 0)
    if jours_monetisation < 0:
        frappe.throw("Le nombre de jours à monétiser ne peut être négatif.")
    if doc.solde_final is not None and float(doc.solde_final) < 0:
        frappe.throw(
            f"Solde final négatif ({doc.solde_final:.1f} j) : "
            f"vous demandez plus de jours que votre solde disponible."
        )


def sync_statut(doc, method=None):
    """Synchronise le champ `statut` (Select) avec workflow_state.

    Wired comme on_update_after_submit + on_update.
    """
    if getattr(doc, "workflow_state", None):
        try:
            if doc.docstatus == 1:
                doc.db_set("statut", doc.workflow_state, update_modified=False)
            else:
                doc.statut = doc.workflow_state
        except Exception:
            pass

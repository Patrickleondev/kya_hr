# -*- coding: utf-8 -*-
"""
Patch v1.0 : Ajouter le rôle Employee aux reports du workspace Espace Stagiaires.
Les reports 'Tableau de Bord Stagiaires' et 'Rapport Présence Stagiaires' étaient
restreints à HR Manager / HR User, empêchant les stagiaires de les consulter.
"""
import frappe


def execute():
    reports = [
        "Tableau de Bord Stagiaires",
        "Rapport Pr\u00e9sence Stagiaires",
    ]
    for report_name in reports:
        if not frappe.db.exists("Report", report_name):
            continue
        already = frappe.db.exists(
            "Has Role",
            {"parenttype": "Report", "parent": report_name, "role": "Employee"},
        )
        if not already:
            frappe.get_doc(
                {
                    "doctype": "Has Role",
                    "parenttype": "Report",
                    "parentfield": "roles",
                    "parent": report_name,
                    "role": "Employee",
                }
            ).insert(ignore_permissions=True)
            frappe.db.commit()

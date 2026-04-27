# -*- coding: utf-8 -*-
"""Auto-rempli report_to_user (Email du chef) pour les DocTypes KYA.
Utilise par doc_events.before_save pour assurer que les notifications 'En attente Chef'
trouvent toujours le bon destinataire.
"""
import frappe


def populate_chef(doc, method=None):
    """Remplit doc.report_to_user depuis Employee.reports_to.user_id"""
    if not getattr(doc, "employee", None):
        return
    try:
        chef_emp = frappe.db.get_value("Employee", doc.employee, "reports_to")
        if not chef_emp:
            return
        chef_user = frappe.db.get_value("Employee", chef_emp, "user_id")
        if chef_user and getattr(doc, "report_to_user", None) != chef_user:
            doc.report_to_user = chef_user
    except Exception:
        # Fail silent: ne bloque jamais le save
        pass

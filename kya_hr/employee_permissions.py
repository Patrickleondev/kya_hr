# -*- coding: utf-8 -*-
"""Restrictions de visibilité sur le DocType Employee.

But : qu'un employé non-RH ne puisse pas lister les fiches d'autres employés
(via web form Link autocomplete, frappe.client.get_list, etc.).

Wired via hooks.py:
    permission_query_conditions = {
        "Employee": "kya_hr.employee_permissions.employee_query",
    }
    has_permission = {
        "Employee": "kya_hr.employee_permissions.employee_has_permission",
    }
"""
import frappe


PRIVILEGED_ROLES = {
    "System Manager",
    "HR Manager",
    "HR User",
    "Responsable RH",
    "Directeur Général",
    "DAAF",
    "DGA",
    "Administrator",
    "Auditeur Interne",
    "Manager",
}


def _user_is_privileged(user):
    if not user or user == "Guest":
        return False
    if user == "Administrator":
        return True
    return bool(PRIVILEGED_ROLES.intersection(set(frappe.get_roles(user))))


def _own_employee(user):
    """Retourne le name de l'Employee actif lié à user, ou None."""
    if not user or user == "Guest":
        return None
    return frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"}, "name"
    )


def employee_query(user):
    """Permission Query Condition : restreint la liste Employee.

    - Privileged (RH, DG, Admin) : pas de restriction
    - Employé : voit sa propre fiche + celles dont il est le supérieur direct
    - Sans fiche Employee : voit rien (1=0)
    """
    if _user_is_privileged(user):
        return ""

    own = _own_employee(user)
    if not own:
        return "1=0"

    # Employee voit : sa fiche + celles dont il est report_to
    return (
        f"(`tabEmployee`.name = {frappe.db.escape(own)} "
        f"OR `tabEmployee`.reports_to = {frappe.db.escape(own)} "
        f"OR `tabEmployee`.user_id = {frappe.db.escape(user)})"
    )


def employee_has_permission(doc, ptype="read", user=None):
    """Has Permission : vérifie l'accès à une fiche Employee spécifique.

    Empêche un non-RH de lire/modifier une fiche autre que la sienne ou
    celle d'un subordonné direct.
    """
    user = user or frappe.session.user

    if _user_is_privileged(user):
        return True

    own = _own_employee(user)
    if not own:
        return False

    target_name = doc.name if hasattr(doc, "name") else doc

    # Sa propre fiche
    if target_name == own:
        return True

    # Fiche d'un subordonné direct
    target_reports_to = frappe.db.get_value("Employee", target_name, "reports_to")
    if target_reports_to == own:
        return True

    # Fiche dont user_id == self.user (rare, mais cas où user_id est rempli sans Employee.name == own)
    target_user_id = frappe.db.get_value("Employee", target_name, "user_id")
    if target_user_id == user:
        return True

    return False

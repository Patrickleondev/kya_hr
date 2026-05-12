# -*- coding: utf-8 -*-
"""Permissions Equipe KYA + Tache Equipe : un Chef d'Équipe ne voit que
les équipes qu'il dirige (ou dont il est membre) et les tâches associées.

Complémentaire à `employee_permissions.py` (Employee).

Wired via hooks.py :
    permission_query_conditions = {
        "Employee": "kya_hr.employee_permissions.employee_query",
        "Equipe KYA": "kya_hr.equipe_permissions.equipe_kya_query",
        "Tache Equipe": "kya_hr.equipe_permissions.tache_equipe_query",
    }
"""
import frappe


GLOBAL_ROLES = {
    "System Manager",
    "Administrator",
    "HR Manager",
    "HR User",
    "Responsable RH",
    "Directeur Général",
    "DGA",
    "DAAF",
    "Responsable Comptable",
    "Auditeur Interne",
}

CHEF_ROLES = {"Chef Equipe", "Chef d'Équipe"}


def _user_is_global(user):
    if not user or user == "Guest":
        return False
    if user == "Administrator":
        return True
    return bool(GLOBAL_ROLES.intersection(set(frappe.get_roles(user))))


def _own_employee(user):
    if not user or user == "Guest":
        return None
    return frappe.db.get_value(
        "Employee", {"user_id": user, "status": "Active"}, "name"
    )


def equipe_kya_query(user):
    """Restreint la liste Equipe KYA aux équipes que l'employé dirige ou dont
    il est membre. Les rôles globaux gardent vue complète."""
    if _user_is_global(user):
        return ""
    emp = _own_employee(user)
    if not emp:
        return "1=0"
    safe_emp = frappe.db.escape(emp)
    return (
        f"(`tabEquipe KYA`.chef_equipe = {safe_emp} "
        f"OR `tabEquipe KYA`.name IN ("
        f"SELECT custom_kya_equipe FROM `tabEmployee` "
        f"WHERE name = {safe_emp} AND custom_kya_equipe IS NOT NULL))"
    )


def tache_equipe_query(user):
    """Restreint Tache Equipe :
    - Chef d'Équipe : les tâches dont l'équipe est dirigée par cet employé.
    - Employé : les tâches où il a une attribution, OU les tâches de son équipe.
    """
    if _user_is_global(user):
        return ""
    emp = _own_employee(user)
    if not emp:
        return "1=0"
    safe_emp = frappe.db.escape(emp)
    roles = set(frappe.get_roles(user) or [])

    if CHEF_ROLES & roles:
        return (
            f"`tabTache Equipe`.equipe IN ("
            f"SELECT name FROM `tabEquipe KYA` "
            f"WHERE chef_equipe = {safe_emp})"
        )

    return (
        f"(`tabTache Equipe`.name IN ("
        f"SELECT parent FROM `tabTache Equipe Attribution` "
        f"WHERE employe = {safe_emp}) "
        f"OR `tabTache Equipe`.equipe IN ("
        f"SELECT custom_kya_equipe FROM `tabEmployee` "
        f"WHERE name = {safe_emp} AND custom_kya_equipe IS NOT NULL))"
    )

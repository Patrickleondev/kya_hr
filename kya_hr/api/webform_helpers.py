# -*- coding: utf-8 -*-
"""Helpers pour les Web Forms KYA.

Fournit deux endpoints whitelistés (utilisateurs authentifiés uniquement)
pour pré-remplir le champ « demandeur » dans les formulaires :

- get_current_employee : Employee lié à frappe.session.user
- search_employees : recherche floue par nom (employé tape son nom si
  matricule oublié)
"""
from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def get_current_employee():
    """Retourne l'Employee lié à l'utilisateur courant.

    Returns dict {name, employee_name, department, designation} ou {} si
    aucun Employee n'est lié.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {}

    emp = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "department", "designation"],
        as_dict=True,
    )
    if not emp:
        # Fallback : email perso/pro si user_id n'est pas câblé
        for field in ("personal_email", "company_email", "prefered_email"):
            emp = frappe.db.get_value(
                "Employee",
                {field: user, "status": "Active"},
                ["name", "employee_name", "department", "designation"],
                as_dict=True,
            )
            if emp:
                break
    return emp or {}


@frappe.whitelist()
def search_employees(query: str = "", limit: int = 10):
    """Recherche floue d'employés actifs par nom ou matricule.

    Utilisé par les Web Forms quand l'utilisateur ne se souvient pas de
    son matricule. Retourne une liste légère (name, employee_name,
    department) — aucune donnée sensible.
    """
    query = (query or "").strip()
    if len(query) < 2:
        return []

    try:
        limit = max(1, min(int(limit), 25))
    except (TypeError, ValueError):
        limit = 10

    like = f"%{query}%"
    rows = frappe.db.sql(
        """
        SELECT name, employee_name, department
        FROM `tabEmployee`
        WHERE status = 'Active'
          AND (
                employee_name LIKE %(q)s
             OR name LIKE %(q)s
             OR employee_number LIKE %(q)s
             OR custom_matricule_kya LIKE %(q)s
          )
        ORDER BY
          CASE WHEN employee_name LIKE %(prefix)s THEN 0 ELSE 1 END,
          employee_name
        LIMIT %(limit)s
        """,
        {"q": like, "prefix": f"{query}%", "limit": limit},
        as_dict=True,
    )
    return rows or []

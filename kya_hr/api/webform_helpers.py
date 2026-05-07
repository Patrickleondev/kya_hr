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
    roles = set(frappe.get_roles(frappe.session.user))
    if not ({"System Manager", "HR Manager", "HR User", "Responsable RH"} & roles):
        frappe.throw(_("Vous n'êtes pas autorisé à rechercher d'autres employés."))

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


@frappe.whitelist()
def find_my_employee(query: str = ""):
    """Retourne uniquement l'Employee rattaché à l'utilisateur courant.

    Cette méthode aide un utilisateur qui ne connaît pas son matricule sans
    exposer l'annuaire complet. Elle ne renvoie un résultat que si le texte
    saisi correspond à son propre nom, matricule ou email.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return []

    query = (query or "").strip().lower()
    if len(query) < 2:
        return []

    fields = ["name", "employee_name", "department", "designation", "company_email", "personal_email", "user_id"]
    candidates = []

    for filters in (
        {"user_id": user, "status": "Active"},
        {"company_email": user, "status": "Active"},
        {"personal_email": user, "status": "Active"},
        {"prefered_email": user, "status": "Active"},
    ):
        emp = frappe.db.get_value("Employee", filters, fields, as_dict=True)
        if emp and emp.name not in {row.name for row in candidates}:
            candidates.append(emp)

    matches = []
    for emp in candidates:
        haystack = " ".join(
            str(emp.get(field) or "")
            for field in ("name", "employee_name", "department", "designation", "company_email", "personal_email")
        ).lower()
        if query in haystack:
            matches.append({
                "name": emp.name,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "designation": emp.designation,
            })

    return matches

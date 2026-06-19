# -*- coding: utf-8 -*-
"""Restriction de visibilité sur le DocType Attendance (présences).

Sans ceci, le rôle `Employee` a read=1 sans `if_owner` -> un employé verrait
TOUTES les présences. On limite : RH/Manager voient tout ; les autres ne voient
que leurs propres présences (+ celles de leurs subordonnés directs, utile aux
chefs d'équipe/service).

Wired via hooks.py :
    permission_query_conditions = { "Attendance": "kya_hr.attendance_permissions.attendance_query" }
    has_permission = { "Attendance": "kya_hr.attendance_permissions.attendance_has_permission" }
"""
import frappe

from kya_hr.employee_permissions import _user_is_privileged, _own_employee


def _allowed_employees(user):
    """Liste des Employee dont `user` peut voir les présences : la sienne + ses
    subordonnés directs (reports_to)."""
    own = _own_employee(user)
    if not own:
        return []
    subs = frappe.get_all("Employee", filters={"reports_to": own}, pluck="name") or []
    return [own, *subs]


def attendance_query(user):
    """Permission Query Condition : restreint la liste Attendance."""
    if _user_is_privileged(user):
        return ""
    allowed = _allowed_employees(user)
    if not allowed:
        return "1=0"
    vals = ", ".join(frappe.db.escape(e) for e in allowed)
    return f"`tabAttendance`.employee in ({vals})"


def attendance_has_permission(doc, ptype="read", user=None):
    """Has Permission : accès à une présence précise."""
    user = user or frappe.session.user
    if _user_is_privileged(user):
        return True
    allowed = set(_allowed_employees(user))
    if not allowed:
        return False
    emp = doc.employee if hasattr(doc, "employee") else frappe.db.get_value("Attendance", doc, "employee")
    return emp in allowed

# -*- coding: utf-8 -*-
# Fiche de Gestion des Congés Annuels — KYA RH
# Reproduit le format Excel "FICHE DE GESTION DES CONGES ANNUELS YYYY"
# 1 ligne par employé, jusqu'à 2 départs chronologiques.
import frappe
from frappe.utils import formatdate, getdate

LEAVE_TYPE_ANNUEL_CANDIDATES = ["Congé Annuel", "Congé Annuel KYA", "Annual Leave", "Privilege Leave"]


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "N°", "fieldname": "ord", "fieldtype": "Int", "width": 50},
        {"label": "Nom", "fieldname": "nom", "fieldtype": "Data", "width": 140},
        {"label": "Prénoms", "fieldname": "prenoms", "fieldtype": "Data", "width": 160},
        {"label": "Département", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": "Acquis", "fieldname": "acquis", "fieldtype": "Float", "width": 80, "precision": 0},
        {"label": "Anticipés", "fieldname": "anticipes", "fieldtype": "Float", "width": 90, "precision": 0},
        {"label": "Restants", "fieldname": "restants", "fieldtype": "Float", "width": 90, "precision": 0},
        {"label": "Date Départ 1", "fieldname": "depart_1", "fieldtype": "Date", "width": 110},
        {"label": "Date Reprise 1", "fieldname": "reprise_1", "fieldtype": "Date", "width": 110},
        {"label": "Jours pris 1", "fieldname": "jours_1", "fieldtype": "Float", "width": 90, "precision": 0},
        {"label": "Solde 1", "fieldname": "solde_1", "fieldtype": "Float", "width": 80, "precision": 0},
        {"label": "Date Départ 2", "fieldname": "depart_2", "fieldtype": "Date", "width": 110},
        {"label": "Date Reprise 2", "fieldname": "reprise_2", "fieldtype": "Date", "width": 110},
        {"label": "Jours pris 2", "fieldname": "jours_2", "fieldtype": "Float", "width": 90, "precision": 0},
        {"label": "Solde 2", "fieldname": "solde_2", "fieldtype": "Float", "width": 80, "precision": 0},
        {"label": "Statut", "fieldname": "statut", "fieldtype": "Data", "width": 110},
    ]


def _resolve_leave_type():
    """Trouve le Leave Type 'Congé Annuel' qui existe en base."""
    existing = set(frappe.get_all("Leave Type", pluck="name"))
    for cand in LEAVE_TYPE_ANNUEL_CANDIDATES:
        if cand in existing:
            return cand
    return None


def get_data(filters):
    year = int(filters.get("year") or frappe.utils.now_datetime().year)
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    leave_type = filters.get("leave_type") or _resolve_leave_type()

    emp_filters = {"status": "Active"}
    if filters.get("department"):
        emp_filters["department"] = filters["department"]
    if filters.get("employment_type"):
        emp_filters["employment_type"] = filters["employment_type"]
    else:
        emp_filters["employment_type"] = ["not in", ["Stage", "Intern"]]

    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "first_name", "last_name", "department"],
        order_by="last_name asc, first_name asc",
    )

    rows = []
    for idx, emp in enumerate(employees, start=1):
        # Acquis = somme des allocations validées de l'année
        alloc_filters = {
            "employee": emp.name,
            "docstatus": 1,
            "from_date": [">=", year_start],
            "to_date": ["<=", year_end],
        }
        if leave_type:
            alloc_filters["leave_type"] = leave_type
        acquis = frappe.db.get_value(
            "Leave Allocation",
            alloc_filters,
            "SUM(total_leaves_allocated)",
        ) or 0

        # Pris (toutes Leave Applications validées de l'année)
        la_filters = {
            "employee": emp.name,
            "docstatus": 1,
            "status": "Approved",
            "from_date": [">=", year_start],
            "to_date": ["<=", year_end],
        }
        if leave_type:
            la_filters["leave_type"] = leave_type
        applications = frappe.get_all(
            "Leave Application",
            filters=la_filters,
            fields=["name", "from_date", "to_date", "total_leave_days", "workflow_state", "status"],
            order_by="from_date asc",
        )

        anticipes = sum((a.total_leave_days or 0) for a in applications)
        restants = (acquis or 0) - anticipes

        d1 = applications[0] if len(applications) >= 1 else None
        d2 = applications[1] if len(applications) >= 2 else None

        jours_1 = (d1.total_leave_days if d1 else 0) or 0
        jours_2 = (d2.total_leave_days if d2 else 0) or 0
        solde_1 = (acquis or 0) - jours_1
        solde_2 = solde_1 - jours_2

        # Nom / Prénoms : utilise last_name / first_name si présents, sinon split employee_name
        nom = (emp.last_name or "").strip()
        prenoms = (emp.first_name or "").strip()
        if not nom and emp.employee_name:
            parts = emp.employee_name.strip().split(" ", 1)
            nom = parts[0]
            prenoms = parts[1] if len(parts) > 1 else ""

        # Statut synthétique
        statut = "Pas de congé"
        if d2:
            statut = "2 départs"
        elif d1:
            statut = "1 départ"

        rows.append({
            "ord": idx,
            "nom": nom,
            "prenoms": prenoms,
            "department": emp.department,
            "acquis": acquis,
            "anticipes": anticipes,
            "restants": restants,
            "depart_1": d1.from_date if d1 else None,
            "reprise_1": d1.to_date if d1 else None,
            "jours_1": jours_1 if d1 else 0,
            "solde_1": solde_1 if d1 else (acquis or 0),
            "depart_2": d2.from_date if d2 else None,
            "reprise_2": d2.to_date if d2 else None,
            "jours_2": jours_2 if d2 else 0,
            "solde_2": solde_2 if d2 else (solde_1 if d1 else (acquis or 0)),
            "statut": statut,
        })

    return rows


def get_chart(data):
    if not data:
        return None
    dept = {}
    for d in data:
        k = d.get("department") or "Non défini"
        dept[k] = dept.get(k, 0) + (d.get("anticipes") or 0)
    return {
        "data": {
            "labels": list(dept.keys()),
            "datasets": [{"name": "Jours pris", "values": list(dept.values())}],
        },
        "type": "bar",
        "colors": ["#0d7377"],
    }


def get_summary(data):
    if not data:
        return []
    total_acquis = sum((d.get("acquis") or 0) for d in data)
    total_pris = sum((d.get("anticipes") or 0) for d in data)
    total_restants = sum((d.get("restants") or 0) for d in data)
    employes_avec_conge = sum(1 for d in data if (d.get("anticipes") or 0) > 0)
    return [
        {"label": "Effectif", "value": len(data), "datatype": "Int", "indicator": "blue"},
        {"label": "Total Acquis", "value": total_acquis, "datatype": "Float", "indicator": "blue"},
        {"label": "Total Pris", "value": total_pris, "datatype": "Float", "indicator": "orange"},
        {"label": "Solde Global", "value": total_restants, "datatype": "Float", "indicator": "green"},
        {"label": "Employés en congé", "value": employes_avec_conge, "datatype": "Int", "indicator": "purple"},
    ]

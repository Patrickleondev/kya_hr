# Copyright (c) 2026, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Département", "fieldname": "department", "fieldtype": "Link",
         "options": "Department", "width": 180},
        {"label": "Employé", "fieldname": "employee", "fieldtype": "Link",
         "options": "Employee", "width": 110},
        {"label": "Nom", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "Statut", "fieldname": "workflow_state", "fieldtype": "Data", "width": 130},

        {"label": "Solde N-1", "fieldname": "solde_n1", "fieldtype": "Float",
         "width": 90, "precision": 1},
        {"label": "Jours acquis", "fieldname": "jours_acquis", "fieldtype": "Float",
         "width": 100, "precision": 1},
        {"label": "Congés oblig.", "fieldname": "conges_obligatoires", "fieldtype": "Int",
         "width": 100},
        {"label": "Solde dispo.", "fieldname": "solde_disponible", "fieldtype": "Float",
         "width": 100, "precision": 1},

        {"label": "P1 Départ", "fieldname": "p1_debut", "fieldtype": "Date", "width": 100},
        {"label": "P1 Reprise", "fieldname": "p1_fin", "fieldtype": "Date", "width": 100},
        {"label": "P1 Jours", "fieldname": "p1_jours", "fieldtype": "Int", "width": 80},

        {"label": "P2 Départ", "fieldname": "p2_debut", "fieldtype": "Date", "width": 100},
        {"label": "P2 Reprise", "fieldname": "p2_fin", "fieldtype": "Date", "width": 100},
        {"label": "P2 Jours", "fieldname": "p2_jours", "fieldtype": "Int", "width": 80},

        {"label": "P3 Départ", "fieldname": "p3_debut", "fieldtype": "Date", "width": 100},
        {"label": "P3 Reprise", "fieldname": "p3_fin", "fieldtype": "Date", "width": 100},
        {"label": "P3 Jours", "fieldname": "p3_jours", "fieldtype": "Int", "width": 80},

        {"label": "P4 Départ", "fieldname": "p4_debut", "fieldtype": "Date", "width": 100},
        {"label": "P4 Reprise", "fieldname": "p4_fin", "fieldtype": "Date", "width": 100},
        {"label": "P4 Jours", "fieldname": "p4_jours", "fieldtype": "Int", "width": 80},

        {"label": "Total jours", "fieldname": "total_jours", "fieldtype": "Int", "width": 100},
        {"label": "Monétisation", "fieldname": "jours_monetisation", "fieldtype": "Int", "width": 110},
        {"label": "Solde final", "fieldname": "solde_final", "fieldtype": "Float",
         "width": 100, "precision": 1},

        {"label": "Référence", "fieldname": "name", "fieldtype": "Link",
         "options": "Planning Conge", "width": 130},
    ]


def get_data(filters):
    annee = int(filters.get("annee") or frappe.utils.now_datetime().year)

    conditions = ["pc.annee = %(annee)s"]
    values = {"annee": annee}

    if filters.get("department"):
        conditions.append("pc.department = %(department)s")
        values["department"] = filters["department"]

    if filters.get("workflow_state"):
        conditions.append("pc.workflow_state = %(workflow_state)s")
        values["workflow_state"] = filters["workflow_state"]

    where = " AND ".join(conditions)

    plannings = frappe.db.sql(
        f"""
        SELECT
            pc.name, pc.employee, pc.employee_name, pc.department,
            pc.workflow_state, pc.statut,
            pc.solde_n1, pc.jours_acquis, pc.conges_obligatoires,
            pc.solde_disponible, pc.solde_final,
            pc.total_jours, pc.jours_monetisation
        FROM `tabPlanning Conge` pc
        WHERE pc.docstatus < 2
          AND {where}
        ORDER BY pc.department, pc.employee_name
        """,
        values,
        as_dict=True,
    )

    result = []
    for p in plannings:
        row = dict(p)
        periodes = frappe.db.sql(
            """
            SELECT date_debut, date_fin, nb_jours, idx
            FROM `tabPlanning Conge Periode`
            WHERE parent = %(name)s
            ORDER BY idx ASC
            LIMIT 4
            """,
            {"name": p.name},
            as_dict=True,
        )

        for i, per in enumerate(periodes, start=1):
            row[f"p{i}_debut"] = per.date_debut
            row[f"p{i}_fin"] = per.date_fin
            row[f"p{i}_jours"] = per.nb_jours

        row["workflow_state"] = p.workflow_state or p.statut or "Brouillon"
        result.append(row)

    return result


def get_chart(data):
    if not data:
        return None

    by_dept = {}
    for d in data:
        dept = d.get("department") or "Non défini"
        if dept not in by_dept:
            by_dept[dept] = {"planifies": 0, "monetises": 0}
        by_dept[dept]["planifies"] += d.get("total_jours") or 0
        by_dept[dept]["monetises"] += d.get("jours_monetisation") or 0

    return {
        "data": {
            "labels": list(by_dept.keys()),
            "datasets": [
                {"name": "Jours planifiés",
                 "values": [v["planifies"] for v in by_dept.values()]},
                {"name": "Jours monétisés",
                 "values": [v["monetises"] for v in by_dept.values()]},
            ],
        },
        "type": "bar",
        "colors": ["#009688", "#ff9800"],
    }


def get_summary(data):
    if not data:
        return []
    total_planifies = sum(d.get("total_jours") or 0 for d in data)
    total_monet = sum(d.get("jours_monetisation") or 0 for d in data)
    total_employes = len({d.get("employee") for d in data if d.get("employee")})
    approuves = sum(1 for d in data if d.get("workflow_state") == "Approuvé")

    return [
        {"label": "Employés", "value": total_employes, "datatype": "Int", "indicator": "blue"},
        {"label": "Plannings approuvés", "value": approuves, "datatype": "Int",
         "indicator": "green"},
        {"label": "Total jours planifiés", "value": total_planifies, "datatype": "Int",
         "indicator": "orange"},
        {"label": "Total jours monétisés", "value": total_monet, "datatype": "Int",
         "indicator": "purple"},
    ]

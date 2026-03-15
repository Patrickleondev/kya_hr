import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data, filters)
    report_summary = get_summary(data)
    return columns, data, None, chart, report_summary


def get_columns():
    return [
        {"label": "ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 100},
        {"label": "Nom Complet", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Genre", "fieldname": "gender", "fieldtype": "Data", "width": 80},
        {"label": "Département", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 160},
        {"label": "Maître de Stage", "fieldname": "reports_to_name", "fieldtype": "Data", "width": 160},
        {"label": "Date Début", "fieldname": "date_of_joining", "fieldtype": "Date", "width": 110},
        {"label": "Durée (jours)", "fieldname": "duree_jours", "fieldtype": "Int", "width": 100},
        {"label": "Permissions", "fieldname": "nb_permissions", "fieldtype": "Int", "width": 100},
        {"label": "Perm. Approuvées", "fieldname": "nb_perm_approved", "fieldtype": "Int", "width": 120},
        {"label": "Bilans", "fieldname": "nb_bilans", "fieldtype": "Int", "width": 80},
        {"label": "Présences (mois)", "fieldname": "nb_presences", "fieldtype": "Int", "width": 120},
        {"label": "Absences (mois)", "fieldname": "nb_absences", "fieldtype": "Int", "width": 110},
        {"label": "Statut", "fieldname": "status", "fieldtype": "Data", "width": 80},
    ]


def get_data(filters):
    conditions = "WHERE e.employment_type = 'Stage'"
    values = {}

    if filters.get("department"):
        conditions += " AND e.department = %(department)s"
        values["department"] = filters["department"]

    if filters.get("gender"):
        conditions += " AND e.gender = %(gender)s"
        values["gender"] = filters["gender"]

    if filters.get("status"):
        conditions += " AND e.status = %(status)s"
        values["status"] = filters["status"]
    else:
        conditions += " AND e.status = 'Active'"

    employees = frappe.db.sql("""
        SELECT
            e.name as employee,
            e.employee_name,
            IFNULL(e.gender, '-') as gender,
            e.department,
            e.date_of_joining,
            e.status,
            IFNULL(rt.employee_name, '-') as reports_to_name,
            DATEDIFF(CURDATE(), e.date_of_joining) as duree_jours
        FROM `tabEmployee` e
        LEFT JOIN `tabEmployee` rt ON rt.name = e.reports_to
        {conditions}
        ORDER BY e.department, e.employee_name
    """.format(conditions=conditions), values, as_dict=True)

    now = frappe.utils.now_datetime()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    month_end = now.strftime("%Y-%m-%d")

    for emp in employees:
        emp_id = emp["employee"]

        # Permission count
        perm_total = frappe.db.count("Permission Sortie Stagiaire", {"employee": emp_id}) or 0
        perm_approved = frappe.db.count("Permission Sortie Stagiaire", {
            "employee": emp_id, "workflow_state": "Approuvé"
        }) or 0
        emp["nb_permissions"] = perm_total
        emp["nb_perm_approved"] = perm_approved

        # Bilan count
        emp["nb_bilans"] = frappe.db.count("Bilan Fin de Stage", {"employee": emp_id}) or 0

        # Attendance this month
        emp["nb_presences"] = frappe.db.count("Attendance", {
            "employee": emp_id,
            "status": "Present",
            "attendance_date": ["between", [month_start, month_end]],
        }) or 0

        emp["nb_absences"] = frappe.db.count("Attendance", {
            "employee": emp_id,
            "status": "Absent",
            "attendance_date": ["between", [month_start, month_end]],
        }) or 0

    return employees


def get_chart(data, filters):
    chart_type = filters.get("chart_type") if filters else None

    if chart_type == "Genre":
        return _chart_by_gender(data)
    elif chart_type == "Présences":
        return _chart_attendance(data)
    else:
        return _chart_by_department(data)


def _chart_by_department(data):
    dept_count = {}
    for row in data:
        d = row.get("department") or "Non défini"
        dept_count[d] = dept_count.get(d, 0) + 1

    labels = list(dept_count.keys())
    values = list(dept_count.values())
    return {
        "data": {"labels": labels, "datasets": [{"name": "Stagiaires", "values": values}]},
        "type": "bar",
        "colors": ["#009688"],
        "barOptions": {"stacked": False},
    }


def _chart_by_gender(data):
    gender_count = {}
    for row in data:
        g = row.get("gender") or "Non défini"
        gender_count[g] = gender_count.get(g, 0) + 1

    labels = list(gender_count.keys())
    values = list(gender_count.values())
    return {
        "data": {"labels": labels, "datasets": [{"name": "Stagiaires", "values": values}]},
        "type": "donut",
        "colors": ["#1a3a5c", "#e74c3c", "#95a5a6"],
    }


def _chart_attendance(data):
    labels = []
    presents = []
    absents = []
    for row in data:
        labels.append(row.get("employee_name", "")[:15])
        presents.append(row.get("nb_presences", 0))
        absents.append(row.get("nb_absences", 0))

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Présences", "values": presents},
                {"name": "Absences", "values": absents},
            ],
        },
        "type": "bar",
        "colors": ["#27ae60", "#e74c3c"],
        "barOptions": {"stacked": True},
    }


def get_summary(data):
    total = len(data)
    men = sum(1 for d in data if d.get("gender") in ("Male", "Homme", "Masculin", "M"))
    women = sum(1 for d in data if d.get("gender") in ("Female", "Femme", "Féminin", "F"))
    total_perm = sum(d.get("nb_permissions", 0) for d in data)
    total_bilans = sum(d.get("nb_bilans", 0) for d in data)
    total_presences = sum(d.get("nb_presences", 0) for d in data)
    departments = len(set(d.get("department") for d in data if d.get("department")))

    return [
        {"value": total, "label": "Total Stagiaires", "datatype": "Int", "indicator": "blue"},
        {"value": men, "label": "Hommes", "datatype": "Int", "indicator": "blue"},
        {"value": women, "label": "Femmes", "datatype": "Int", "indicator": "pink"},
        {"value": departments, "label": "Départements", "datatype": "Int", "indicator": "green"},
        {"value": total_perm, "label": "Permissions totales", "datatype": "Int", "indicator": "orange"},
        {"value": total_bilans, "label": "Bilans soumis", "datatype": "Int", "indicator": "green"},
        {"value": total_presences, "label": "Présences ce mois", "datatype": "Int", "indicator": "green"},
    ]

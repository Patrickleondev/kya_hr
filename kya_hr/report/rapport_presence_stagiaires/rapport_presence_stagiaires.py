import frappe
from frappe.utils import getdate, today, get_first_day


def execute(filters=None):
    if not filters:
        filters = {}
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart(data, filters)
    report_summary = get_summary(data)
    return columns, data, None, chart, report_summary


def get_columns(filters):
    period = filters.get("period", "Journalier")
    cols = [
        {"label": "Stagiaire", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 100},
        {"label": "Nom", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Département", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 160},
        {"label": "Maître de Stage", "fieldname": "reports_to_name", "fieldtype": "Data", "width": 160},
    ]
    if period == "Journalier":
        cols += [
            {"label": "Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 110},
            {"label": "Statut", "fieldname": "status", "fieldtype": "Data", "width": 100},
            {"label": "Entrée", "fieldname": "first_in", "fieldtype": "Time", "width": 90},
            {"label": "Sortie", "fieldname": "last_out", "fieldtype": "Time", "width": 90},
            {"label": "Heures", "fieldname": "working_hours", "fieldtype": "Float", "width": 80, "precision": 1},
        ]
    else:
        cols += [
            {"label": "Présent", "fieldname": "present", "fieldtype": "Int", "width": 80},
            {"label": "Absent", "fieldname": "absent", "fieldtype": "Int", "width": 80},
            {"label": "En congé", "fieldname": "on_leave", "fieldtype": "Int", "width": 80},
            {"label": "Total jours", "fieldname": "total_days", "fieldtype": "Int", "width": 90},
            {"label": "Taux présence", "fieldname": "presence_rate", "fieldtype": "Percent", "width": 110},
            {"label": "Permissions", "fieldname": "permissions", "fieldtype": "Int", "width": 90},
        ]
    return cols


def get_data(filters):
    period = filters.get("period", "Journalier")
    conditions = ["e.status = 'Active'", "e.employment_type = 'Stage'"]
    values = {}

    if filters.get("department"):
        conditions.append("e.department = %(department)s")
        values["department"] = filters["department"]

    if period == "Journalier":
        date = getdate(filters.get("date") or today())
        values["att_date"] = date
        data = frappe.db.sql("""
            SELECT
                e.name as employee,
                e.employee_name,
                e.department,
                IFNULL(rt.employee_name, '-') as reports_to_name,
                a.attendance_date,
                IFNULL(a.status, 'Non pointé') as status,
                a.working_hours
            FROM `tabEmployee` e
            LEFT JOIN `tabEmployee` rt ON rt.name = e.reports_to
            LEFT JOIN `tabAttendance` a ON a.employee = e.name
                AND a.attendance_date = %(att_date)s AND a.docstatus = 1
            WHERE {conditions}
            ORDER BY e.department, e.employee_name
        """.format(conditions=" AND ".join(conditions)), values, as_dict=True)

        for row in data:
            if not row.get("attendance_date"):
                row["attendance_date"] = date
            checkins = frappe.db.sql("""
                SELECT MIN(time) as first_in, MAX(time) as last_out
                FROM `tabEmployee Checkin`
                WHERE employee = %s AND DATE(time) = %s
            """, (row["employee"], date), as_dict=True)
            if checkins and checkins[0].get("first_in"):
                row["first_in"] = str(checkins[0]["first_in"]).split(" ")[-1][:5] if checkins[0]["first_in"] else ""
                row["last_out"] = str(checkins[0]["last_out"]).split(" ")[-1][:5] if checkins[0]["last_out"] else ""
        return data
    else:
        from_date = getdate(filters.get("from_date") or get_first_day(today()))
        to_date = getdate(filters.get("to_date") or today())
        values["from_date"] = from_date
        values["to_date"] = to_date

        employees = frappe.db.sql("""
            SELECT e.name as employee, e.employee_name, e.department,
                IFNULL(rt.employee_name, '-') as reports_to_name
            FROM `tabEmployee` e
            LEFT JOIN `tabEmployee` rt ON rt.name = e.reports_to
            WHERE {conditions}
            ORDER BY e.department, e.employee_name
        """.format(conditions=" AND ".join(conditions)), values, as_dict=True)

        for emp in employees:
            att = frappe.db.sql("""
                SELECT status, COUNT(*) as cnt
                FROM `tabAttendance`
                WHERE employee = %s AND attendance_date BETWEEN %s AND %s AND docstatus = 1
                GROUP BY status
            """, (emp["employee"], from_date, to_date), as_dict=True)

            counts = {a["status"]: a["cnt"] for a in att}
            emp["present"] = counts.get("Present", 0)
            emp["absent"] = counts.get("Absent", 0)
            emp["on_leave"] = counts.get("On Leave", 0)
            emp["total_days"] = emp["present"] + emp["absent"] + emp["on_leave"]
            emp["presence_rate"] = round(emp["present"] / emp["total_days"] * 100, 1) if emp["total_days"] else 0
            emp["permissions"] = frappe.db.count("Permission Sortie Stagiaire", {
                "employee": emp["employee"],
                "workflow_state": "Approuvé",
            }) or 0
        return employees


def get_chart(data, filters):
    period = filters.get("period", "Journalier")
    if period == "Journalier":
        status_counts = {}
        for row in data:
            s = row.get("status", "Non pointé")
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "data": {
                "labels": list(status_counts.keys()),
                "datasets": [{"values": list(status_counts.values())}],
            },
            "type": "donut",
            "colors": ["#36a2eb", "#ff6384", "#ff9f40", "#4bc0c0"],
        }
    else:
        departments = {}
        for row in data:
            dept = row.get("department") or "Sans département"
            if dept not in departments:
                departments[dept] = {"present": 0, "absent": 0}
            departments[dept]["present"] += row.get("present", 0)
            departments[dept]["absent"] += row.get("absent", 0)
        return {
            "data": {
                "labels": list(departments.keys()),
                "datasets": [
                    {"name": "Présent", "values": [d["present"] for d in departments.values()]},
                    {"name": "Absent", "values": [d["absent"] for d in departments.values()]},
                ],
            },
            "type": "bar",
            "colors": ["#36a2eb", "#ff6384"],
        }


def get_summary(data):
    total = len(data)
    if not total:
        return []
    if "status" in (data[0] if data else {}):
        present = sum(1 for r in data if r.get("status") == "Present")
        absent = sum(1 for r in data if r.get("status") == "Absent")
        return [
            {"value": total, "label": "Total stagiaires", "datatype": "Int"},
            {"value": present, "label": "Présents", "datatype": "Int", "indicator": "green"},
            {"value": absent, "label": "Absents", "datatype": "Int", "indicator": "red"},
        ]
    else:
        tot_present = sum(r.get("present", 0) for r in data)
        tot_absent = sum(r.get("absent", 0) for r in data)
        avg_rate = round(sum(r.get("presence_rate", 0) for r in data) / total, 1) if total else 0
        return [
            {"value": total, "label": "Stagiaires", "datatype": "Int"},
            {"value": tot_present, "label": "Jours présence", "datatype": "Int", "indicator": "green"},
            {"value": tot_absent, "label": "Jours absence", "datatype": "Int", "indicator": "red"},
            {"value": avg_rate, "label": "Taux moyen (%)", "datatype": "Percent", "indicator": "blue"},
        ]

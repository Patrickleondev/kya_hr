import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Employé", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 100},
        {"label": "Nom", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Département", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": "Type de Congé", "fieldname": "leave_type", "fieldtype": "Link", "options": "Leave Type", "width": 160},
        {"label": "Jours Alloués", "fieldname": "total_allocated", "fieldtype": "Float", "width": 110},
        {"label": "Jours Pris", "fieldname": "total_taken", "fieldtype": "Float", "width": 100},
        {"label": "Solde Restant", "fieldname": "balance", "fieldtype": "Float", "width": 110},
        {"label": "Dernière Période", "fieldname": "last_leave", "fieldtype": "Data", "width": 200},
        {"label": "Statut Dernier Congé", "fieldname": "last_status", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    conditions = ""
    values = {}

    if filters.get("employee"):
        conditions += " AND la.employee = %(employee)s"
        values["employee"] = filters["employee"]
    if filters.get("department"):
        conditions += " AND la.department = %(department)s"
        values["department"] = filters["department"]
    if filters.get("leave_type"):
        conditions += " AND la.leave_type = %(leave_type)s"
        values["leave_type"] = filters["leave_type"]

    year = filters.get("year") or frappe.utils.now_datetime().year
    values["year_start"] = f"{year}-01-01"
    values["year_end"] = f"{year}-12-31"

    # Allocations for the year
    allocations = frappe.db.sql("""
        SELECT
            employee, employee_name, department, leave_type,
            SUM(total_leaves_allocated) as total_allocated
        FROM `tabLeave Allocation`
        WHERE docstatus = 1
            AND from_date >= %(year_start)s
            AND to_date <= %(year_end)s
            {conditions}
        GROUP BY employee, leave_type
    """.format(conditions=conditions.replace("la.", "")), values, as_dict=True)

    result = []
    for alloc in allocations:
        taken_vals = {
            "employee": alloc.employee,
            "leave_type": alloc.leave_type,
            "year_start": values["year_start"],
            "year_end": values["year_end"],
        }
        taken = frappe.db.sql("""
            SELECT
                COALESCE(SUM(total_leave_days), 0) as total_taken
            FROM `tabLeave Application`
            WHERE docstatus = 1
                AND employee = %(employee)s
                AND leave_type = %(leave_type)s
                AND from_date >= %(year_start)s
                AND to_date <= %(year_end)s
                AND status = 'Approved'
        """, taken_vals, as_dict=True)

        total_taken = taken[0].total_taken if taken else 0

        # Last leave application
        last = frappe.db.sql("""
            SELECT from_date, to_date, status, workflow_state
            FROM `tabLeave Application`
            WHERE employee = %(employee)s
                AND leave_type = %(leave_type)s
                AND from_date >= %(year_start)s
            ORDER BY from_date DESC LIMIT 1
        """, taken_vals, as_dict=True)

        last_leave = ""
        last_status = ""
        if last:
            last_leave = f"{frappe.utils.formatdate(last[0].from_date)} → {frappe.utils.formatdate(last[0].to_date)}"
            last_status = last[0].workflow_state or last[0].status

        result.append({
            "employee": alloc.employee,
            "employee_name": alloc.employee_name,
            "department": alloc.department,
            "leave_type": alloc.leave_type,
            "total_allocated": alloc.total_allocated,
            "total_taken": total_taken,
            "balance": alloc.total_allocated - total_taken,
            "last_leave": last_leave,
            "last_status": last_status,
        })

    return result


def get_chart(data):
    if not data:
        return None

    dept_taken = {}
    for d in data:
        dept = d.get("department") or "Non défini"
        dept_taken[dept] = dept_taken.get(dept, 0) + d.get("total_taken", 0)

    return {
        "data": {
            "labels": list(dept_taken.keys()),
            "datasets": [{"name": "Jours Pris", "values": list(dept_taken.values())}],
        },
        "type": "bar",
        "colors": ["#fc4f51"],
    }


def get_summary(data):
    if not data:
        return []
    total_alloc = sum(d.get("total_allocated", 0) for d in data)
    total_taken = sum(d.get("total_taken", 0) for d in data)
    total_balance = sum(d.get("balance", 0) for d in data)
    return [
        {"label": "Total Alloués", "value": total_alloc, "datatype": "Float", "indicator": "blue"},
        {"label": "Total Pris", "value": total_taken, "datatype": "Float", "indicator": "orange"},
        {"label": "Solde Global", "value": total_balance, "datatype": "Float", "indicator": "green"},
    ]

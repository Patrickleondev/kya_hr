import frappe
from frappe.utils import today, now_datetime, add_days, getdate, get_datetime


# ═══════════════════════════════════════════════════════════════
#  QUICK LINKS (HRMS Mobile)
# ═══════════════════════════════════════════════════════════════

# Types d'emploi considérés comme "personnel interne"
EMPLOYEE_TYPES = {"CDI", "CDD", "Full-time", "Part-time", "Probation", "Contract"}
# Types considérés comme "stagiaires"
STAGE_TYPES = {"Stage", "Intern", "Apprentice"}
# Types considérés comme "prestataires"
PRESTATAIRE_TYPES = {"Prestataire de service"}


def _get_user_category(employment_type):
    """Détermine la catégorie utilisateur à partir du type d'emploi."""
    if employment_type in STAGE_TYPES:
        return "stage"
    elif employment_type in PRESTATAIRE_TYPES:
        return "prestataire"
    else:
        return "employee"


@frappe.whitelist()
def get_kya_quick_links():
    """Return KYA-specific quick links based on current user's employment type."""
    user = frappe.session.user
    if user == "Guest":
        return []

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employment_type", "employee_name"],
        as_dict=True,
    )

    if not employee:
        return []

    category = _get_user_category(employee.get("employment_type") or "")
    links = []

    if category == "stage":
        # --- Stagiaire links ---
        links.append({
            "title": "Permission de Sortie",
            "description": "Demander une permission de sortie",
            "url": "/permission-sortie-stagiaire",
            "emoji": "🚪",
        })
        links.append({
            "title": "Bilan de Stage",
            "description": "Remplir le bilan de fin de stage",
            "url": "/bilan-fin-de-stage",
            "emoji": "📝",
        })
    elif category == "prestataire":
        # --- Prestataire de service links ---
        links.append({
            "title": "Permission de Sortie",
            "description": "Demander une permission de sortie",
            "url": "/permission-sortie-employe",
            "emoji": "🚪",
        })
    else:
        # --- Employee (CDI/CDD) links ---
        links.append({
            "title": "Permission de Sortie",
            "description": "Demander une permission de sortie",
            "url": "/permission-sortie-employe",
            "emoji": "🚪",
        })
        links.append({
            "title": "Planning de Congé",
            "description": "Planifier vos périodes de congé annuelles",
            "url": "/planning-conge",
            "emoji": "📅",
        })

    # --- Common links (all types) ---
    links.append({
        "title": "PV Sortie Matériel",
        "description": "Déclarer une sortie de matériel",
        "url": "/pv-sortie-materiel",
        "emoji": "📦",
    })
    links.append({
        "title": "Demande d\'Achat",
        "description": "Soumettre une demande d\'achat",
        "url": "/demande-achat",
        "emoji": "🛒",
    })

    return links


@frappe.whitelist()
def get_user_category():
    """Return the current user's category (stage/prestataire/employee).
    Used by the HRMS frontend to apply UI filters."""
    user = frappe.session.user
    if user == "Guest":
        return {"category": "guest", "employment_type": None}

    emp = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employment_type"],
        as_dict=True,
    )
    if not emp:
        return {"category": "unknown", "employment_type": None}

    return {
        "category": _get_user_category(emp.employment_type or ""),
        "employment_type": emp.employment_type,
    }


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW ACTIONS (Web Form Mobile Approval)
# ═══════════════════════════════════════════════════════════════

ALLOWED_DOCTYPES = {
    "Permission Sortie Stagiaire",
    "Permission Sortie Employe",
    "PV Sortie Materiel",
    "Planning Conge",
    "Demande Achat KYA",
}


@frappe.whitelist()
def get_kya_workflow_actions(doctype, docname):
    """Get available workflow actions for the current user on a document.
    Returns current workflow_state and list of possible actions."""
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw("Type de document non autorisé", frappe.PermissionError)

    doc = frappe.get_doc(doctype, docname)
    doc.check_permission("read")

    from frappe.model.workflow import get_transitions

    transitions = get_transitions(doc, raise_exception=False)
    actions = []
    for t in transitions:
        actions.append({
            "action": t.get("action"),
            "next_state": t.get("next_state"),
        })

    return {
        "workflow_state": doc.workflow_state,
        "docstatus": doc.docstatus,
        "actions": actions,
    }


@frappe.whitelist()
def apply_kya_workflow_action(doctype, docname, action):
    """Apply a workflow action from the web form (mobile approval)."""
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw("Type de document non autorisé", frappe.PermissionError)

    from frappe.model.workflow import apply_workflow

    doc = frappe.get_doc(doctype, docname)
    doc.check_permission("write")
    apply_workflow(doc, action)

    return {
        "status": "success",
        "workflow_state": doc.workflow_state,
        "docstatus": doc.docstatus,
    }


# ═══════════════════════════════════════════════════════════════
#  BIOMETRIC ATTENDANCE API (for frontend dashboard)
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_attendance_summary(from_date=None, to_date=None, department=None):
    """Get attendance summary (present, absent, late, half day) for a date range."""
    if not from_date:
        from_date = getdate(today()).replace(day=1).isoformat()
    if not to_date:
        to_date = today()

    filters = {
        "attendance_date": ["between", [from_date, to_date]],
        "docstatus": 1,
    }
    if department:
        filters["department"] = department

    summary = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
          AND docstatus = 1
          {dept_filter}
        GROUP BY status
    """.format(
        dept_filter="AND department = %(department)s" if department else ""
    ), {
        "from_date": from_date,
        "to_date": to_date,
        "department": department,
    }, as_dict=True)

    daily = frappe.db.sql("""
        SELECT attendance_date, status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE attendance_date BETWEEN %(from_date)s AND %(to_date)s
          AND docstatus = 1
          {dept_filter}
        GROUP BY attendance_date, status
        ORDER BY attendance_date
    """.format(
        dept_filter="AND department = %(department)s" if department else ""
    ), {
        "from_date": from_date,
        "to_date": to_date,
        "department": department,
    }, as_dict=True)

    emp_filters = {"status": "Active"}
    if department:
        emp_filters["department"] = department
    total_employees = frappe.db.count("Employee", emp_filters)

    departments = frappe.db.sql_list(
        "SELECT DISTINCT department FROM `tabEmployee` WHERE status='Active' AND department IS NOT NULL"
    )

    return {
        "from_date": from_date,
        "to_date": to_date,
        "total_employees": total_employees,
        "summary": {row.status: row.count for row in summary},
        "daily_breakdown": daily,
        "departments": departments,
    }


@frappe.whitelist()
def get_employee_checkins(employee=None, from_date=None, to_date=None,
                          department=None, limit_page_length=100, limit_start=0):
    """Get Employee Checkin logs for attendance tracking."""
    if not from_date:
        from_date = today()
    if not to_date:
        to_date = today()

    filters = {
        "time": ["between", [
            f"{from_date} 00:00:00",
            f"{to_date} 23:59:59",
        ]],
    }
    if employee:
        filters["employee"] = employee
    if department:
        filters["department"] = department

    checkins = frappe.get_all(
        "Employee Checkin",
        filters=filters,
        fields=[
            "name", "employee", "employee_name", "department",
            "time", "log_type", "device_id",
            "attendance", "shift",
        ],
        order_by="time desc",
        limit_page_length=int(limit_page_length),
        limit_start=int(limit_start),
    )

    total = frappe.db.count("Employee Checkin", filters)

    return {
        "data": checkins,
        "total": total,
        "from_date": from_date,
        "to_date": to_date,
    }


@frappe.whitelist()
def get_attendance_dashboard(date=None, department=None):
    """Get real-time attendance dashboard data for a specific date."""
    if not date:
        date = today()

    emp_filters = {"status": "Active"}
    if department:
        emp_filters["department"] = department

    all_employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "department", "designation", "image"],
    )
    emp_ids = [e.name for e in all_employees]
    emp_map = {e.name: e for e in all_employees}

    att_records = frappe.get_all(
        "Attendance",
        filters={
            "attendance_date": date,
            "docstatus": 1,
            "employee": ["in", emp_ids] if emp_ids else ["in", ["__none__"]],
        },
        fields=["employee", "status", "leave_type", "late_entry", "early_exit"],
    )
    att_map = {a.employee: a for a in att_records}

    checkins = frappe.db.sql("""
        SELECT employee,
               MIN(CASE WHEN log_type = 'IN' THEN time END) as first_in,
               MAX(CASE WHEN log_type = 'OUT' THEN time END) as last_out,
               COUNT(*) as total_punches
        FROM `tabEmployee Checkin`
        WHERE DATE(time) = %(date)s
          AND employee IN %(employees)s
        GROUP BY employee
    """, {
        "date": date,
        "employees": emp_ids or ["__none__"],
    }, as_dict=True) if emp_ids else []
    checkin_map = {c.employee: c for c in checkins}

    present = []
    absent = []
    on_leave = []
    late = []

    for emp_id in emp_ids:
        emp = emp_map[emp_id]
        att = att_map.get(emp_id)
        ci = checkin_map.get(emp_id)

        entry = {
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "department": emp.department,
            "designation": emp.designation,
            "image": emp.image,
            "first_in": str(ci.first_in) if ci and ci.first_in else None,
            "last_out": str(ci.last_out) if ci and ci.last_out else None,
            "total_punches": ci.total_punches if ci else 0,
        }

        if att:
            entry["status"] = att.status
            entry["leave_type"] = att.leave_type
            entry["late_entry"] = att.late_entry
            entry["early_exit"] = att.early_exit

            if att.status == "On Leave":
                on_leave.append(entry)
            elif att.status in ("Present", "Half Day", "Work From Home"):
                present.append(entry)
                if att.late_entry:
                    late.append(entry)
            else:
                absent.append(entry)
        else:
            entry["status"] = "Absent"
            absent.append(entry)

    return {
        "date": date,
        "department": department,
        "stats": {
            "total": len(emp_ids),
            "present": len(present),
            "absent": len(absent),
            "on_leave": len(on_leave),
            "late": len(late),
        },
        "present": present,
        "absent": absent,
        "on_leave": on_leave,
        "late": late,
    }


@frappe.whitelist()
def get_department_attendance_stats(from_date=None, to_date=None):
    """Get attendance breakdown by department for a date range."""
    if not from_date:
        from_date = getdate(today()).replace(day=1).isoformat()
    if not to_date:
        to_date = today()

    stats = frappe.db.sql("""
        SELECT
            e.department,
            a.status,
            COUNT(*) as count
        FROM `tabAttendance` a
        JOIN `tabEmployee` e ON e.name = a.employee
        WHERE a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
          AND a.docstatus = 1
          AND e.department IS NOT NULL
        GROUP BY e.department, a.status
        ORDER BY e.department
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

    dept_map = {}
    for row in stats:
        dept = row.department
        if dept not in dept_map:
            dept_map[dept] = {"department": dept}
        dept_map[dept][row.status] = row.count

    return {
        "from_date": from_date,
        "to_date": to_date,
        "data": list(dept_map.values()),
    }


@frappe.whitelist()
def get_employee_attendance_detail(employee, from_date=None, to_date=None):
    """Get detailed attendance for a specific employee."""
    if not from_date:
        from_date = getdate(today()).replace(day=1).isoformat()
    if not to_date:
        to_date = today()

    emp = frappe.get_value(
        "Employee", employee,
        ["name", "employee_name", "department", "designation",
         "attendance_device_id", "image", "company"],
        as_dict=True,
    )
    if not emp:
        frappe.throw("Employé non trouvé", frappe.DoesNotExistError)

    attendance = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": 1,
        },
        fields=["attendance_date", "status", "leave_type",
                "late_entry", "early_exit", "working_hours"],
        order_by="attendance_date desc",
    )

    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [
                f"{from_date} 00:00:00",
                f"{to_date} 23:59:59",
            ]],
        },
        fields=["time", "log_type", "device_id", "shift"],
        order_by="time desc",
    )

    summary = {}
    for a in attendance:
        status = a.status
        summary[status] = summary.get(status, 0) + 1

    return {
        "employee": emp,
        "from_date": from_date,
        "to_date": to_date,
        "attendance": attendance,
        "checkins": checkins,
        "summary": summary,
    }

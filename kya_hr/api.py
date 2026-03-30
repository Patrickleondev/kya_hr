import frappe
from frappe.utils import today, now_datetime, add_days, getdate, get_datetime, cint


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
            "url": "/permission-sortie-stagiaire/new",
            "emoji": "🚪",
        })
        links.append({
            "title": "Bilan de Stage",
            "description": "Remplir le bilan de fin de stage",
            "url": "/bilan-fin-de-stage/new",
            "emoji": "📝",
        })
    elif category == "prestataire":
        # --- Prestataire de service links ---
        links.append({
            "title": "Permission de Sortie",
            "description": "Demander une permission de sortie",
            "url": "/permission-sortie-employe/new",
            "emoji": "🚪",
        })
    else:
        # --- Employee (CDI/CDD) links ---
        links.append({
            "title": "Permission de Sortie",
            "description": "Demander une permission de sortie",
            "url": "/permission-sortie-employe/new",
            "emoji": "🚪",
        })
        links.append({
            "title": "Planning de Congé",
            "description": "Planifier vos périodes de congé annuelles",
            "url": "/planning-conge/new",
            "emoji": "📅",
        })

    # --- Common links (all types) ---
    links.append({
        "title": "PV Sortie Matériel",
        "description": "Déclarer une sortie de matériel",
        "url": "/pv-sortie-materiel/new",
        "emoji": "📦",
    })
    links.append({
        "title": "Demande d\'Achat",
        "description": "Soumettre une demande d\'achat",
        "url": "/demande-achat/new",
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
    "Bilan Fin de Stage",
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


# ═══════════════════════════════════════════════════════════════
#  MES DEMANDES (Document Tracking for Mobile)
# ═══════════════════════════════════════════════════════════════

_TRACKABLE_DOCTYPES = [
    {
        "doctype": "Permission Sortie Employe",
        "label": "Permission de Sortie",
        "category": "rh",
        "for": ["employee", "prestataire"],
    },
    {
        "doctype": "Permission Sortie Stagiaire",
        "label": "Permission de Sortie",
        "category": "rh",
        "for": ["stage"],
    },
    {
        "doctype": "Planning Conge",
        "label": "Planning de Congé",
        "category": "rh",
        "for": ["employee"],
    },
    {
        "doctype": "PV Sortie Materiel",
        "label": "PV Sortie Matériel",
        "category": "stock",
        "for": ["employee", "stage", "prestataire"],
        "filter_by": "owner",  # No Employee Link field, filter by doc creator
    },
    {
        "doctype": "Demande Achat KYA",
        "label": "Demande d'Achat",
        "category": "achats",
        "for": ["employee"],
    },
    {
        "doctype": "Bilan Fin de Stage",
        "label": "Bilan de Stage",
        "category": "rh",
        "for": ["stage"],
    },
]

_STATE_COLORS = {
    "Brouillon": "orange",
    "En attente Chef": "blue",
    "En attente Chef Service": "blue",
    "En attente RH": "blue",
    "En attente DG": "blue",
    "En attente DGA": "blue",
    "En attente DAAF": "blue",
    "En attente Magasin": "blue",
    "En attente Audit": "blue",
    "En attente Comptabilité": "blue",
    "En attente Resp. Stagiaires": "blue",
    "En cours": "yellow",
    "Approuvé": "green",
    "Approuvée": "green",
    "Validé": "green",
    "Rejeté": "red",
    "Rejetée": "red",
    "Annulé": "gray",
}


@frappe.whitelist()
def get_my_documents(limit=20, offset=0, status_filter=None):
    """Retourne les documents de l'utilisateur courant avec états workflow."""
    user = frappe.session.user
    if user == "Guest":
        return {"data": [], "total": 0}

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employment_type"],
        as_dict=True,
    )
    if not employee:
        return {"data": [], "total": 0}

    category = _get_user_category(employee.employment_type or "")
    documents = []

    for dt_info in _TRACKABLE_DOCTYPES:
        if category not in dt_info["for"]:
            continue

        dt = dt_info["doctype"]
        if not frappe.db.exists("DocType", dt):
            continue

        filter_field = dt_info.get("filter_by", "employee")
        if filter_field == "owner":
            filters = {"owner": user}
        else:
            filters = {filter_field: employee.name}
        if status_filter and status_filter != "all":
            filters["workflow_state"] = status_filter

        try:
            docs = frappe.get_all(
                dt,
                filters=filters,
                fields=["name", "creation", "modified", "workflow_state", "docstatus"],
                order_by="modified desc",
                limit_page_length=50,
            )
        except Exception:
            continue

        for doc in docs:
            ws = doc.get("workflow_state") or "Brouillon"
            documents.append({
                "doctype": dt,
                "name": doc.name,
                "label": dt_info["label"],
                "category": dt_info["category"],
                "workflow_state": ws,
                "color": _STATE_COLORS.get(ws, "gray"),
                "creation": str(doc.creation),
                "modified": str(doc.modified),
                "url": f"/app/{frappe.scrub(dt).replace('_', '-')}/{doc.name}",
            })

    # Sort by modified desc
    documents.sort(key=lambda d: d["modified"], reverse=True)
    total = len(documents)
    page = documents[cint(offset): cint(offset) + cint(limit)]

    return {"data": page, "total": total}


# ═══════════════════════════════════════════════════════════════
#  ENQUÊTES & ÉVALUATIONS (KYA Forms for Mobile)
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_my_kya_forms():
    """Retourne les enquêtes/évaluations disponibles et remplies pour l'utilisateur."""
    user = frappe.session.user
    if user == "Guest":
        return {"available": [], "completed": []}

    # Vérifier si le DocType KYA Form existe (kya_services installé)
    if not frappe.db.exists("DocType", "KYA Form"):
        return {"available": [], "completed": []}

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "department"],
        as_dict=True,
    )

    # Formulaires publiés (actifs)
    available = []
    try:
        forms = frappe.get_all(
            "KYA Form",
            filters={"statut": "Publié"},
            fields=["name", "titre", "description", "type_formulaire",
                     "date_debut", "date_fin", "token"],
            order_by="creation desc",
        )
        for f in forms:
            # Vérifier si déjà rempli
            already_done = False
            if employee and frappe.db.exists("DocType", "KYA Form Response"):
                already_done = frappe.db.exists("KYA Form Response", {
                    "form": f.name,
                    "respondent_email": user,
                })
            available.append({
                "name": f.name,
                "titre": f.titre,
                "description": f.description or "",
                "type": f.type_formulaire or "Enquête",
                "date_debut": str(f.date_debut) if f.date_debut else None,
                "date_fin": str(f.date_fin) if f.date_fin else None,
                "completed": bool(already_done),
                "url": f"/kya-survey?token={f.token}" if f.token else f"/app/kya-form/{f.name}",
            })
    except Exception:
        pass

    # Réponses déjà soumises
    completed = []
    try:
        if frappe.db.exists("DocType", "KYA Form Response"):
            responses = frappe.get_all(
                "KYA Form Response",
                filters={"respondent_email": user},
                fields=["name", "form", "creation", "respondent_name"],
                order_by="creation desc",
                limit_page_length=20,
            )
            for r in responses:
                form_title = frappe.db.get_value("KYA Form", r.form, "titre") or r.form
                completed.append({
                    "name": r.name,
                    "form": r.form,
                    "form_title": form_title,
                    "date": str(r.creation),
                })
    except Exception:
        pass

    return {"available": available, "completed": completed}


# ═══════════════════════════════════════════════════════════════
#  MES TÂCHES (KYA Taches for Mobile)
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_my_tasks():
    """Retourne les tâches attribuées à l'utilisateur courant."""
    user = frappe.session.user
    if user == "Guest":
        return {"tasks": [], "plans": []}

    # Vérifier si le module KYA Taches existe
    if not frappe.db.exists("DocType", "Tache Equipe"):
        return {"tasks": [], "plans": []}

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name"],
        as_dict=True,
    )
    if not employee:
        return {"tasks": [], "plans": []}

    # Tâches assignées directement
    tasks = []
    try:
        taches = frappe.get_all(
            "Tache Equipe",
            filters={"responsable": employee.name},
            fields=["name", "titre", "statut", "priorite", "date_debut",
                     "date_echeance", "progression", "plan_trimestriel"],
            order_by="date_echeance asc",
            limit_page_length=50,
        )
        for t in taches:
            tasks.append({
                "name": t.name,
                "titre": t.titre,
                "statut": t.statut or "Non démarré",
                "priorite": t.priorite or "Moyenne",
                "date_debut": str(t.date_debut) if t.date_debut else None,
                "date_echeance": str(t.date_echeance) if t.date_echeance else None,
                "progression": t.progression or 0,
                "plan": t.plan_trimestriel,
                "url": f"/app/tache-equipe/{t.name}",
            })
    except Exception:
        pass

    # Plans trimestriels où l'utilisateur est chef d'équipe
    plans = []
    try:
        if frappe.db.exists("DocType", "Plan Trimestriel"):
            mes_plans = frappe.get_all(
                "Plan Trimestriel",
                filters={"chef_equipe": employee.name},
                fields=["name", "titre", "trimestre", "annee", "statut",
                         "equipe", "progression_globale"],
                order_by="creation desc",
                limit_page_length=10,
            )
            for p in mes_plans:
                plans.append({
                    "name": p.name,
                    "titre": p.titre or f"Plan {p.trimestre} {p.annee}",
                    "statut": p.statut or "Brouillon",
                    "equipe": p.equipe,
                    "progression": p.progression_globale or 0,
                    "url": f"/app/plan-trimestriel/{p.name}",
                })
    except Exception:
        pass

    return {"tasks": tasks, "plans": plans}


# ═══════════════════════════════════════════════════════════
# MES DEMANDES — LISTE COMBINÉE + STATISTIQUES
# ═══════════════════════════════════════════════════════════

@frappe.whitelist()
def get_demandes_combined(limit=50, offset=0, type_filter=None, statut_filter=None):
    """
    Retourne une liste combinée de PV Sortie Matériel et Demande Achat KYA.
    Filtrable par type (pv / da) et par statut (workflow_state).
    """
    user = frappe.session.user
    if user == "Guest":
        return {"data": [], "total": 0}

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name"],
        as_dict=True,
    )

    results = []

    # ── PV Sortie Matériel ─────────────────────────────────
    if not type_filter or type_filter == "pv":
        pv_filters = {"owner": user}
        if statut_filter:
            pv_filters["workflow_state"] = statut_filter
        try:
            pvs = frappe.get_all(
                "PV Sortie Materiel",
                filters=pv_filters,
                fields=["name", "objet", "date_sortie", "workflow_state",
                        "reference", "creation", "owner"],
                order_by="creation desc",
                limit_page_length=int(limit) * 2,
            )
            for doc in pvs:
                results.append({
                    "name": doc.name,
                    "type": "PV Sortie Matériel",
                    "type_code": "pv",
                    "objet": doc.objet or doc.reference or "",
                    "date": str(doc.date_sortie) if doc.date_sortie else str(doc.creation)[:10],
                    "statut": doc.workflow_state or "Brouillon",
                    "color": _STATE_COLORS.get(doc.workflow_state or "Brouillon", "gray"),
                    "url": f"/pv-sortie-materiel?name={doc.name}",
                    "creation": str(doc.creation),
                })
        except Exception:
            pass

    # ── Demande d'Achat ────────────────────────────────────
    if not type_filter or type_filter == "da":
        da_filters = {}
        if employee:
            da_filters["employee"] = employee.name
        else:
            da_filters["owner"] = user
        if statut_filter:
            da_filters["workflow_state"] = statut_filter
        try:
            das = frappe.get_all(
                "Demande Achat KYA",
                filters=da_filters,
                fields=["name", "objet", "date_demande", "workflow_state",
                        "montant_total", "urgence", "creation", "owner"],
                order_by="creation desc",
                limit_page_length=int(limit) * 2,
            )
            for doc in das:
                results.append({
                    "name": doc.name,
                    "type": "Demande d'Achat",
                    "type_code": "da",
                    "objet": doc.objet or "",
                    "date": str(doc.date_demande) if doc.date_demande else str(doc.creation)[:10],
                    "statut": doc.workflow_state or "Brouillon",
                    "color": _STATE_COLORS.get(doc.workflow_state or "Brouillon", "gray"),
                    "montant": doc.montant_total or 0,
                    "urgence": doc.urgence or "Normale",
                    "url": f"/demande-achat?name={doc.name}",
                    "creation": str(doc.creation),
                })
        except Exception:
            pass

    # Tri global par date de création décroissante
    results.sort(key=lambda x: x["creation"], reverse=True)

    total = len(results)
    offset = int(offset)
    limit = int(limit)
    data = results[offset: offset + limit]

    return {"data": data, "total": total}


@frappe.whitelist()
def get_demandes_stats():
    """
    Retourne les statistiques des demandes de l'utilisateur courant :
    - total, par statut (brouillon / en_cours / approuve / rejete)
    - par type (pv vs da)
    """
    user = frappe.session.user
    if user == "Guest":
        return {}

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        "name",
    )

    stats = {
        "total": 0,
        "brouillon": 0,
        "en_cours": 0,
        "approuve": 0,
        "rejete": 0,
        "pv_total": 0,
        "da_total": 0,
    }

    en_cours_states = {
        "En attente Chef", "En attente Chef Service", "En attente RH",
        "En attente DG", "En attente DGA", "En attente Magasin",
        "En attente Audit", "En attente Comptabilité", "En attente DAAF",
        "En attente Resp. Stagiaires", "En cours",
        "En attente Approbation",
    }
    approuve_states = {"Approuvé", "Approuvée", "Validé"}
    rejete_states = {"Rejeté", "Rejetée", "Annulé"}

    # PV Sortie Matériel
    try:
        pvs = frappe.get_all(
            "PV Sortie Materiel",
            filters={"owner": user},
            fields=["workflow_state"],
        )
        stats["pv_total"] = len(pvs)
        stats["total"] += len(pvs)
        for doc in pvs:
            ws = doc.workflow_state or "Brouillon"
            if ws == "Brouillon":
                stats["brouillon"] += 1
            elif ws in en_cours_states:
                stats["en_cours"] += 1
            elif ws in approuve_states:
                stats["approuve"] += 1
            elif ws in rejete_states:
                stats["rejete"] += 1
    except Exception:
        pass

    # Demande d'Achat
    try:
        da_filters = {"employee": employee} if employee else {"owner": user}
        das = frappe.get_all(
            "Demande Achat KYA",
            filters=da_filters,
            fields=["workflow_state"],
        )
        stats["da_total"] = len(das)
        stats["total"] += len(das)
        for doc in das:
            ws = doc.workflow_state or "Brouillon"
            if ws == "Brouillon":
                stats["brouillon"] += 1
            elif ws in en_cours_states:
                stats["en_cours"] += 1
            elif ws in approuve_states:
                stats["approuve"] += 1
            elif ws in rejete_states:
                stats["rejete"] += 1
    except Exception:
        pass

    return stats


# ─── Dashboard Stagiaires ──────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_stagiaires(annee=None):
    """Stats globales pour le module Stagiaires (accessible RH + System Manager)."""
    import datetime
    if annee:
        annee = int(annee)
    else:
        annee = datetime.date.today().year

    stats = {
        "annee": annee,
        "stagiaires_actifs": 0,
        "stagiaires_total": 0,
        "permissions_total": 0,
        "permissions_approuvees": 0,
        "permissions_en_cours": 0,
        "permissions_rejetees": 0,
        "bilans_total": 0,
        "bilans_soumis": 0,
        "note_moyenne": 0,
        "mentions": {},
        "permissions_par_mois": {},
        "top_beneficiaires": [],
    }

    # Stagiaires
    try:
        stagiaires = frappe.get_all(
            "Employee",
            filters={"employment_type": "Stage", "status": "Active"},
            fields=["name", "employee_name", "department"],
        )
        stats["stagiaires_actifs"] = len(stagiaires)
        stats["stagiaires_total"] = frappe.db.count(
            "Employee", {"employment_type": "Stage"}
        )
    except Exception:
        pass

    en_cours_states = {
        "En attente Chef", "En attente Chef Service",
        "En attente Resp. Stagiaires", "En attente DG", "En cours",
    }
    approuve_states = {"Approuvé", "Approuvée", "Validé"}
    rejete_states = {"Rejeté", "Rejetée", "Annulé"}

    # Permissions Stagiaires
    try:
        perms = frappe.get_all(
            "Permission Sortie Stagiaire",
            filters=[["date_sortie", ">=", f"{annee}-01-01"],
                     ["date_sortie", "<=", f"{annee}-12-31"]],
            fields=["name", "workflow_state", "date_sortie", "employee", "employee_name"],
        )
        stats["permissions_total"] = len(perms)
        mois_count = {}
        benef_count = {}
        for p in perms:
            ws = p.workflow_state or "Brouillon"
            if ws in approuve_states:
                stats["permissions_approuvees"] += 1
            elif ws in en_cours_states:
                stats["permissions_en_cours"] += 1
            elif ws in rejete_states:
                stats["permissions_rejetees"] += 1
            # Par mois
            if p.date_sortie:
                mois = str(p.date_sortie)[:7]
                mois_count[mois] = mois_count.get(mois, 0) + 1
            # Par bénéficiaire
            emp = p.employee_name or p.employee or "Inconnu"
            benef_count[emp] = benef_count.get(emp, 0) + 1
        stats["permissions_par_mois"] = mois_count
        # Top 5
        stats["top_beneficiaires"] = sorted(
            [{"nom": k, "count": v} for k, v in benef_count.items()],
            key=lambda x: x["count"], reverse=True
        )[:5]
    except Exception:
        pass

    # Bilans de Stage
    try:
        bilans = frappe.get_all(
            "Bilan Fin de Stage",
            fields=["name", "workflow_state", "note_globale", "mention"],
        )
        stats["bilans_total"] = len(bilans)
        notes = []
        mentions = {}
        for b in bilans:
            ws = b.workflow_state or "Brouillon"
            if ws in approuve_states:
                stats["bilans_soumis"] += 1
            if b.note_globale:
                notes.append(float(b.note_globale))
            if b.mention:
                mentions[b.mention] = mentions.get(b.mention, 0) + 1
        if notes:
            stats["note_moyenne"] = round(sum(notes) / len(notes), 2)
        stats["mentions"] = mentions
    except Exception:
        pass

    return stats


@frappe.whitelist()
def get_dashboard_employes(annee=None):
    """Stats globales pour le module Employés (accessible RH + System Manager)."""
    import datetime
    if annee:
        annee = int(annee)
    else:
        annee = datetime.date.today().year

    stats = {
        "annee": annee,
        "employes_actifs": 0,
        "employes_total": 0,
        "permissions_total": 0,
        "permissions_approuvees": 0,
        "permissions_en_cours": 0,
        "permissions_rejetees": 0,
        "permissions_par_mois": {},
        "conges_total": 0,
        "conges_approuves": 0,
        "pv_total": 0,
        "pv_approuves": 0,
        "da_total": 0,
        "da_approuves": 0,
        "da_montant_total_approuve": 0,
        "absences_total": 0,
        "presences_total": 0,
        "taux_presence": 0,
        "top_demandeurs_da": [],
    }

    en_cours_states = {
        "En attente Chef", "En attente Chef Service", "En attente RH",
        "En attente DG", "En attente DGA", "En attente Magasin",
        "En attente Audit", "En attente Comptabilité",
        "En attente Approbation", "En cours",
    }
    approuve_states = {"Approuvé", "Approuvée", "Validé"}
    rejete_states = {"Rejeté", "Rejetée", "Annulé"}

    # Employés (hors stagiaires)
    try:
        emp_filters = [["employment_type", "!=", "Stage"], ["status", "=", "Active"]]
        stats["employes_actifs"] = frappe.db.count("Employee", emp_filters)
        stats["employes_total"] = frappe.db.count(
            "Employee", [["employment_type", "!=", "Stage"]]
        )
    except Exception:
        pass

    # Permissions Employés
    try:
        perms = frappe.get_all(
            "Permission Sortie Employe",
            filters=[["date_sortie", ">=", f"{annee}-01-01"],
                     ["date_sortie", "<=", f"{annee}-12-31"]],
            fields=["name", "workflow_state", "date_sortie"],
        )
        stats["permissions_total"] = len(perms)
        mois_count = {}
        for p in perms:
            ws = p.workflow_state or "Brouillon"
            if ws in approuve_states:
                stats["permissions_approuvees"] += 1
            elif ws in en_cours_states:
                stats["permissions_en_cours"] += 1
            elif ws in rejete_states:
                stats["permissions_rejetees"] += 1
            if p.date_sortie:
                mois = str(p.date_sortie)[:7]
                mois_count[mois] = mois_count.get(mois, 0) + 1
        stats["permissions_par_mois"] = mois_count
    except Exception:
        pass

    # Plannings Congé
    try:
        conges = frappe.get_all(
            "Planning Conge",
            filters=[["annee", "=", annee]],
            fields=["name", "workflow_state"],
        )
        stats["conges_total"] = len(conges)
        for c in conges:
            if (c.workflow_state or "") in approuve_states:
                stats["conges_approuves"] += 1
    except Exception:
        pass

    # PV Sortie Matériel
    try:
        pvs = frappe.get_all(
            "PV Sortie Materiel",
            filters=[["date_sortie", ">=", f"{annee}-01-01"],
                     ["date_sortie", "<=", f"{annee}-12-31"]],
            fields=["name", "workflow_state"],
        )
        stats["pv_total"] = len(pvs)
        for p in pvs:
            if (p.workflow_state or "") in approuve_states:
                stats["pv_approuves"] += 1
    except Exception:
        pass

    # Demandes d'Achat
    try:
        das = frappe.get_all(
            "Demande Achat KYA",
            filters=[["date_demande", ">=", f"{annee}-01-01"],
                     ["date_demande", "<=", f"{annee}-12-31"]],
            fields=["name", "workflow_state", "montant_total", "employee"],
        )
        stats["da_total"] = len(das)
        da_by_emp = {}
        for d in das:
            ws = d.workflow_state or "Brouillon"
            if ws in approuve_states:
                stats["da_approuves"] += 1
                stats["da_montant_total_approuve"] += float(d.montant_total or 0)
            emp = d.employee or "Inconnu"
            da_by_emp[emp] = da_by_emp.get(emp, {"count": 0, "montant": 0})
            da_by_emp[emp]["count"] += 1
            da_by_emp[emp]["montant"] += float(d.montant_total or 0)
        stats["top_demandeurs_da"] = sorted(
            [{"emp": k, "count": v["count"], "montant": v["montant"]}
             for k, v in da_by_emp.items()],
            key=lambda x: x["count"], reverse=True
        )[:5]
    except Exception:
        pass

    # Présences / Absences
    try:
        att = frappe.get_all(
            "Attendance",
            filters=[["attendance_date", ">=", f"{annee}-01-01"],
                     ["attendance_date", "<=", f"{annee}-12-31"]]
            if annee else [],
            fields=["status"],
        )
        for a in att:
            if a.status in ("Present", "Work From Home", "Half Day"):
                stats["presences_total"] += 1
            elif a.status == "Absent":
                stats["absences_total"] += 1
        total_att = stats["presences_total"] + stats["absences_total"]
        if total_att > 0:
            stats["taux_presence"] = round(
                stats["presences_total"] / total_att * 100, 1
            )
    except Exception:
        pass

    return stats


@frappe.whitelist()
def get_webforms_list():
    """Retourne la liste des web forms KYA HR avec leurs URLs et statuts."""
    forms = [
        {
            "name": "permission-sortie-stagiaire",
            "label": "Permission de Sortie Stagiaire",
            "route": "/permission-sortie-stagiaire",
            "new_route": "/permission-sortie-stagiaire/new",
            "ref": "AEA-ENG-30-V01",
            "module": "Stagiaires",
            "icon": "🎓"
        },
        {
            "name": "permission-sortie-employe",
            "label": "Permission de Sortie Employé",
            "route": "/permission-sortie-employe",
            "new_route": "/permission-sortie-employe/new",
            "ref": "AEA-ENG-30-V01",
            "module": "Employés",
            "icon": "👤"
        },
        {
            "name": "demande-achat",
            "label": "Demande d'Achat",
            "route": "/demande-achat",
            "new_route": "/demande-achat/new",
            "ref": "AEA-ENG-30-V01",
            "module": "Achats",
            "icon": "🛒"
        },
        {
            "name": "pv-sortie-materiel",
            "label": "PV Sortie de Matériel",
            "route": "/pv-sortie-materiel",
            "new_route": "/pv-sortie-materiel/new",
            "ref": "AEA-ENG-30-V01",
            "module": "Stock",
            "icon": "📦"
        },
        {
            "name": "planning-conge",
            "label": "Planning de Congé",
            "route": "/planning-conge",
            "new_route": "/planning-conge/new",
            "ref": "AEA-ENG-30-V01",
            "module": "Employés",
            "icon": "📅"
        },
        {
            "name": "bilan-fin-de-stage",
            "label": "Bilan de Fin de Stage",
            "route": "/bilan-fin-de-stage",
            "new_route": "/bilan-fin-de-stage/new",
            "ref": "AEA-ENG-30-V01",
            "module": "Stagiaires",
            "icon": "📋"
        },
    ]
    # Enrichir avec le count des documents liés
    doctypes_map = {
        "permission-sortie-stagiaire": "Permission Sortie Stagiaire",
        "permission-sortie-employe": "Permission Sortie Employe",
        "demande-achat": "Demande Achat KYA",
        "pv-sortie-materiel": "PV Sortie Materiel",
        "planning-conge": "Planning Conge",
        "bilan-fin-de-stage": "Bilan Fin de Stage",
    }
    for form in forms:
        dt = doctypes_map.get(form["name"])
        if dt:
            try:
                form["count"] = frappe.db.count(dt)
            except Exception:
                form["count"] = 0
    return forms


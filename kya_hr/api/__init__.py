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
            "title": "Espace Mobile Stagiaire",
            "description": "Ouvrir le tableau de bord mobile stagiaire",
            "url": "/tableau-bord-stagiaires",
            "emoji": "📱",
        })
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
            "title": "Espace Mobile RH",
            "description": "Ouvrir le tableau de bord mobile employé",
            "url": "/tableau-bord-employes",
            "emoji": "📱",
        })
        links.append({
            "title": "Permission de Sortie",
            "description": "Demander une permission de sortie",
            "url": "/permission-sortie-employe/new",
            "emoji": "🚪",
        })
    else:
        # --- Employee (CDI/CDD) links ---
        links.append({
            "title": "Espace Mobile RH",
            "description": "Ouvrir le tableau de bord mobile employé",
            "url": "/tableau-bord-employes",
            "emoji": "📱",
        })
        links.append({
            "title": "Permission de Sortie",
            "description": "Demander une permission de sortie",
            "url": "/permission-sortie-employe/new",
            "emoji": "🚪",
        })
        links.append({
            "title": "Demande de Congé",
            "description": "Soumettre une demande de congé",
            "url": "/demande-conge/new",
            "emoji": "🏖️",
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
    "Leave Application",
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
def get_my_kya_forms(trimestre=None, annee=None, equipe_cible=None, type_formulaire=None):
    """Vue mobile RHMS des formulaires satisfaction KYA avec onglets et filtres.

    Conserve les clés legacy (available/completed) pour rétrocompatibilité UI.
    """
    try:
        dashboard = frappe.call(
            "kya_services.api.get_employee_forms_dashboard",
            trimestre=trimestre,
            annee=annee,
            equipe_cible=equipe_cible,
            type_formulaire=type_formulaire,
        )
    except Exception:
        return {
            "available": [],
            "completed": [],
            "tabs": {"actifs": [], "en_attente": [], "deja_repondu": [], "fermes": [], "historique": []},
            "counts": {"actifs": 0, "en_attente": 0, "deja_repondu": 0, "fermes": 0, "historique": 0},
            "filters": {"trimestres": ["T1", "T2", "T3", "T4"], "annees": [], "equipes": [], "types": []},
        }

    tabs = dashboard.get("tabs", {})
    available = tabs.get("actifs", []) + tabs.get("en_attente", [])
    completed = [
        {
            "name": item.get("form_name"),
            "form": item.get("form_name"),
            "form_title": item.get("titre"),
            "date": item.get("date_reponse") or item.get("date_creation"),
        }
        for item in tabs.get("deja_repondu", [])
    ]

    dashboard["available"] = available
    dashboard["completed"] = completed
    return dashboard


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
                    "url": f"/pv-sortie-materiel/{doc.name}",
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
                    "url": f"/demande-achat/{doc.name}",
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
            "name": "demande-conge",
            "label": "Demande de Congé",
            "route": "/demande-conge",
            "new_route": "/demande-conge/new",
            "ref": "AEA-ENG-30-V01",
            "module": "Employés",
            "icon": "🏖️"
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
        "demande-conge": "Leave Application",
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


@frappe.whitelist()
def get_my_hr_dossiers(from_date=None, to_date=None, doctype_filter=None, limit=200):
    """Historique unifie des dossiers RH du demandeur courant.

    Retourne les dossiers des principaux flux RH avec filtrage par date,
    type de fiche et etat workflow.
    """
    user = frappe.session.user
    if user == "Guest":
        return []

    limit = cint(limit) or 200
    limit = min(max(limit, 1), 500)

    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if not employee:
        return []

    specs = [
        {
            "label": "Permission Sortie Employé",
            "doctype": "Permission Sortie Employe",
            "employee_field": "employee",
            "date_field": "date_sortie",
            "route": "/permission-sortie-employe",
        },
        {
            "label": "Planning de Congé",
            "doctype": "Planning Conge",
            "employee_field": "employee",
            "date_field": "creation",
            "route": "/planning-conge",
        },
        {
            "label": "Demande de Congé",
            "doctype": "Leave Application",
            "employee_field": "employee",
            "date_field": "from_date",
            "route": "/demande-conge",
        },
        {
            "label": "Demande d'Achat",
            "doctype": "Demande Achat KYA",
            "employee_field": "employee",
            "date_field": "date_demande",
            "route": "/demande-achat",
        },
    ]

    if doctype_filter:
        specs = [s for s in specs if s["doctype"] == doctype_filter or s["label"] == doctype_filter]

    out = []
    for spec in specs:
        filters = {spec["employee_field"]: employee}
        date_field = spec["date_field"]
        if from_date and to_date:
            filters[date_field] = ["between", [from_date, to_date]]
        elif from_date:
            filters[date_field] = [">=", from_date]
        elif to_date:
            filters[date_field] = ["<=", to_date]

        rows = frappe.get_all(
            spec["doctype"],
            filters=filters,
            fields=["name", "workflow_state", "docstatus", "creation", date_field],
            order_by="creation desc",
            limit_page_length=limit,
        )

        for row in rows:
            dossier_date = row.get(date_field) or row.get("creation")
            out.append({
                "doctype": spec["doctype"],
                "type_fiche": spec["label"],
                "numero_dossier": row.get("name"),
                "workflow_state": row.get("workflow_state") or "Brouillon",
                "docstatus": row.get("docstatus"),
                "date_dossier": dossier_date,
                "date_creation": row.get("creation"),
                "route": f"{spec['route']}?name={row.get('name')}",
            })

    out.sort(key=lambda d: str(d.get("date_dossier") or d.get("date_creation") or ""), reverse=True)
    return out[:limit]


# ═══════════════════════════════════════════════════════════════
#  WEB FORM: Employee auto-fill helpers
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_employee_from_user():
    """Retourne le dossier Employee de l'utilisateur connecté (pour auto-remplissage web form).

    Toujours basé sur frappe.session.user — aucun paramètre accepté pour
    éviter toute énumération de fiches d'autres employés.
    """
    user = frappe.session.user
    if user == "Guest":
        return None

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "department", "reports_to", "employment_type"],
        as_dict=True,
    )
    return employee


@frappe.whitelist()
def search_employee_by_name(search_term):
    """Vérifie si le nom saisi correspond à la fiche Employee de l'utilisateur connecté.

    Sécurité : ne retourne QUE la fiche de l'utilisateur connecté si le nom
    correspond. N'énumère jamais les fiches des autres employés.

    Args:
        search_term: Nom complet saisi par l'utilisateur (doit correspondre à sa propre fiche)

    Returns:
        dict {name, employee_name, department, employment_type} si correspondance,
        sinon None.
    """
    user = frappe.session.user
    if user == "Guest" or not search_term or len(search_term.strip()) < 2:
        return None

    # Récupère uniquement la fiche de l'utilisateur connecté
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "department", "employment_type"],
        as_dict=True,
    )
    if not employee:
        return None

    # Vérifie que le nom saisi correspond (insensible à la casse, tolérant aux espaces)
    term = search_term.strip().lower()
    own_name = (employee.get("employee_name") or "").strip().lower()
    if term in own_name or own_name.startswith(term):
        return employee

    return None




# ═══════════════════════════════════════════════════════════════
#  IMPORT EXCEL — Évaluation Trimestrielle (Plan Trimestriel)
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def import_evaluation_excel(file_url, equipe, trimestre, annee):
    """Importe un fichier Excel d'évaluation trimestrielle (Équipe X) et
    crée/met à jour le Plan Trimestriel correspondant + ses Tâches Equipe.

    Format attendu (cf. evaluation_trimestrielle_Equipe_IT_T1_2026):
      - Ligne 4 : en-têtes (N°, RESULTATS ATTENDUS, TÂCHES PREVUES,
        POSSIBILITE DIGITALISATION, TAUX DIGITALISATION, ATTRIBUTION,
        INDICATEUR (KPI), TAUX ESTIME, ..., TAUX EFFECTIF)
      - Ligne 5+ : données (un résultat peut s'étaler sur N lignes,
        chaque ligne = une tâche)

    Retourne:
        dict {
          "plan": <name>,           # nom du Plan Trimestriel
          "taches_created": int,
          "taches_updated": int,
          "errors": [str],
          "attributions_resolved": int,
          "attributions_unresolved": [str],
        }
    """
    import os
    import openpyxl
    from frappe.utils.file_manager import get_file_path

    if not file_url:
        frappe.throw(_("Aucun fichier fourni."))

    # Sécurité: l'utilisateur doit avoir le rôle Chef Service / HR Manager / System Manager
    user_roles = set(frappe.get_roles())
    allowed = {"Chef Service", "HR Manager", "System Manager", "Responsable RH"}
    if not (allowed & user_roles):
        frappe.throw(_("Permission refusée : seul le Chef d'Équipe ou la RH peut importer."))

    file_path = get_file_path(file_url)
    if not os.path.exists(file_path):
        frappe.throw(_("Fichier introuvable : {0}").format(file_url))

    try:
        wb = openpyxl.load_workbook(file_path, data_only=True, read_only=False)
    except Exception as e:
        frappe.throw(_("Lecture Excel impossible : {0}").format(str(e)))

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 5:
        frappe.throw(_("Le fichier ne contient pas assez de lignes (min 5)."))

    # ── Trouve la ligne d'en-tête (contient "RESULTATS ATTENDUS") ───
    header_idx = None
    for i, row in enumerate(rows[:10]):
        joined = " ".join(str(c) for c in row if c is not None).upper()
        if "RESULTATS ATTENDUS" in joined and "TÂCHES" in joined.replace("TACHES", "TÂCHES"):
            header_idx = i
            break
    if header_idx is None:
        frappe.throw(_("En-tête 'RESULTATS ATTENDUS / TÂCHES PREVUES' introuvable."))

    headers = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
    # Mappe les colonnes par mot-clé
    def find_col(*keywords):
        for idx, h in enumerate(headers):
            up = h.upper()
            if all(k.upper() in up for k in keywords):
                return idx
        return None

    col_num = find_col("N°") or find_col("NUM")
    col_resultat = find_col("RESULTATS")
    col_tache = find_col("TÂCHES") or find_col("TACHES")
    col_digit = find_col("POSSIBILITE")
    col_taux_digit = find_col("TAUX", "DIGITALISATION")
    col_attrib = find_col("ATTRIBUTION")
    col_kpi = find_col("INDICATEUR") or find_col("KPI")
    col_taux_est = find_col("TAUX", "ESTIME")
    col_taux_eff = find_col("TAUX", "EFFECTIF")

    if col_resultat is None or col_tache is None:
        frappe.throw(_("Colonnes 'RESULTATS ATTENDUS' ou 'TÂCHES PREVUES' introuvables."))

    # ── Pre-scan: extraire la liste des resultats uniques (R1, R2...) ─
    pre_resultats = {}  # numero -> libelle
    cur_num, cur_lib = None, None
    for row in rows[header_idx + 1:]:
        if all(c is None or str(c).strip() == "" for c in row):
            continue
        if col_num is not None and row[col_num] is not None:
            try:
                cur_num = str(int(float(row[col_num])))
            except (ValueError, TypeError):
                cur_num = str(row[col_num]).strip()
        if col_resultat is not None and row[col_resultat] is not None:
            cur_lib = str(row[col_resultat]).strip()
        if cur_num and cur_lib and cur_num not in pre_resultats:
            pre_resultats[cur_num] = cur_lib

    # ── Crée ou récupère le Plan Trimestriel ────────────────────────
    annee = cint(annee)
    existing = frappe.db.get_value(
        "Plan Trimestriel",
        {"equipe": equipe, "trimestre": trimestre, "annee": annee},
        "name",
    )
    if existing:
        plan = frappe.get_doc("Plan Trimestriel", existing)
    else:
        plan = frappe.new_doc("Plan Trimestriel")
        plan.equipe = equipe
        plan.trimestre = trimestre
        plan.annee = annee
        plan.titre = f"Évaluation {trimestre} {annee} — {equipe}"
        plan.statut = "Brouillon"
        # equipe_abbr (utilise par autoname): derive du nom du departement
        plan.equipe_abbr = (equipe.replace(" ", "")[:8].upper()) if equipe else "PLAN"
        # chef_equipe: tente Equipe KYA, sinon premier Employee actif du dept
        chef = None
        try:
            chef = frappe.db.get_value("Equipe KYA", equipe, "chef_equipe")
        except Exception:
            chef = None
        if not chef:
            chef = frappe.db.get_value(
                "Employee",
                {"department": equipe, "status": "Active"},
                "name",
                order_by="creation asc",
            )
        if not chef:
            # Fallback ultime: premier Employee actif
            chef = frappe.db.get_value("Employee", {"status": "Active"}, "name")
        if chef:
            plan.chef_equipe = chef
        # resultats (Table reqd): pre-remplit depuis le pre-scan
        for num, lib in pre_resultats.items():
            try:
                plan.append("resultats", {
                    "numero": num,
                    "libelle": lib[:1000],
                    "poids": 1,
                })
            except Exception:
                # Si la child table 'Resultat Attendu Item' a d'autres champs requis,
                # on essaie a minima
                pass
        plan.insert(ignore_permissions=True)

    # ── Parse les lignes de données ─────────────────────────────────
    taches_created = 0
    taches_updated = 0
    errors = []
    attrib_resolved = 0
    attrib_unresolved = []
    current_resultat_num = None
    current_resultat_lib = None

    for r_idx, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        # Ligne vide ?
        if all(c is None or str(c).strip() == "" for c in row):
            continue

        # Récupère le N° de résultat (peut être None si fusion)
        if col_num is not None and row[col_num] is not None:
            try:
                current_resultat_num = str(int(float(row[col_num])))
            except (ValueError, TypeError):
                current_resultat_num = str(row[col_num]).strip()
        if col_resultat is not None and row[col_resultat] is not None:
            current_resultat_lib = str(row[col_resultat]).strip()

        # Tâche
        tache_lib = row[col_tache] if col_tache is not None else None
        if not tache_lib or not str(tache_lib).strip():
            continue
        tache_lib = str(tache_lib).strip()

        digit = (str(row[col_digit]).strip().upper() if col_digit is not None and row[col_digit] is not None else "OUI")
        if digit not in ("OUI", "NON"):
            digit = "OUI"

        taux_digit = _safe_pct(row[col_taux_digit]) if col_taux_digit is not None else 0
        kpi = str(row[col_kpi]).strip() if col_kpi is not None and row[col_kpi] is not None else ""
        taux_est = _safe_pct(row[col_taux_est]) if col_taux_est is not None else 100
        taux_eff = _safe_pct(row[col_taux_eff]) if col_taux_eff is not None else 0
        attrib_raw = str(row[col_attrib]).strip() if col_attrib is not None and row[col_attrib] is not None else ""

        # Cherche tâche existante (même plan + même libellé) sinon crée
        existing_tache = frappe.db.get_value(
            "Tache Equipe",
            {"plan": plan.name, "libelle": tache_lib[:140]},
            "name",
        )
        try:
            if existing_tache:
                t = frappe.get_doc("Tache Equipe", existing_tache)
                taches_updated += 1
            else:
                t = frappe.new_doc("Tache Equipe")
                t.plan = plan.name
                t.equipe = equipe
                taches_created += 1

            t.resultat_numero = current_resultat_num or ""
            t.resultat_libelle = (current_resultat_lib or "")[:1000]
            t.libelle = tache_lib[:1000]
            t.digitalisable = digit
            t.taux_digitalisation = taux_digit
            t.kpi = kpi[:1000]
            t.taux_estime = taux_est
            t.taux_effectif = taux_eff
            t.poids = 1
            t.frequence = "Trimestrielle"
            if not t.statut:
                t.statut = "Non démarré"

            # Résolution des attributions (séparateurs "," ";" "\n" "/")
            t.attributions = []
            if attrib_raw:
                names = [n.strip() for n in attrib_raw.replace(";", ",").replace("/", ",").replace("\n", ",").split(",") if n.strip()]
                for n in names:
                    emp = _resolve_employee_by_name(n)
                    if emp:
                        t.append("attributions", {
                            "employe": emp["name"],
                            "nom_employe": emp["employee_name"],
                            "matricule": emp.get("employee_number") or "",
                            "role_attribution": "Responsable" if not t.attributions else "Contributeur",
                        })
                        attrib_resolved += 1
                    else:
                        attrib_unresolved.append(f"L{r_idx}: {n}")

            t.save(ignore_permissions=True)
        except Exception as e:
            errors.append(f"Ligne {r_idx}: {str(e)[:200]}")
            frappe.log_error(frappe.get_traceback(), f"import_evaluation_excel L{r_idx}")

    frappe.db.commit()

    return {
        "plan": plan.name,
        "taches_created": taches_created,
        "taches_updated": taches_updated,
        "errors": errors,
        "attributions_resolved": attrib_resolved,
        "attributions_unresolved": attrib_unresolved,
    }


def _safe_pct(value):
    """Convertit une valeur (float, int, "0%", "0.5", "1") en pourcentage 0-100."""
    if value is None or value == "":
        return 0
    try:
        if isinstance(value, str):
            s = value.strip().replace(",", ".")
            if s.endswith("%"):
                return float(s[:-1])
            v = float(s)
        else:
            v = float(value)
        # Heuristique: si <= 1, c'est une fraction → *100; sinon déjà en %
        if 0 <= v <= 1.0:
            return round(v * 100, 2)
        return round(v, 2)
    except (ValueError, TypeError):
        return 0


def _resolve_employee_by_name(name):
    """Cherche un Employee par nom (employee_name ou first/last name).

    Tolérant à la casse et aux espaces. Retourne dict {name, employee_name,
    employee_number} ou None.
    """
    if not name:
        return None
    name = name.strip()
    # 1. Match exact employee_name
    emp = frappe.db.get_value(
        "Employee",
        {"employee_name": name, "status": "Active"},
        ["name", "employee_name", "employee_number"],
        as_dict=True,
    )
    if emp:
        return emp
    # 2. LIKE insensible à la casse
    matches = frappe.get_all(
        "Employee",
        filters={"employee_name": ["like", f"%{name}%"], "status": "Active"},
        fields=["name", "employee_name", "employee_number"],
        limit=1,
    )
    if matches:
        return matches[0]
    return None


def _(s):
    """Alias frappe._ pour i18n."""
    try:
        return frappe._(s)
    except Exception:
        return s


@frappe.whitelist()
def get_current_employee():
    """Alias public utilisé par les Web Forms KYA. Retourne la fiche Employee active liée au user."""
    return get_employee_from_user()

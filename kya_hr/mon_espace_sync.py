import frappe
from frappe.utils import cint


STAGE_TYPES = {"Stage", "Intern", "Apprentice"}

REQUEST_SPECS = [
    {
        "label": "Permission de Sortie Employe",
        "doctype": "Permission Sortie Employe",
        "route": "/permission-sortie-employe",
        "employee_field": "employee",
        "date_fields": ["date_sortie", "creation"],
        "audience": {"employee", "prestataire"},
        "icon": "🚪",
    },
    {
        "label": "Permission Sortie Stagiaire",
        "doctype": "Permission Sortie Stagiaire",
        "route": "/permission-sortie-stagiaire",
        "employee_field": "employee",
        "date_fields": ["date_sortie", "creation"],
        "audience": {"stage"},
        "icon": "🎓",
    },
    {
        "label": "Bilan de Fin de Stage",
        "doctype": "Bilan Fin de Stage",
        "route": "/bilan-fin-de-stage",
        "employee_field": "employee",
        "date_fields": ["date_bilan", "creation"],
        "audience": {"stage"},
        "icon": "📋",
    },
    {
        "label": "Demande Congé Stagiaire",
        "doctype": "Demande Conge Stagiaire",
        "route": "/demande-conge-stagiaire",
        "employee_field": "employee",
        "date_fields": ["date_debut", "from_date", "creation"],
        "audience": {"stage"},
        "icon": "🏖️",
    },
    {
        "label": "Planning de Congé",
        "doctype": "Planning Conge",
        "route": "/planning-conge",
        "employee_field": "employee",
        "date_fields": ["creation"],
        "audience": {"employee", "prestataire"},
        "icon": "📅",
    },
    {
        "label": "Demande de Congé",
        "doctype": "Leave Application",
        "route": "/demande-conge",
        "employee_field": "employee",
        "date_fields": ["from_date", "creation"],
        "audience": {"employee", "prestataire"},
        "icon": "✈️",
    },
    {
        "label": "Demande d'Achat",
        "doctype": "Demande Achat KYA",
        "route": "/demande-achat",
        "employee_field": "employee",
        "date_fields": ["date_demande", "creation"],
        "audience": {"employee", "stage", "prestataire"},
        "icon": "🛒",
    },
    {
        "label": "PV Sortie Matériel",
        "doctype": "PV Sortie Materiel",
        "route": "/pv-sortie-materiel",
        "employee_field": "employee",
        "date_fields": ["date_sortie", "creation"],
        "audience": {"employee", "stage", "prestataire"},
        "icon": "📦",
    },
    {
        "label": "Contrat KYA",
        "doctype": "KYA Contrat",
        "route": "/kya-contrat",
        "employee_field": "employee",
        "date_fields": ["creation"],
        "audience": {"employee", "stage", "prestataire"},
        "icon": "📝",
    },
]

FORM_SPECS = [
    {"label": "Permission de Sortie", "route": "permission-sortie-employe", "icon": "🚪", "audience": {"employee", "prestataire"}},
    {"label": "Permission de Sortie Stagiaire", "route": "permission-sortie-stagiaire", "icon": "🎓", "audience": {"stage"}},
    {"label": "Bilan de Fin de Stage", "route": "bilan-fin-de-stage", "icon": "📋", "audience": {"stage"}},
    {"label": "PV Sortie Matériel", "route": "pv-sortie-materiel", "icon": "📦", "audience": {"employee", "stage", "prestataire"}},
    {"label": "Demande d'Achat", "route": "demande-achat", "icon": "🛒", "audience": {"employee", "stage", "prestataire"}},
    {"label": "Planning de Congé", "route": "planning-conge", "icon": "🏖️", "audience": {"employee", "prestataire"}},
    {"label": "Demande de Congé", "route": "demande-conge", "icon": "✈️", "audience": {"employee", "prestataire"}},
]


def _doctype_exists(doctype):
    return bool(frappe.db.exists("DocType", doctype))


def _has_field(doctype, fieldname):
    try:
        return fieldname in {field.fieldname for field in frappe.get_meta(doctype).fields}
    except Exception:
        return False


def _existing_fields(doctype, candidates):
    base_fields = {"name", "owner", "creation", "modified", "docstatus"}
    fields = []
    for fieldname in candidates:
        if fieldname in base_fields or _has_field(doctype, fieldname):
            fields.append(fieldname)
    return fields


def _category(employee):
    if not employee:
        return "unknown"
    if (employee.get("employment_type") or "") in STAGE_TYPES:
        return "stage"
    if (employee.get("employment_type") or "").lower().startswith("prestataire"):
        return "prestataire"
    return "employee"


def _state_label(row):
    return row.get("workflow_state") or row.get("statut") or row.get("status") or ("Soumis" if cint(row.get("docstatus")) else "Brouillon")


def _state_bucket(state, docstatus=0):
    value = (state or "").lower()
    if "rejet" in value or "annul" in value or "refus" in value:
        return "rejete"
    if "approuv" in value or "valid" in value or "final" in value or "signé" in value or "signe" in value:
        return "approuve"
    if "attente" in value or "cours" in value or "soumis" in value:
        return "en_cours"
    if cint(docstatus) == 1:
        return "approuve"
    return "brouillon"


def _state_class(bucket):
    return {
        "approuve": "ok",
        "rejete": "ko",
        "en_cours": "encours",
        "brouillon": "draft",
    }.get(bucket, "draft")


def _doc_date(row, spec):
    for fieldname in spec.get("date_fields") or []:
        if row.get(fieldname):
            return row.get(fieldname)
    return row.get("modified") or row.get("creation")


def _route_for(spec, name):
    return f"{spec['route']}/{name}"


def _get_employee(user):
    if user == "Guest":
        return None
    return frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "designation", "department", "image", "employment_type", "company_email", "personal_email", "user_id"],
        as_dict=True,
    )


def _collect_requests(employee, user, category, limit=40):
    requests = []
    stats = {"total": 0, "brouillon": 0, "en_cours": 0, "approuve": 0, "rejete": 0}

    if not employee:
        return requests, stats

    for spec in REQUEST_SPECS:
        if category not in spec["audience"] or not _doctype_exists(spec["doctype"]):
            continue

        doctype = spec["doctype"]
        employee_field = spec.get("employee_field") or "employee"
        if _has_field(doctype, employee_field):
            filters = {employee_field: employee.name}
        else:
            filters = {"owner": user}

        fields = _existing_fields(
            doctype,
            ["name", "owner", "creation", "modified", "docstatus", "workflow_state", "statut", "status"] + spec.get("date_fields", []),
        )
        try:
            rows = frappe.get_all(
                doctype,
                filters=filters,
                fields=fields,
                order_by="modified desc",
                limit_page_length=limit,
            )
        except Exception:
            continue

        for row in rows:
            state = _state_label(row)
            bucket = _state_bucket(state, row.get("docstatus"))
            stats["total"] += 1
            stats[bucket] = stats.get(bucket, 0) + 1
            requests.append({
                "doctype": doctype,
                "name": row.name,
                "label": spec["label"],
                "icon": spec.get("icon"),
                "status": state,
                "bucket": bucket,
                "state_class": _state_class(bucket),
                "date": _doc_date(row, spec),
                "modified": row.get("modified") or row.get("creation"),
                "url": _route_for(spec, row.name),
            })

    requests.sort(key=lambda item: str(item.get("modified") or ""), reverse=True)
    return requests[:limit], stats


def _collect_form_notifications(employee):
    notifications = []
    if not employee:
        return notifications

    if frappe.db.exists("DocType", "KYA Form Response") and frappe.db.exists("DocType", "KYA Form"):
        try:
            rows = frappe.db.sql(
                """
                SELECT kfr.name, kfr.formulaire, kfr.token, kf.titre, kf.type_formulaire, kf.date_limite
                FROM `tabKYA Form Response` kfr
                LEFT JOIN `tabKYA Form` kf ON kf.name = kfr.formulaire
                WHERE kfr.employe = %s
                  AND (kfr.soumis_le IS NULL OR kfr.soumis_le = '')
                ORDER BY COALESCE(kf.date_limite, kfr.creation) ASC
                LIMIT 10
                """,
                employee.name,
                as_dict=True,
            )
            for row in rows:
                notifications.append({
                    "type": "form",
                    "title": row.titre or row.formulaire or "Formulaire KYA",
                    "text": "Formulaire à remplir",
                    "url": f"/kya-survey?token={row.token}" if row.token else "",
                    "date": row.date_limite,
                    "state_class": "encours",
                })
        except Exception:
            pass

    if frappe.db.exists("DocType", "KYA Evaluation"):
        try:
            rows = frappe.get_all(
                "KYA Evaluation",
                filters={"evaluateur": employee.name, "soumis_le": ["is", "not set"]},
                fields=_existing_fields("KYA Evaluation", ["name", "type_evaluation", "evalue_name", "trimestre", "annee", "token", "creation"]),
                order_by="creation desc",
                limit_page_length=10,
            )
            for row in rows:
                notifications.append({
                    "type": "evaluation",
                    "title": row.get("type_evaluation") or "Évaluation KYA",
                    "text": row.get("evalue_name") or "Évaluation à compléter",
                    "url": f"/kya-eval?token={row.token}" if row.get("token") else f"/app/kya-evaluation/{row.name}",
                    "date": f"{row.get('trimestre') or ''} {row.get('annee') or ''}".strip(),
                    "state_class": "encours",
                })
        except Exception:
            pass

    return notifications


def _collect_system_notifications(user):
    notifications = []
    if _doctype_exists("Notification Log"):
        fields = _existing_fields("Notification Log", ["name", "subject", "document_type", "document_name", "read", "creation"])
        try:
            rows = frappe.get_all(
                "Notification Log",
                filters={"for_user": user, "read": 0} if _has_field("Notification Log", "read") else {"for_user": user},
                fields=fields,
                order_by="creation desc",
                limit_page_length=10,
            )
            for row in rows:
                doctype = row.get("document_type")
                docname = row.get("document_name")
                notifications.append({
                    "type": "notification",
                    "title": row.get("subject") or "Notification",
                    "text": doctype or "Notification système",
                    "url": f"/app/{frappe.scrub(doctype).replace('_', '-')}/{docname}" if doctype and docname else "/app/notification-log",
                    "date": row.get("creation"),
                    "state_class": "encours",
                })
        except Exception:
            pass
    return notifications


def _collect_pending_actions(user):
    actions = []
    if _doctype_exists("ToDo"):
        try:
            rows = frappe.get_all(
                "ToDo",
                filters={"allocated_to": user, "status": ["!=", "Closed"]},
                fields=_existing_fields("ToDo", ["name", "description", "reference_type", "reference_name", "date", "priority", "creation"]),
                order_by="creation desc",
                limit_page_length=15,
            )
            for row in rows:
                ref_type = row.get("reference_type")
                ref_name = row.get("reference_name")
                actions.append({
                    "type": "todo",
                    "title": row.get("description") or "Action à faire",
                    "status": row.get("priority") or "Ouvert",
                    "url": f"/app/{frappe.scrub(ref_type).replace('_', '-')}/{ref_name}" if ref_type and ref_name else f"/app/todo/{row.name}",
                    "date": row.get("date") or row.get("creation"),
                    "state_class": "encours",
                })
        except Exception:
            pass

    if _doctype_exists("Workflow Action"):
        meta_fields = _existing_fields("Workflow Action", ["name", "reference_doctype", "reference_name", "workflow_state", "status", "creation", "user"])
        filters = {"user": user} if _has_field("Workflow Action", "user") else {"owner": user}
        if _has_field("Workflow Action", "status"):
            filters["status"] = ["in", ["Open", "Pending"]]
        try:
            rows = frappe.get_all(
                "Workflow Action",
                filters=filters,
                fields=meta_fields,
                order_by="creation desc",
                limit_page_length=15,
            )
            for row in rows:
                ref_type = row.get("reference_doctype")
                ref_name = row.get("reference_name")
                actions.append({
                    "type": "workflow",
                    "title": ref_type or "Validation workflow",
                    "status": row.get("workflow_state") or row.get("status") or "À traiter",
                    "url": f"/app/{frappe.scrub(ref_type).replace('_', '-')}/{ref_name}" if ref_type and ref_name else "/app/workflow-action",
                    "date": row.get("creation"),
                    "state_class": "encours",
                })
        except Exception:
            pass

    return actions[:20]


def _available_forms(category):
    return [form.copy() for form in FORM_SPECS if category in form["audience"]]


def build_mon_espace_context(user=None):
    user = user or frappe.session.user
    employee = _get_employee(user)
    category = _category(employee)
    requests, stats = _collect_requests(employee, user, category)
    form_notifications = _collect_form_notifications(employee)
    system_notifications = _collect_system_notifications(user)
    pending_actions = _collect_pending_actions(user)

    notifications = (form_notifications + system_notifications + pending_actions)[:20]
    return {
        "employee": employee,
        "category": category,
        "is_stagiaire": category == "stage",
        "available_forms": _available_forms(category),
        "requests": requests,
        "stats": stats,
        "form_notifications": form_notifications,
        "system_notifications": system_notifications,
        "pending_actions": pending_actions,
        "notifications": notifications,
        "notification_count": len(notifications),
    }


@frappe.whitelist()
def get_mon_espace_sync():
    """Payload synchronisé pour /mon-espace, filtré sur l'utilisateur connecté."""
    if frappe.session.user == "Guest":
        return {"employee": None, "requests": [], "stats": {}, "notifications": []}
    return build_mon_espace_context()

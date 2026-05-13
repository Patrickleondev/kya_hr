"""KYA Leave Application guardrails.

The public web form uses HRMS Leave Application, but KYA needs a four-step
business approval path:

Employee -> Superior (Employee.reports_to) -> RH -> DG.

This module keeps that path practical for local/preprod deployments by
auto-provisioning missing leave allocations and enforcing signatures server-side.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate


SIGNATURE_FIELDS = {
    "signature_employe_la": {
        "date_field": "date_signature_employe_la",
        "states": {"Brouillon", "Draft", "Open"},
        "label": "Employé",
    },
    "signature_superieur_la": {
        "date_field": "date_signature_superieur_la",
        "states": {"En attente du Supérieur Immédiat", "En attente Supérieur", "En attente Chef"},
        "label": "Supérieur immédiat",
    },
    "signature_rh_la": {
        "date_field": "date_signature_rh_la",
        "states": {"En attente RH"},
        "label": "RH",
    },
    "signature_dg_la": {
        "date_field": "date_signature_dg_la",
        "states": {"En attente DG"},
        "label": "DG",
    },
}

RH_ROLES = {"Responsable RH", "HR Manager", "HR User"}
DG_ROLES = {"Directeur Général", "DG"}
SUPERIOR_ROLES = {"Supérieur Immédiat", "Chef Service"}
ADMIN_ROLES = {"System Manager"}


def before_validate(doc, method=None):
    _populate_employee_context(doc)
    _ensure_default_holiday_list(doc)
    _ensure_flexible_leave_allocation(doc)


def before_save(doc, method=None):
    _populate_employee_context(doc)
    _route_special_requesters(doc)
    _sync_hrms_status(doc)


def validate(doc, method=None):
    _validate_employee_scope(doc)
    _sync_hrms_status(doc)
    _guard_signature_changes(doc)
    _set_signature_dates(doc)


def on_update(doc, method=None):
    _sync_signature_dates_after_workflow(doc)


def ensure_setup():
    """Idempotent post-migrate setup for fields and workflow consistency."""
    _ensure_report_to_user_field()
    _ensure_workflow_states()
    _ensure_workflow_action_masters()
    _ensure_default_company_holiday_lists()
    _ensure_workflow_transitions()


def requester_is_rh(doc) -> bool:
    return bool(_requester_roles(doc) & RH_ROLES)


def requester_is_dg(doc) -> bool:
    return bool(_requester_roles(doc) & DG_ROLES)


def requester_is_superior(doc) -> bool:
    return bool(_requester_roles(doc) & SUPERIOR_ROLES)


def _current_roles(user=None) -> set[str]:
    if (user or frappe.session.user) == "Administrator":
        return {"Administrator", "System Manager"}
    return set(frappe.get_roles(user or frappe.session.user))


def _requester_user(doc) -> str | None:
    if not doc.get("employee"):
        return None
    return frappe.db.get_value("Employee", doc.employee, "user_id")


def _requester_roles(doc) -> set[str]:
    user = _requester_user(doc)
    return set(frappe.get_roles(user)) if user else set()


def _current_employee(user=None) -> str | None:
    return frappe.db.get_value(
        "Employee",
        {"user_id": user or frappe.session.user, "status": "Active"},
        "name",
    )


def _can_select_any_employee(user=None) -> bool:
    roles = _current_roles(user)
    return bool((ADMIN_ROLES | RH_ROLES) & roles) or "Administrator" in roles


def _is_requester(doc, user=None) -> bool:
    user = user or frappe.session.user
    requester = _requester_user(doc)
    return bool(user and (user == requester or user == doc.owner))


def _populate_employee_context(doc) -> None:
    if not doc.get("employee"):
        current_employee = _current_employee()
        if current_employee:
            doc.employee = current_employee

    if doc.get("employee"):
        employee = frappe.db.get_value(
            "Employee",
            doc.employee,
            ["employee_name", "department", "company", "reports_to", "user_id"],
            as_dict=True,
        )
        if employee:
            if not doc.get("employee_name") and employee.employee_name:
                doc.employee_name = employee.employee_name
            if not doc.get("department") and employee.department:
                doc.department = employee.department
            if not doc.get("company") and employee.company:
                doc.company = employee.company

            report_to_user = None
            if employee.reports_to:
                report_to_user = frappe.db.get_value("Employee", employee.reports_to, "user_id")
            if hasattr(doc, "report_to_user") or frappe.db.has_column("Leave Application", "report_to_user"):
                doc.report_to_user = report_to_user
            if not doc.get("leave_approver") and report_to_user:
                doc.leave_approver = report_to_user

    if not doc.get("posting_date"):
        doc.posting_date = nowdate()


def _validate_employee_scope(doc) -> None:
    user = frappe.session.user
    if user in ("Administrator", "Guest") or _can_select_any_employee(user):
        return
    current_employee = _current_employee(user)
    if not current_employee:
        frappe.throw(_("Aucun employé actif n'est lié à votre compte utilisateur."))
    if doc.employee != current_employee:
        frappe.throw(_("Vous ne pouvez pas créer une demande de congé pour un autre employé."))


def _ensure_flexible_leave_allocation(doc) -> None:
    """Create or widen a submitted allocation so HRMS does not block the request.

    KYA still keeps the Leave Application workflow approval path. This only avoids
    the operational dead-end where a valid request cannot even be submitted
    because the yearly allocation was not initialized on a test/preprod site.
    """
    if not (doc.get("employee") and doc.get("leave_type") and doc.get("from_date") and doc.get("to_date")):
        return
    if frappe.db.get_value("Leave Type", doc.leave_type, "is_lwp"):
        return

    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)
    if to_date < from_date:
        return

    requested_days = max(date_diff(to_date, from_date) + 1, 1)
    max_days = frappe.db.get_value("Leave Type", doc.leave_type, "max_leaves_allowed") or requested_days
    allocation_days = max(float(max_days or 0), float(requested_days))

    existing = frappe.db.sql(
        """
        SELECT name, from_date, to_date, new_leaves_allocated
        FROM `tabLeave Allocation`
        WHERE employee = %s
          AND leave_type = %s
          AND docstatus = 1
          AND from_date <= %s
          AND to_date >= %s
        ORDER BY to_date DESC
        LIMIT 1
        """,
        (doc.employee, doc.leave_type, to_date, from_date),
        as_dict=True,
    )
    if existing:
        row = existing[0]
        new_from = min(getdate(row.from_date), from_date)
        new_to = max(getdate(row.to_date), to_date)
        new_total = max(float(row.new_leaves_allocated or 0), allocation_days)
        frappe.db.set_value(
            "Leave Allocation",
            row.name,
            {"from_date": new_from, "to_date": new_to, "new_leaves_allocated": new_total},
            update_modified=False,
        )
        return

    year_from = getdate(f"{from_date.year}-01-01")
    year_to = getdate(f"{to_date.year}-12-31")
    company = doc.get("company") or frappe.db.get_value("Employee", doc.employee, "company")

    allocation = frappe.get_doc(
        {
            "doctype": "Leave Allocation",
            "employee": doc.employee,
            "leave_type": doc.leave_type,
            "from_date": year_from,
            "to_date": year_to,
            "new_leaves_allocated": allocation_days,
            "company": company,
        }
    )
    allocation.flags.ignore_permissions = True
    allocation.flags.ignore_links = True
    allocation.insert(ignore_permissions=True)
    allocation.submit()


def _ensure_default_holiday_list(doc) -> None:
    company = doc.get("company") or (
        frappe.db.get_value("Employee", doc.employee, "company") if doc.get("employee") else None
    )
    if company:
        _ensure_company_holiday_list(company)


def _ensure_default_company_holiday_lists() -> None:
    for company in frappe.get_all("Company", pluck="name"):
        _ensure_company_holiday_list(company)


def _ensure_company_holiday_list(company: str) -> str:
    existing = frappe.db.get_value("Company", company, "default_holiday_list")
    if existing and frappe.db.exists("Holiday List", existing):
        return existing

    current_year = getdate(nowdate()).year
    list_name = f"{company} - KYA Default Holidays {current_year}"
    if not frappe.db.exists("Holiday List", list_name):
        holiday_list = frappe.get_doc(
            {
                "doctype": "Holiday List",
                "holiday_list_name": list_name,
                "from_date": f"{current_year}-01-01",
                "to_date": f"{current_year + 1}-12-31",
                "weekly_off": "Sunday",
            }
        )
        holiday_list.insert(ignore_permissions=True)
    frappe.db.set_value("Company", company, "default_holiday_list", list_name, update_modified=False)
    return list_name


def _route_special_requesters(doc) -> None:
    if not doc.get("workflow_state") or doc.is_new():
        return
    if not doc.has_value_changed("workflow_state"):
        return

    if requester_is_rh(doc) and doc.workflow_state in {
        "En attente du Supérieur Immédiat",
        "En attente Supérieur",
        "En attente Chef",
        "En attente RH",
    }:
        doc.workflow_state = "En attente DG"
    elif requester_is_superior(doc) and doc.workflow_state in {
        "En attente du Supérieur Immédiat",
        "En attente Supérieur",
        "En attente Chef",
    }:
        doc.workflow_state = "En attente RH"
    elif requester_is_dg(doc) and doc.workflow_state == "En attente DG":
        doc.workflow_state = "Approuvé"


def _sync_hrms_status(doc) -> None:
    state = doc.get("workflow_state")
    if state == "Approuvé":
        doc.status = "Approved"
    elif state == "Rejeté":
        doc.status = "Rejected"
    elif not doc.get("status"):
        doc.status = "Open"


def _guard_signature_changes(doc) -> None:
    old = doc.get_doc_before_save()
    current_state = doc.get("workflow_state") or "Brouillon"

    for fieldname, cfg in SIGNATURE_FIELDS.items():
        if not hasattr(doc, fieldname):
            continue
        new_value = doc.get(fieldname)
        old_value = old.get(fieldname) if old else None
        if not new_value or new_value == old_value:
            continue

        if current_state not in cfg["states"]:
            frappe.throw(
                _("La signature {0} n'est pas autorisée à l'état {1}.").format(
                    cfg["label"], current_state
                )
            )
        _assert_can_sign(doc, fieldname)


def _assert_can_sign(doc, fieldname: str) -> None:
    user = frappe.session.user
    roles = _current_roles(user)
    if user == "Administrator" or ADMIN_ROLES & roles:
        return

    if fieldname == "signature_employe_la":
        if not _is_requester(doc, user):
            frappe.throw(_("Seul l'employé demandeur peut signer la partie Employé."))
        return

    if _is_requester(doc, user):
        frappe.throw(_("Vous ne pouvez pas signer une étape d'approbation de votre propre demande."))

    if fieldname == "signature_superieur_la":
        expected = doc.get("report_to_user")
        if not expected:
            frappe.throw(_("Aucun supérieur immédiat n'est configuré pour cet employé."))
        if user != expected:
            frappe.throw(_("Seul le supérieur immédiat configuré sur la fiche Employé peut signer."))
        if not (roles & SUPERIOR_ROLES):
            frappe.throw(_("Le signataire doit avoir le rôle Supérieur Immédiat ou Chef Service."))
        return

    if fieldname == "signature_rh_la":
        if not (roles & RH_ROLES):
            frappe.throw(_("Cette signature est réservée à la RH."))
        return

    if fieldname == "signature_dg_la":
        if not (roles & DG_ROLES):
            frappe.throw(_("Cette signature est réservée au Directeur Général."))


def _set_signature_dates(doc) -> None:
    for fieldname, cfg in SIGNATURE_FIELDS.items():
        date_field = cfg["date_field"]
        if doc.get(fieldname) and hasattr(doc, date_field) and not doc.get(date_field):
            doc.set(date_field, nowdate())


def _sync_signature_dates_after_workflow(doc) -> None:
    updates = {}
    for fieldname, cfg in SIGNATURE_FIELDS.items():
        date_field = cfg["date_field"]
        if doc.get(fieldname) and hasattr(doc, date_field) and not doc.get(date_field):
            updates[date_field] = nowdate()
    if updates:
        frappe.db.set_value(doc.doctype, doc.name, updates, update_modified=False)


def _ensure_report_to_user_field() -> None:
    if frappe.db.exists("Custom Field", "Leave Application-report_to_user"):
        return
    field = frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": "Leave Application",
            "fieldname": "report_to_user",
            "label": "Utilisateur supérieur immédiat",
            "fieldtype": "Data",
            "insert_after": "leave_approver",
            "hidden": 1,
            "read_only": 1,
            "no_copy": 1,
            "description": "Auto: Employee.reports_to.user_id",
        }
    )
    field.insert(ignore_permissions=True)


def _ensure_workflow_states() -> None:
    for state_name in ("En attente du Supérieur Immédiat",):
        if not frappe.db.exists("Workflow State", state_name):
            frappe.get_doc(
                {
                    "doctype": "Workflow State",
                    "workflow_state_name": state_name,
                    "style": "Warning",
                }
            ).insert(ignore_permissions=True)


def _ensure_workflow_action_masters() -> None:
    for action in ("Soumettre", "Approuver", "Rejeter"):
        if frappe.db.exists("Workflow Action Master", action):
            continue
        frappe.get_doc(
            {
                "doctype": "Workflow Action Master",
                "workflow_action_name": action,
            }
        ).insert(ignore_permissions=True)


def _ensure_workflow_transitions() -> None:
    workflow_name = frappe.db.get_value(
        "Workflow",
        {"document_type": "Leave Application", "is_active": 1},
        "name",
    )
    if not workflow_name:
        return

    workflow = frappe.get_doc("Workflow", workflow_name)
    managed_states = {
        "Brouillon",
        "En attente du Supérieur Immédiat",
        "En attente RH",
        "En attente DG",
    }
    workflow.transitions = [
        row for row in workflow.transitions
        if row.state not in managed_states
    ]

    transitions = [
        ("Brouillon", "Soumettre", "En attente du Supérieur Immédiat", "Employee", 1),
        ("En attente du Supérieur Immédiat", "Approuver", "En attente RH", "Supérieur Immédiat", 0),
        ("En attente du Supérieur Immédiat", "Rejeter", "Rejeté", "Supérieur Immédiat", 0),
        ("En attente RH", "Approuver", "En attente DG", "Responsable RH", 0),
        ("En attente RH", "Rejeter", "Rejeté", "Responsable RH", 0),
        ("En attente DG", "Approuver", "Approuvé", "Directeur Général", 0),
        ("En attente DG", "Rejeter", "Rejeté", "Directeur Général", 0),
    ]
    for state, action, next_state, allowed, allow_self_approval in transitions:
        workflow.append(
            "transitions",
            {
                "state": state,
                "action": action,
                "next_state": next_state,
                "allowed": allowed,
                "allow_self_approval": allow_self_approval,
                "condition": None,
            },
        )
    for row in workflow.states:
        if row.state == "Approuvé":
            row.update_field = "status"
            row.update_value = "Approved"
        elif row.state == "Rejeté":
            row.update_field = "status"
            row.update_value = "Rejected"
    workflow.save(ignore_permissions=True)

import frappe
from frappe.utils import getdate


def create_leave_from_planning(doc, method=None):
    """
    Quand un Planning Congé passe à l'état 'Approuvé', crée automatiquement
    des Leave Application HRMS pour chaque période afin de décompter les soldes.
    Appelé via doc_events on_update.
    """
    if doc.workflow_state != "Approuvé":
        return

    # Vérifier qu'on n'a pas déjà créé les Leave Application pour ce planning
    if doc.flags.get("leave_apps_created"):
        return

    existing = frappe.db.exists("Leave Application", {
        "custom_planning_conge": doc.name,
    })
    if existing:
        return  # Déjà créé précédemment

    if not doc.periodes:
        return

    created = []
    errors = []

    for row in doc.periodes:
        if not row.date_debut or not row.date_fin or not row.type_conge:
            continue

        try:
            leave = frappe.get_doc({
                "doctype": "Leave Application",
                "employee": doc.employee,
                "leave_type": row.type_conge,
                "from_date": getdate(row.date_debut),
                "to_date": getdate(row.date_fin),
                "description": f"Créé depuis Planning Congé {doc.name} (période {row.idx})",
                "status": "Approved",
                "leave_approver": _get_leave_approver(doc.employee),
                "custom_planning_conge": doc.name,
            })
            leave.flags.ignore_permissions = True
            leave.flags.ignore_validate = False
            leave.insert()
            leave.submit()
            created.append(leave.name)
        except Exception as e:
            errors.append(f"Période {row.idx} ({row.date_debut} → {row.date_fin}): {str(e)}")

    doc.flags.leave_apps_created = True

    if created:
        frappe.msgprint(
            f"✅ {len(created)} demande(s) de congé HRMS créée(s) automatiquement : "
            + ", ".join(created),
            alert=True,
            indicator="green",
        )
    if errors:
        frappe.msgprint(
            "⚠️ Erreurs lors de la création de certaines demandes de congé :<br>"
            + "<br>".join(errors),
            alert=True,
            indicator="orange",
        )


def _get_leave_approver(employee):
    """Récupère le leave_approver de l'employé, ou un fallback HR Manager."""
    approver = frappe.db.get_value("Employee", employee, "leave_approver")
    if approver:
        return approver

    # Fallback : premier utilisateur avec le rôle Leave Approver ou HR Manager
    hr = frappe.db.get_value(
        "Has Role",
        {"role": ["in", ["Leave Approver", "HR Manager"]], "parenttype": "User"},
        "parent",
    )
    return hr or "Administrator"

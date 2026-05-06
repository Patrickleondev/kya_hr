"""Normalize KYA Notification recipients after fixtures import.

Some legacy fixtures pointed final notifications to Employee Link fields.
Frappe Notification expects an email/user field there, so keep this idempotent
post-migrate fix after fixture sync.
"""

import frappe


FIELD_FIXES = {
    "KYA - PV Matériel: En attente Chef": "report_to_user",
    "KYA - Permission Stagiaire: Approuvée": "owner",
    "KYA - Permission Stagiaire: Rejetée": "owner",
    "KYA - Permission Employé: Approuvée": "owner",
    "KYA - Permission Employé: Rejetée": "owner",
    "KYA - Planning Congé: Approuvé": "owner",
    "KYA - Planning Congé: Rejeté": "owner",
}

ROLE_FIXES = {
    "Directeur General": "Directeur Général",
}


def _fix_recipient_field(notification_name, fieldname):
    parent = frappe.db.exists("Notification", notification_name)
    if not parent:
        return False

    rows = frappe.get_all(
        "Notification Recipient",
        filters={"parent": notification_name},
        fields=["name", "receiver_by_document_field", "receiver_by_role"],
        limit_page_length=20,
    )
    changed = False
    for row in rows:
        if row.receiver_by_document_field == fieldname and not row.receiver_by_role:
            continue
        frappe.db.set_value(
            "Notification Recipient",
            row.name,
            {
                "receiver_by_document_field": fieldname,
                "receiver_by_role": None,
            },
            update_modified=False,
        )
        changed = True
    return changed


def _fix_role(old_role, new_role):
    if not frappe.db.exists("Role", new_role):
        return 0
    rows = frappe.get_all(
        "Notification Recipient",
        filters={"receiver_by_role": old_role},
        pluck="name",
        limit_page_length=200,
    )
    for name in rows:
        frappe.db.set_value(
            "Notification Recipient",
            name,
            "receiver_by_role",
            new_role,
            update_modified=False,
        )
    return len(rows)


def execute():
    if not frappe.db.has_table("Notification Recipient"):
        return {"skipped": True}

    changed_fields = []
    for notification_name, fieldname in FIELD_FIXES.items():
        if _fix_recipient_field(notification_name, fieldname):
            changed_fields.append(notification_name)

    changed_roles = {}
    for old_role, new_role in ROLE_FIXES.items():
        count = _fix_role(old_role, new_role)
        if count:
            changed_roles[old_role] = {"new_role": new_role, "count": count}

    frappe.db.commit()
    frappe.clear_cache()

    result = {"field_fixes": changed_fields, "role_fixes": changed_roles}
    print(f"[kya_hr.notification_fixes] {result}")
    return result


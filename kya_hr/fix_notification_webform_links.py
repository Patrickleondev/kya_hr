"""Normalize notification links to KYA web forms.

This ensures emails always point to '/<route>?name=<DOC>' instead of
legacy '/<route>/<DOC>' URLs that can trigger "Not found" on Web Form pages.
"""

import frappe


KYA_WEBFORM_ROUTES = [
    "permission-sortie-stagiaire",
    "permission-sortie-employe",
    "demande-achat",
    "pv-sortie-materiel",
    "planning-conge",
    "bilan-fin-de-stage",
]


def _normalize_message_links(message: str) -> str:
    if not message:
        return message

    normalized = message
    for route in KYA_WEBFORM_ROUTES:
        legacy_patterns = [
            f"/{route}/{{{{ doc.name }}}}",
            f"/{route}/{{{{doc.name}}}}",
        ]
        target = f"/{route}?name={{{{ doc.name }}}}"

        for legacy in legacy_patterns:
            normalized = normalized.replace(legacy, target)

    return normalized


def execute():
    """After-migrate hook: repair notification webform links in DB."""
    notifications = frappe.get_all("Notification", fields=["name", "message"])

    updated = 0
    for n in notifications:
        old_message = n.get("message") or ""
        new_message = _normalize_message_links(old_message)

        if new_message != old_message:
            frappe.db.set_value("Notification", n["name"], "message", new_message, update_modified=False)
            updated += 1

    if updated:
        frappe.db.commit()
        frappe.logger("kya_hr").info(
            "[fix_notification_webform_links] Updated %s notifications with normalized webform links",
            updated,
        )

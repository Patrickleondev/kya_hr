"""
KYA HR — Rappels automatiques (anniversaires, ancienneté)

Envoi quotidien aux utilisateurs ayant le rôle « KYA Destinataire Notif ».
"""

import frappe
from frappe.utils import today, getdate

ROLE_NOTIF = "KYA Destinataire Notif"


def send_kya_birthday_reminders():
    """Envoie un rappel d'anniversaire de naissance aux destinataires KYA."""
    today_date = getdate(today())

    employees = frappe.db.sql(
        """
        SELECT name, employee_name, date_of_birth, department, designation
        FROM `tabEmployee`
        WHERE status = 'Active'
          AND (employment_type IS NULL OR employment_type != 'Stage')
          AND DAY(date_of_birth) = %s
          AND MONTH(date_of_birth) = %s
        """,
        (today_date.day, today_date.month),
        as_dict=True,
    )
    if not employees:
        return

    recipients = _get_notif_recipients()
    if not recipients:
        return

    from kya_hr.utils import get_kya_email_footer

    footer = get_kya_email_footer()

    for emp in employees:
        age = today_date.year - emp.date_of_birth.year
        subject = f"\U0001f382 Anniversaire \u2014 {emp.employee_name}"
        message = (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#ff8f00,#ffa726);padding:24px;"
            "border-radius:12px 12px 0 0;text-align:center;'>"
            "<img src='https://www.kya-energy.com/wp-content/uploads/2024/02/Logo-10-ans-KYA.png'"
            " width='60' style='margin-bottom:8px;'>"
            "<h2 style='color:white;margin:0;'>\U0001f382 Joyeux Anniversaire !</h2></div>"
            "<div style='background:white;padding:24px;border:1px solid #e0e0e0;"
            "border-radius:0 0 12px 12px;'>"
            "<p>Chers coll\u00e8gues,</p>"
            f"<p>Aujourd\u2019hui, <b>{emp.employee_name}</b>"
            f" ({emp.designation or ''} \u2014 {emp.department or ''})"
            f" f\u00eate ses <b>{age} ans</b> !</p>"
            "<p>Toute l\u2019\u00e9quipe KYA-Energy Group lui souhaite un "
            "<b>tr\u00e8s joyeux anniversaire</b> \U0001f389</p>"
            "</div>"
            f"{footer}"
            "</div>"
        )
        frappe.sendmail(recipients=recipients, subject=subject, message=message, now=True)


def send_kya_anniversary_reminders():
    """Envoie un rappel d'anniversaire de service aux destinataires KYA."""
    today_date = getdate(today())

    employees = frappe.db.sql(
        """
        SELECT name, employee_name, date_of_joining, department, designation
        FROM `tabEmployee`
        WHERE status = 'Active'
          AND (employment_type IS NULL OR employment_type != 'Stage')
          AND DAY(date_of_joining) = %s
          AND MONTH(date_of_joining) = %s
          AND YEAR(date_of_joining) < %s
        """,
        (today_date.day, today_date.month, today_date.year),
        as_dict=True,
    )
    if not employees:
        return

    recipients = _get_notif_recipients()
    if not recipients:
        return

    from kya_hr.utils import get_kya_email_footer

    footer = get_kya_email_footer()

    for emp in employees:
        years = today_date.year - emp.date_of_joining.year
        plural = "s" if years > 1 else ""
        subject = (
            f"\U0001f3c6 Anniversaire de service \u2014 "
            f"{emp.employee_name} ({years} an{plural})"
        )
        message = (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#1565c0,#42a5f5);padding:24px;"
            "border-radius:12px 12px 0 0;text-align:center;'>"
            "<img src='https://www.kya-energy.com/wp-content/uploads/2024/02/Logo-10-ans-KYA.png'"
            " width='60' style='margin-bottom:8px;'>"
            "<h2 style='color:white;margin:0;'>\U0001f3c6 Anniversaire de Service</h2></div>"
            "<div style='background:white;padding:24px;border:1px solid #e0e0e0;"
            "border-radius:0 0 12px 12px;'>"
            "<p>Chers coll\u00e8gues,</p>"
            f"<p>Aujourd\u2019hui, <b>{emp.employee_name}</b>"
            f" ({emp.designation or ''} \u2014 {emp.department or ''})"
            f" c\u00e9l\u00e8bre <b>{years} an{plural}</b>"
            " au sein de KYA-Energy Group !</p>"
            "<p>Merci pour votre d\u00e9vouement et votre engagement \U0001f64f</p>"
            "</div>"
            f"{footer}"
            "</div>"
        )
        frappe.sendmail(recipients=recipients, subject=subject, message=message, now=True)


def _get_notif_recipients():
    """Retourne la liste d'emails des utilisateurs ayant le rôle KYA Destinataire Notif."""
    users = frappe.get_all(
        "Has Role",
        filters={"role": ROLE_NOTIF, "parenttype": "User"},
        pluck="parent",
    )
    return [u for u in set(users) if frappe.db.get_value("User", u, "enabled")]

"""
KYA HR — Rappels automatiques (anniversaires de naissance et d'ancienneté).

Envoi quotidien a l'equipe RH + Direction. Les stagiaires sont exclus.
Destinataires : la RH (HR Manager, HR User, Responsable RH) et la Direction
(Directeur Général, DGA). On NE précise PAS l'âge de la personne.
"""

import frappe
from frappe.utils import today, getdate

# Roles qui recoivent les rappels : la RH et le DG uniquement (pas System
# Manager, pour ne pas arroser les comptes techniques/admin).
REMINDER_ROLES = (
    "HR Manager",
    "HR User",
    "Responsable RH",
    "Directeur Général",  # DG
    "DGA",
)

# Types d'emploi exclus (stagiaires)
EXCLUDED_TYPES = ("Stage", "Intern", "Apprentice")


def _email_header(bg, emoji, title):
    # Logo embarqué INLINE (CID) via `embed=` : Frappe lit le fichier sur le
    # disque et l'attache à l'e-mail. Robuste derrière le SSO Pangolin et non
    # bloqué par Gmail (contrairement à une URL <img src> vers le site, que les
    # clients mail ne peuvent pas charger → image cassée).
    return (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
        "<div style='background:{bg};padding:24px;border-radius:12px 12px 0 0;text-align:center;'>"
        "<img embed='assets/kya_hr/images/kya_logo.png' alt='KYA-Energy Group'"
        " width='60' height='60' border='0'"
        " style='display:block;margin:0 auto 10px;background:#fff;padding:6px;border-radius:4px;'>"
        "<h2 style='color:white;margin:0;'>{emoji} {title}</h2>"
        "</div>"
        "<div style='background:#fff;padding:24px;border:1px solid #e0e0e0;"
        "border-radius:0 0 12px 12px;'>"
    ).format(bg=bg, emoji=emoji, title=title)


def _email_close():
    from kya_hr.utils import get_kya_email_footer
    return "</div>{}</div>".format(get_kya_email_footer())


def send_kya_birthday_reminders():
    """Rappel quotidien : anniversaires de naissance des employes permanents."""
    today_date = getdate(today())

    employees = frappe.db.sql(
        """
        SELECT name, employee_name, date_of_birth, department, designation
        FROM `tabEmployee`
        WHERE status = 'Active'
          AND (employment_type IS NULL
               OR employment_type NOT IN %(excluded)s)
          AND DAY(date_of_birth)   = %(day)s
          AND MONTH(date_of_birth) = %(month)s
        """,
        {"excluded": EXCLUDED_TYPES, "day": today_date.day, "month": today_date.month},
        as_dict=True,
    )
    if not employees:
        return

    recipients = _get_reminder_recipients()
    if not recipients:
        return

    for emp in employees:
        # NB : on ne précise PAS l'âge de la personne (règle KYA).
        subject = "Anniversaire — {}".format(emp.employee_name)
        body = (
            _email_header("#ff8f00", "\U0001f382", "Joyeux Anniversaire !")
            + "<p>Chers coll&egrave;gues,</p>"
            + "<p>Aujourd&rsquo;hui, <b>{name}</b>"
            " ({desig} &mdash; {dept})"
            " f&ecirc;te son anniversaire !</p>".format(
                name=frappe.utils.escape_html(emp.employee_name),
                desig=frappe.utils.escape_html(emp.designation or ""),
                dept=frappe.utils.escape_html(emp.department or ""),
            )
            + "<p>Toute l&rsquo;&eacute;quipe KYA-Energy Group lui souhaite un "
            "<b>tr&egrave;s joyeux anniversaire</b> \U0001f389</p>"
            + _email_close()
        )
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=body,
            now=False,
        )


def send_kya_anniversary_reminders():
    """Rappel quotidien : anniversaires d'anciennete (date d'embauche)."""
    today_date = getdate(today())

    employees = frappe.db.sql(
        """
        SELECT name, employee_name, date_of_joining, department, designation
        FROM `tabEmployee`
        WHERE status = 'Active'
          AND (employment_type IS NULL
               OR employment_type NOT IN %(excluded)s)
          AND DAY(date_of_joining)   = %(day)s
          AND MONTH(date_of_joining) = %(month)s
          AND YEAR(date_of_joining)  < %(year)s
        """,
        {
            "excluded": EXCLUDED_TYPES,
            "day": today_date.day,
            "month": today_date.month,
            "year": today_date.year,
        },
        as_dict=True,
    )
    if not employees:
        return

    recipients = _get_reminder_recipients()
    if not recipients:
        return

    for emp in employees:
        years = today_date.year - emp.date_of_joining.year
        plural = "s" if years > 1 else ""
        subject = "\U0001f3c6 Anniversaire de service — {} ({} an{})".format(
            emp.employee_name, years, plural
        )
        body = (
            _email_header("#1565c0", "\U0001f3c6", "Anniversaire de Service")
            + "<p>Chers coll&egrave;gues,</p>"
            + "<p>Aujourd&rsquo;hui, <b>{name}</b>"
            " ({desig} &mdash; {dept})"
            " c&eacute;l&egrave;bre <b>{years} an{plural}</b>"
            " au sein de KYA-Energy Group !</p>".format(
                name=frappe.utils.escape_html(emp.employee_name),
                desig=frappe.utils.escape_html(emp.designation or ""),
                dept=frappe.utils.escape_html(emp.department or ""),
                years=years,
                plural=plural,
            )
            + "<p>Merci pour votre d&eacute;vouement et votre engagement \U0001f64f</p>"
            + _email_close()
        )
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=body,
            now=False,
        )


def _get_reminder_recipients():
    """Emails des utilisateurs actifs dans les roles de rappel (RH + Direction)."""
    users = set()
    for role in REMINDER_ROLES:
        for user in frappe.get_all(
            "Has Role",
            filters={"role": role, "parenttype": "User"},
            pluck="parent",
        ):
            users.add(user)

    result = []
    for user in users:
        if not frappe.db.get_value("User", user, "enabled"):
            continue
        email = frappe.db.get_value("User", user, "email")
        if email and email not in ("Administrator", "Guest"):
            result.append(email)
    return result

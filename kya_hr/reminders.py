"""
KYA HR — Rappels automatiques (anniversaires de naissance et d'ancienneté).

Envoi quotidien. Les stagiaires sont exclus. On NE précise PAS l'âge.
- Anniversaire de NAISSANCE : envoyé à TOUT le personnel via la liste de
  diffusion `personnel@kya-energy.com` (plus de restriction RH/DG).
- Anniversaire d'ANCIENNETÉ (service) : envoyé à la RH + Direction.
"""

import frappe
from frappe.utils import today, getdate

# Boîte de diffusion de TOUT le personnel KYA : cette adresse groupe redistribue
# le message à l'ensemble des salariés. Les rappels d'anniversaire (naissance)
# y sont envoyés → toute l'entreprise reçoit, sans filtrer par rôle.
STAFF_MAILING_LIST = "personnel@kya-energy.com"

# Roles qui recoivent les rappels d'ancienneté : la RH et le DG uniquement (pas
# System Manager, pour ne pas arroser les comptes techniques/admin).
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

    # Rappel de NAISSANCE : envoyé à TOUT le personnel via la liste de diffusion.
    recipients = [STAFF_MAILING_LIST]

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


def rappel_completude_rh():
    """Rappel HEBDOMADAIRE (lundi) à la RH : fiches Salarié actives incomplètes.

    But : encourager la RH à tenir la plateforme à jour (matricule, dates, poste…).
    N'envoie RIEN si toutes les fiches sont complètes (pas de spam inutile)."""
    try:
        from kya_hr.api.rh_effectifs import _data_quality_rows, _CHAMPS_ESSENTIELS  # noqa
    except Exception:
        return
    data = _data_quality_rows()
    if not data.get("nb_incompletes"):
        return  # rien à signaler : on félicite en silence

    recipients = _get_reminder_recipients()
    if not recipients:
        return

    site = frappe.utils.get_url()
    n = data["nb_incompletes"]
    actifs = data["actifs"]

    # Répartition des champs les plus souvent manquants.
    champs_html = "".join(
        "<tr><td style='padding:4px 10px;border-bottom:1px solid #eee;'>{c}</td>"
        "<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right;"
        "font-weight:700;color:#9a3412;'>{n}</td></tr>".format(c=frappe.utils.escape_html(x["champ"]), n=x["n"])
        for x in data.get("par_champ", [])
    )

    # Aperçu des 12 fiches les plus incomplètes (lien direct vers la fiche).
    apercu_html = "".join(
        "<tr><td style='padding:4px 10px;border-bottom:1px solid #eee;'>"
        "<a href='{site}/app/salarie-kya/{name}' style='color:#0f766e;text-decoration:none;'>{mat} — {nom}</a></td>"
        "<td style='padding:4px 10px;border-bottom:1px solid #eee;color:#64748b;font-size:12px;'>{man}</td></tr>".format(
            site=site, name=frappe.utils.quote(x["name"]),
            mat=frappe.utils.escape_html(x["matricule"]),
            nom=frappe.utils.escape_html(x["nom_complet"]),
            man=frappe.utils.escape_html(", ".join(x["manquants"])))
        for x in data["incompletes"][:12]
    )
    reste = n - min(12, n)

    body = (
        _email_header("#0f766e", "\U0001f4cb", "Fiches employés à compléter")
        + "<p>Bonjour,</p>"
        + "<p><b>{n}</b> fiche(s) salarié active(s) sur {actifs} ont des informations "
          "essentielles manquantes. Merci de les compléter sur la plateforme pour "
          "fiabiliser les tableaux de bord (effectifs, retraite, masse salariale).</p>".format(n=n, actifs=actifs)
        + ("<h4 style='margin:16px 0 6px;color:#0f766e;'>Champs les plus souvent manquants</h4>"
           "<table style='border-collapse:collapse;width:100%;font-size:13px;'>" + champs_html + "</table>"
           if champs_html else "")
        + "<h4 style='margin:16px 0 6px;color:#0f766e;'>Fiches à compléter en priorité</h4>"
        + "<table style='border-collapse:collapse;width:100%;font-size:13px;'>" + apercu_html + "</table>"
        + ("<p style='color:#64748b;font-size:12px;'>… et {reste} autre(s) fiche(s).</p>".format(reste=reste)
           if reste > 0 else "")
        + "<p style='margin-top:18px;'><a href='{site}/rh-effectifs' "
          "style='background:#0f766e;color:#fff;padding:10px 18px;border-radius:8px;"
          "text-decoration:none;font-weight:700;'>Ouvrir le tableau de bord RH</a></p>".format(site=site)
        + "<p style='color:#64748b;font-size:12px;'>Une plateforme à jour, c'est des "
          "décisions RH plus justes. Merci pour votre rigueur \U0001f64f</p>"
        + _email_close()
    )
    frappe.sendmail(
        recipients=recipients,
        subject="RH — {n} fiche(s) employé à compléter".format(n=n),
        message=body,
        now=False,
    )

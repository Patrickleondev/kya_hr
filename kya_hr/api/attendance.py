"""API Attendance KYA — marquage par la RH depuis le dashboard.

Contexte metier : actuellement les employes emargent dans un cahier
le matin (nom, prenom, heure d'arrivee, signature). La RH recopie
manuellement dans un fichier Excel. Cette API centralise le marquage.

La RH choisit une equipe sur le dashboard /kya-rh-dashboard, voit les
membres, et marque chaque arrivee + sortie. Le systeme :
- Cree un Employee Checkin (log_type=IN ou OUT) compatible badging futur
- Cree/met a jour l'Attendance du jour (status auto selon checkin/timeout)
- Calcule le retard si arrivee > heure standard equipe (defaut 08:05)
- Calcule les heures travaillees (sortie - arrivee, pause dejeuner exclue)
- Logge marked_by + marked_at pour audit
- Pousse un realtime publish pour rafraichir le dashboard

Endpoints whitelistes (autorisés aux roles RH) :
- mark_arrival(employee, arrival_time)        : creer pointage entree
- mark_departure(employee, departure_time)    : creer pointage sortie
- mark_absent(employee, motif)                : marquer absent
- mark_team_bulk(team, status)                : marquer toute une equipe
- get_team_attendance(team, date)             : lire l'etat d'une equipe
- recalc_working_hours(attendance_name)       : recalcul manuel heures

Securite : check_role() refuse si role pas dans RH_ROLES.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, today

# Heure standard d'arrivee : tolerance de 5 minutes avant retard.
# Pourra etre overridee via Shift Type custom par equipe.
DEFAULT_SHIFT_START = time(8, 0)        # 08:00
DEFAULT_SHIFT_END = time(17, 30)        # 17:30 — sortie standard KYA
DEFAULT_LATENESS_TOLERANCE_MIN = 5      # 5 minutes de tolerance
DEFAULT_LUNCH_BREAK_MINUTES = 60        # pause dej deductible

RH_ROLES = {
    "Responsable RH",
    "HR Manager",
    "HR User",
    "Maitre de Stage",
    "Maître de Stage",
    "Responsable des Stagiaires",
    "System Manager",
}


def _check_rh_role():
    """Refuse l'access si l'utilisateur n'a pas un role RH."""
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not (RH_ROLES & user_roles):
        frappe.throw(
            _("Acces reserve aux roles RH (Responsable RH, HR Manager, HR User, etc.)"),
            frappe.PermissionError,
        )


def _get_shift_start_for_employee(employee_name: str) -> time:
    """Retourne l'heure de debut du Shift Type de l'employe, sinon DEFAULT."""
    try:
        shift = frappe.db.get_value(
            "Employee", employee_name, "default_shift"
        )
        if shift:
            start_str = frappe.db.get_value("Shift Type", shift, "start_time")
            if start_str:
                # start_time est un timedelta dans Frappe
                if isinstance(start_str, timedelta):
                    total_sec = int(start_str.total_seconds())
                    h, rem = divmod(total_sec, 3600)
                    m, _s = divmod(rem, 60)
                    return time(h, m)
    except Exception:
        pass
    return DEFAULT_SHIFT_START


def _compute_lateness(arrival_dt: datetime, shift_start: time) -> int:
    """Retourne le nombre de minutes de retard (0 si dans la tolerance)."""
    shift_dt = arrival_dt.replace(
        hour=shift_start.hour, minute=shift_start.minute, second=0, microsecond=0
    )
    diff = (arrival_dt - shift_dt).total_seconds() / 60
    if diff <= DEFAULT_LATENESS_TOLERANCE_MIN:
        return 0
    return int(diff)


def _compute_working_hours(in_dt: datetime, out_dt: datetime) -> float:
    """Calcule les heures travaillees (sortie - arrivee), pause dej deduite si >5h."""
    total_minutes = (out_dt - in_dt).total_seconds() / 60
    if total_minutes <= 0:
        return 0.0
    # Si > 5h, on deduit la pause dej (typique 12h-13h)
    if total_minutes > 5 * 60:
        total_minutes -= DEFAULT_LUNCH_BREAK_MINUTES
    return round(total_minutes / 60, 2)


def _create_checkin(employee: str, log_type: str, ts: datetime, marked_by: str) -> str:
    """Cree un Employee Checkin (idempotent).

    Re-valider une présence rejouait l'insertion -> HRMS levait « Cet employé a
    déjà un journal avec le même horodatage » et tout le marquage échouait (donc
    les heures ne se calculaient jamais). On réutilise donc un pointage existant
    au lieu d'en recréer un.
    """
    existing = frappe.db.get_value(
        "Employee Checkin",
        {"employee": employee, "log_type": log_type, "time": ts},
        "name",
    )
    if existing:
        return existing
    doc = frappe.new_doc("Employee Checkin")
    doc.employee = employee
    doc.log_type = log_type  # "IN" ou "OUT"
    doc.time = ts
    doc.device_id = f"manual:{marked_by}"
    try:
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        # doublon d'horodatage (course / re-validation) : réutiliser l'existant
        existing = frappe.db.get_value(
            "Employee Checkin", {"employee": employee, "time": ts}, "name"
        )
        if existing:
            return existing
        raise


def _get_or_create_attendance(employee: str, att_date: str) -> Any:
    """Recupere ou cree l'Attendance du jour pour cet employe."""
    existing = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": att_date, "docstatus": ["!=", 2]},
        "name",
    )
    if existing:
        return frappe.get_doc("Attendance", existing)
    doc = frappe.new_doc("Attendance")
    doc.employee = employee
    doc.attendance_date = att_date
    doc.status = "Present"  # par defaut, peut etre override
    doc.company = frappe.db.get_value("Employee", employee, "company") \
        or frappe.defaults.get_global_default("company")
    return doc


def _is_on_approved_leave(employee: str, att_date: str) -> bool:
    """True si l'employe a un Planning Conge Equipe approuve couvrant cette date."""
    # Phase B : on lira Planning Conge Equipe quand il sera cree (D5).
    # En attendant, fallback sur Leave Application (ERPNext natif).
    return bool(
        frappe.db.exists(
            "Leave Application",
            {
                "employee": employee,
                "from_date": ["<=", att_date],
                "to_date": [">=", att_date],
                "status": "Approved",
                "docstatus": 1,
            },
        )
    )


# ════════════════════════════════════════════════════════════════════
#  ENDPOINTS WHITELISTES
# ════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def mark_arrival(employee: str, arrival_time: str | None = None, date: str | None = None) -> dict:
    """Marque l'arrivee d'un employe.

    - arrival_time : ISO datetime ou HH:MM ou None (= maintenant)
    - date : YYYY-MM-DD ou None (= aujourd'hui)

    Retour : { ok, attendance, checkin, lateness_min, status }
    """
    _check_rh_role()
    if not employee:
        frappe.throw(_("employee est requis"))

    att_date = date or today()
    if _is_on_approved_leave(employee, att_date):
        frappe.throw(
            _("L'employe {0} est en conge approuve le {1}. Modifier le planning d'abord.").format(
                employee, att_date
            )
        )

    # Resoudre arrival_time
    if arrival_time:
        # Format HH:MM ou ISO
        if len(arrival_time) <= 8 and ":" in arrival_time:
            hh, mm = arrival_time.split(":")[:2]
            arrival_dt = datetime.combine(getdate(att_date), time(int(hh), int(mm)))
        else:
            arrival_dt = get_datetime(arrival_time)
    else:
        arrival_dt = now_datetime()

    # Compute lateness
    shift_start = _get_shift_start_for_employee(employee)
    lateness = _compute_lateness(arrival_dt, shift_start)

    # Crear Employee Checkin
    checkin_name = _create_checkin(employee, "IN", arrival_dt, frappe.session.user)

    # Get or create Attendance
    att = _get_or_create_attendance(employee, att_date)
    att.in_time = arrival_dt
    att.status = "Present"
    # Custom fields KYA
    att.kya_presence_type = "Présent"
    att.kya_marked_by = frappe.session.user
    att.kya_marked_at = now_datetime()
    att.kya_lateness_minutes = lateness
    if lateness > 0:
        att.late_entry = 1
    att.save(ignore_permissions=True)
    frappe.db.commit()

    # Push realtime aux dashboards ouverts
    try:
        frappe.publish_realtime(
            event="kya_dashboard_updated",
            message={"doctype": "Attendance", "name": att.name},
            after_commit=True,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "attendance": att.name,
        "checkin": checkin_name,
        "lateness_min": lateness,
        "status": "Present",
        "shift_start": shift_start.strftime("%H:%M"),
        "arrival": arrival_dt.strftime("%H:%M"),
    }


@frappe.whitelist()
def mark_departure(employee: str, departure_time: str | None = None, date: str | None = None) -> dict:
    """Marque la sortie d'un employe et calcule les heures travaillees."""
    _check_rh_role()
    if not employee:
        frappe.throw(_("employee est requis"))

    att_date = date or today()
    att_name = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": att_date, "docstatus": ["!=", 2]},
        "name",
    )
    if not att_name:
        frappe.throw(
            _("Aucune Attendance trouvee pour {0} le {1}. Marquer l'arrivee d'abord.").format(
                employee, att_date
            )
        )

    if departure_time:
        if len(departure_time) <= 8 and ":" in departure_time:
            hh, mm = departure_time.split(":")[:2]
            depart_dt = datetime.combine(getdate(att_date), time(int(hh), int(mm)))
        else:
            depart_dt = get_datetime(departure_time)
    else:
        depart_dt = now_datetime()

    checkin_name = _create_checkin(employee, "OUT", depart_dt, frappe.session.user)

    att = frappe.get_doc("Attendance", att_name)
    att.out_time = depart_dt

    in_dt = get_datetime(att.in_time) if att.in_time else None
    if in_dt:
        att.working_hours = _compute_working_hours(in_dt, depart_dt)
    att.kya_marked_by = frappe.session.user
    att.kya_marked_at = now_datetime()
    att.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        frappe.publish_realtime(
            event="kya_dashboard_updated",
            message={"doctype": "Attendance", "name": att.name},
            after_commit=True,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "attendance": att.name,
        "checkin": checkin_name,
        "departure": depart_dt.strftime("%H:%M"),
        "working_hours": flt(att.working_hours),
    }


@frappe.whitelist()
def mark_absent(employee: str, motif: str = "", date: str | None = None) -> dict:
    """Marque l'employe absent."""
    _check_rh_role()
    if not employee:
        frappe.throw(_("employee est requis"))

    att_date = date or today()
    att = _get_or_create_attendance(employee, att_date)
    att.status = "Absent"
    att.kya_presence_type = "Absent"
    att.kya_marked_by = frappe.session.user
    att.kya_marked_at = now_datetime()
    if motif:
        att.kya_motif_absence = motif
    att.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        frappe.publish_realtime(
            event="kya_dashboard_updated",
            message={"doctype": "Attendance", "name": att.name},
            after_commit=True,
        )
    except Exception:
        pass

    return {"ok": True, "attendance": att.name, "status": "Absent"}


@frappe.whitelist()
def mark_status(employee: str, status: str = "Present", date: str | None = None) -> dict:
    """Marque directement le statut du jour (boutons Présent/Retard/Absent).

    Mapping simple pour le marquage manuel RH depuis l'UI de présence :
    - 'Present' / 'Présent' -> status Present, late_entry 0
    - 'Retard'  / 'Late'    -> status Present, late_entry 1 (présent mais en retard)
    - 'Absent'              -> status Absent

    Réutilise _get_or_create_attendance + trace marked_by/marked_at.
    """
    _check_rh_role()
    if not employee:
        frappe.throw(_("employee est requis"))

    att_date = date or today()
    s = (status or "").strip().lower()
    att = _get_or_create_attendance(employee, att_date)

    if s in ("absent",):
        att.status = "Absent"
        att.late_entry = 0
        att.kya_presence_type = "Absent"
    elif s in ("mission", "en mission"):
        # En mission = l'employé travaille (hors site) -> compté Présent dans HRMS,
        # mais distingué via kya_presence_type pour les stats.
        att.status = "Present"
        att.late_entry = 0
        att.kya_presence_type = "En mission"
    elif s in ("conge", "congé", "leave", "on leave"):
        att.status = "On Leave"
        att.late_entry = 0
        att.kya_presence_type = "Congé"
    elif s in ("retard", "late"):
        att.status = "Present"
        att.late_entry = 1
        att.kya_presence_type = "Présent"
    else:  # present / présent / défaut
        att.status = "Present"
        att.late_entry = 0
        att.kya_presence_type = "Présent"

    att.kya_marked_by = frappe.session.user
    att.kya_marked_at = now_datetime()
    att.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        frappe.publish_realtime(
            event="kya_dashboard_updated",
            message={"doctype": "Attendance", "name": att.name},
            after_commit=True,
        )
    except Exception:
        pass

    return {"ok": True, "attendance": att.name,
            "status": att.status, "late_entry": cint(att.late_entry),
            "presence_type": att.kya_presence_type}


@frappe.whitelist()
def set_default_departure(employee: str, date: str | None = None) -> dict:
    """Applique la sortie standard 17:30 pour un employé qui n'a pas émargé sa sortie.

    Règle métier RH validée : si la personne est partie sans noter son heure
    de départ dans le cahier, la RH la CONTACTE d'abord pour confirmer, PUIS
    clique pour poser 17:30 (sortie standard KYA). On ne fabrique jamais
    l'heure automatiquement : ce endpoint est déclenché manuellement.

    Exige une arrivée déjà saisie (sinon il n'y a pas de journée à clôturer).
    """
    _check_rh_role()
    if not employee:
        frappe.throw(_("employee est requis"))
    att_date = date or today()
    att_name = frappe.db.get_value(
        "Attendance",
        {"employee": employee, "attendance_date": att_date, "docstatus": ["!=", 2]},
        "name",
    )
    if not att_name:
        frappe.throw(
            _("Aucune présence pour {0} le {1}.").format(employee, att_date)
        )
    if not frappe.db.get_value("Attendance", att_name, "in_time"):
        frappe.throw(
            _("Pas d'heure d'arrivée : impossible d'appliquer la sortie par défaut.")
        )
    out = mark_departure(employee, departure_time="17:30", date=att_date)
    out["default_applied"] = True
    return out


def _get_team_members(team: str, fields: list[str] | None = None):
    """Membres d'une équipe : par custom_kya_equipe, avec repli sur department.

    En prod le champ `department` (texte libre) est incohérent ; la source de
    vérité est `custom_kya_equipe` (Link Equipe KYA). On cherche d'abord par
    équipe, et si rien ne ressort on retombe sur le department (compat héritée).
    """
    fld = fields or ["name"]
    members = frappe.get_all(
        "Employee",
        filters={"custom_kya_equipe": team, "status": "Active"},
        fields=fld,
    )
    if not members:
        members = frappe.get_all(
            "Employee",
            filters={"department": team, "status": "Active"},
            fields=fld,
        )
    return members


@frappe.whitelist()
def mark_team_bulk(team: str, status: str = "Present", date: str | None = None) -> dict:
    """Marque toute une equipe en une fois. Exclut auto les employes en conge."""
    _check_rh_role()
    if not team:
        frappe.throw(_("team est requis"))
    if status not in ("Present", "Absent"):
        frappe.throw(_("status doit etre Present ou Absent"))

    att_date = date or today()
    members = [m["name"] for m in _get_team_members(team, ["name"])]

    results = {"marked": [], "skipped_leave": [], "errors": []}
    for emp in members:
        try:
            if _is_on_approved_leave(emp, att_date):
                results["skipped_leave"].append(emp)
                continue
            if status == "Present":
                mark_arrival(emp, date=att_date)
            else:
                mark_absent(emp, date=att_date)
            results["marked"].append(emp)
        except Exception as exc:
            results["errors"].append({"employee": emp, "error": str(exc)})

    return {"ok": True, "team": team, **results}


@frappe.whitelist()
def get_team_attendance(team: str, date: str | None = None) -> dict:
    """Retourne l'etat de presence de tous les membres d'une equipe pour une date."""
    _check_rh_role()
    att_date = date or today()

    members = _get_team_members(
        team, ["name", "employee_name", "custom_matricule_kya", "designation"]
    )

    rows = []
    for m in members:
        on_leave = _is_on_approved_leave(m["name"], att_date)
        att_data = frappe.db.get_value(
            "Attendance",
            {"employee": m["name"], "attendance_date": att_date, "docstatus": ["!=", 2]},
            ["name", "status", "in_time", "out_time", "working_hours",
             "kya_presence_type", "kya_lateness_minutes", "kya_marked_by", "kya_marked_at"],
            as_dict=True,
        )
        rows.append({
            "employee": m["name"],
            "employee_name": m["employee_name"],
            "matricule": m["custom_matricule_kya"],
            "designation": m["designation"],
            "on_leave": on_leave,
            "attendance": att_data or {},
        })
    return {"team": team, "date": att_date, "rows": rows}


def _period_bounds(period: str, ref_date) -> tuple:
    """Retourne (from_date, to_date, libellé) pour semaine|mois|trimestre."""
    from datetime import date as _date
    from frappe.utils import add_days, get_last_day, getdate as _g
    d = _g(ref_date) if ref_date else _g(today())
    if period == "semaine":
        start = add_days(d, -d.weekday())          # lundi
        end = add_days(start, 6)                    # dimanche
        label = f"Semaine du {start.strftime('%d/%m')} au {end.strftime('%d/%m/%Y')}"
    elif period == "trimestre":
        q = (d.month - 1) // 3
        start = _date(d.year, q * 3 + 1, 1)
        end = get_last_day(_date(d.year, q * 3 + 3, 1))
        label = f"T{q + 1} {d.year} ({start.strftime('%d/%m')} – {end.strftime('%d/%m/%Y')})"
    else:  # mois
        period = "mois"
        start = d.replace(day=1)
        end = get_last_day(d)
        _MOIS = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
                 "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        label = f"{_MOIS[start.month]} {start.year}"
    return getdate(start), getdate(end), label


@frappe.whitelist()
def get_attendance_report(period: str = "mois", ref_date: str | None = None,
                          equipe: str | None = None) -> dict:
    """Rapport de présence PAR EMPLOYÉ sur une période (semaine|mois|trimestre).

    Pour chaque employé actif (stagiaires inclus) : jours travaillés, retards,
    absences, heures totales et moyennes. Compte les présences saisies au
    dashboard (docstatus != 2, brouillon inclus). Sert le dashboard RH + export.
    """
    _check_rh_role()
    from_date, to_date, label = _period_bounds(period, ref_date)

    cond_eq = "AND COALESCE(e.custom_kya_equipe,'') = %(eq)s" if equipe else ""
    rows = frappe.db.sql(
        f"""
        SELECT
            e.name, e.employee_name,
            COALESCE(e.custom_kya_equipe,'') AS equipe,
            COALESCE(e.department,'')        AS departement,
            COALESCE(e.employment_type,'')   AS type_emploi,
            SUM(CASE WHEN a.status='Present'  THEN 1 ELSE 0 END) AS jours_presents,
            SUM(CASE WHEN a.status='Half Day' THEN 1 ELSE 0 END) AS jours_demi,
            SUM(CASE WHEN a.late_entry=1       THEN 1 ELSE 0 END) AS jours_retard,
            SUM(CASE WHEN a.status='Absent'   THEN 1 ELSE 0 END) AS jours_absent,
            SUM(CASE WHEN a.kya_presence_type='En mission' THEN 1 ELSE 0 END) AS jours_mission,
            SUM(CASE WHEN a.in_time IS NOT NULL AND a.out_time IS NULL
                     THEN 1 ELSE 0 END)                            AS jours_incomplet,
            COALESCE(SUM(a.working_hours),0)  AS heures_saisies,
            COALESCE(SUM(CASE
                WHEN COALESCE(a.working_hours,0) <= 0
                 AND a.in_time IS NOT NULL AND a.out_time IS NOT NULL
                THEN TIMESTAMPDIFF(MINUTE, a.in_time, a.out_time)/60.0
                ELSE 0 END), 0)              AS heures_fallback
        FROM `tabEmployee` e
        LEFT JOIN `tabAttendance` a
            ON a.employee = e.name
           AND a.attendance_date BETWEEN %(fd)s AND %(td)s
           AND a.docstatus != 2
        WHERE e.status='Active' {cond_eq}
        GROUP BY e.name, e.employee_name, e.custom_kya_equipe, e.department, e.employment_type
        ORDER BY e.custom_kya_equipe, e.employee_name
        """,
        {"fd": from_date, "td": to_date, "eq": equipe}, as_dict=True,
    )

    employes = []
    tot = {"jours": 0, "retards": 0, "absents": 0, "missions": 0,
           "incomplets": 0, "heures": 0.0}
    for r in rows:
        jours = int(r.jours_presents or 0) + int(r.jours_demi or 0)
        heures = round(float(r.heures_saisies or 0) + float(r.heures_fallback or 0), 2)
        mission = int(r.jours_mission or 0)
        incomplet = int(r.jours_incomplet or 0)
        employes.append({
            "employee": r.name, "employee_name": r.employee_name,
            "equipe": r.equipe or "Sans équipe", "departement": r.departement,
            "stagiaire": (r.type_emploi or "").lower() in ("stage", "stagiaire", "internship"),
            "jours_travailles": jours,
            "jours_retard": int(r.jours_retard or 0),
            "jours_absent": int(r.jours_absent or 0),
            "jours_mission": mission,
            "jours_incomplet": incomplet,
            "heures_totales": heures,
            "heures_moyennes": round(heures / jours, 2) if jours else 0.0,
        })
        tot["jours"] += jours
        tot["retards"] += int(r.jours_retard or 0)
        tot["absents"] += int(r.jours_absent or 0)
        tot["missions"] += mission
        tot["incomplets"] += incomplet
        tot["heures"] += heures
    tot["heures"] = round(tot["heures"], 1)

    return {
        "period": period, "label": label,
        "from_date": str(from_date), "to_date": str(to_date),
        "employes": employes, "totaux": tot, "nb_employes": len(employes),
    }


@frappe.whitelist()
def recalc_working_hours(attendance_name: str) -> dict:
    """Recalcule manuellement working_hours pour une Attendance (si in/out modifies)."""
    _check_rh_role()
    att = frappe.get_doc("Attendance", attendance_name)
    if att.in_time and att.out_time:
        att.working_hours = _compute_working_hours(
            get_datetime(att.in_time), get_datetime(att.out_time)
        )
        att.save(ignore_permissions=True)
        frappe.db.commit()
        return {"ok": True, "working_hours": flt(att.working_hours)}
    return {"ok": False, "reason": "in_time ou out_time manquant"}

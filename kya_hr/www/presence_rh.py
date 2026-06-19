"""LOT 5.3 — Page de marquage des présences (RH).

Remplace le cahier papier + recopie Excel : la RH voit la liste des
employés (groupés par équipe/département) et marque en 1 clic
Présent / Retard / Absent. Appelle l'API kya_hr.api.attendance.mark_status.

Rendu serveur (liste + statut du jour), actions via fetch JSON.
"""
import frappe
from frappe import _
from frappe.utils import today, formatdate

no_cache = 1

_VIEW_ROLES = {
    "Responsable RH", "HR Manager", "HR User", "Maître de Stage",
    "Responsable des Stagiaires", "System Manager",
    "Directeur Général", "DGA", "Chef Service",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not _VIEW_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la RH et à la Direction."),
                     frappe.PermissionError)

    att_date = today()
    employes = []
    stats = {"total": 0, "presents": 0, "retards": 0, "absents": 0,
             "non_marques": 0, "heures": 0.0}

    try:
        rows = frappe.db.sql(
            """
            SELECT
                e.name, e.employee_name,
                COALESCE(e.custom_kya_equipe, '') AS equipe,
                COALESCE(e.department, '') AS departement,
                a.status AS att_status, a.late_entry AS att_late,
                a.in_time AS in_time, a.out_time AS out_time,
                a.working_hours AS working_hours
            FROM `tabEmployee` e
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = %(d)s
                AND a.docstatus != 2
            WHERE e.status='Active'
            ORDER BY e.custom_kya_equipe, e.employee_name
            """,
            {"d": att_date}, as_dict=True,
        )
        employes = rows
        stats["total"] = len(rows)
        total_hours = 0.0
        for r in rows:
            # heures d'arrivée / sortie (HH:MM) pour préremplir les champs time
            r.arrivee = str(r.in_time)[11:16] if r.in_time else ""
            r.sortie = str(r.out_time)[11:16] if r.out_time else ""
            wh = float(r.working_hours or 0)
            # Cohérence : si arrivée ET sortie existent mais working_hours non
            # calculé (fiche marquée avant sans sortie, ou importée), calculer
            # à la volée (sortie − arrivée) en heures.
            if wh <= 0 and r.in_time and r.out_time:
                delta = (r.out_time - r.in_time).total_seconds() / 3600.0
                if delta > 0:
                    wh = round(delta, 2)
            r.heures = round(wh, 2)
            total_hours += wh
            if r.att_status == "Absent":
                stats["absents"] += 1
                r.etat = "Absent"
            elif r.att_status == "Present" and r.att_late:
                stats["retards"] += 1
                r.etat = "Retard"
            elif r.att_status == "Present":
                stats["presents"] += 1
                r.etat = "Présent"
            else:
                stats["non_marques"] += 1
                r.etat = ""
        stats["heures"] = round(total_hours, 1)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "presence-rh: chargement")

    context.employes = employes
    context.stats = stats
    context.att_date = att_date
    context.att_date_label = formatdate(att_date)
    context.no_breadcrumbs = True

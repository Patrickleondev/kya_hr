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
    stats = {"total": 0, "presents": 0, "retards": 0, "absents": 0, "non_marques": 0}

    try:
        rows = frappe.db.sql(
            """
            SELECT
                e.name, e.employee_name,
                COALESCE(e.custom_kya_equipe, '') AS equipe,
                COALESCE(e.department, '') AS departement,
                a.status AS att_status, a.late_entry AS att_late
            FROM `tabEmployee` e
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = %(d)s
            WHERE e.status='Active'
            ORDER BY e.custom_kya_equipe, e.employee_name
            """,
            {"d": att_date}, as_dict=True,
        )
        employes = rows
        stats["total"] = len(rows)
        for r in rows:
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
    except Exception:
        frappe.log_error(frappe.get_traceback(), "presence-rh: chargement")

    context.employes = employes
    context.stats = stats
    context.att_date = att_date
    context.att_date_label = formatdate(att_date)
    context.no_breadcrumbs = True

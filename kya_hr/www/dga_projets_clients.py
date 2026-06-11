"""LOT 5.2 — Tableau de bord DGA : Projets & Clients.

Vue destinée au DGA : portefeuille de projets (installations solaires,
centrales, etc.), clients associés, et matériel sorti par projet
(via PV Sortie Matériel qui porte les champs project / client).

Lecture seule, rendu serveur (fluide). Accès : DGA / DG / System Manager
+ Chef Service (pilotage opérationnel).
"""
import frappe
from frappe import _
from frappe.utils import flt, formatdate

no_cache = 1

_ALLOWED_ROLES = {
    "DGA", "Directeur Général", "DG", "System Manager",
    "Chef Service", "Projects Manager", "Projects User",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la Direction (DGA)."), frappe.PermissionError)

    stats = {"projets": 0, "clients": 0, "ouverts": 0, "pv_lies": 0}
    projets = []
    clients = []

    # Matériel sorti agrégé par projet (PV Sortie Matériel porte 'project')
    pv_par_projet = {}
    try:
        rows = frappe.db.sql(
            """
            SELECT COALESCE(project, projet) AS proj, COUNT(*) AS nb
            FROM `tabPV Sortie Materiel`
            WHERE (project IS NOT NULL AND project != '')
               OR (projet IS NOT NULL AND projet != '')
            GROUP BY proj
            """,
            as_dict=True,
        )
        for r in rows:
            if r.proj:
                pv_par_projet[r.proj] = r.nb
        stats["pv_lies"] = sum(pv_par_projet.values())
    except Exception:
        frappe.log_error(frappe.get_traceback(), "dga-projets-clients: pv")

    # Projets
    try:
        projets = frappe.get_all(
            "Project",
            fields=["name", "project_name", "status", "percent_complete",
                    "customer", "expected_start_date", "expected_end_date",
                    "estimated_costing"],
            order_by="modified desc",
            limit_page_length=50,
        )
        stats["projets"] = len(projets)
        stats["ouverts"] = sum(1 for p in projets if (p.status or "") == "Open")
        for p in projets:
            p.nb_pv = pv_par_projet.get(p.name, 0)
            p.debut = formatdate(p.expected_start_date) if p.expected_start_date else "—"
            p.fin = formatdate(p.expected_end_date) if p.expected_end_date else "—"
            p.avancement = int(flt(p.percent_complete))
            # Nom client lisible
            p.client_nom = (frappe.db.get_value("Customer", p.customer, "customer_name")
                            if p.customer else "")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "dga-projets-clients: projets")

    # Clients (avec nb de projets)
    try:
        clients = frappe.get_all(
            "Customer",
            fields=["name", "customer_name", "customer_group", "territory"],
            order_by="modified desc",
            limit_page_length=50,
        )
        stats["clients"] = len(clients)
        for c in clients:
            c.nb_projets = frappe.db.count("Project", {"customer": c.name})
    except Exception:
        frappe.log_error(frappe.get_traceback(), "dga-projets-clients: clients")

    context.stats = stats
    context.projets = projets
    context.clients = clients
    context.no_breadcrumbs = True

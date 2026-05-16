import frappe
from frappe import _
from frappe.utils import flt, formatdate, today, add_days

no_cache = 1

_ALLOWED_ROLES = {
    "Directeur Général", "DGA", "DAAF", "DFC",
    "Auditeur Interne", "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la Direction Générale."), frappe.PermissionError)

    stats = {
        "demandes_dg": 0,
        "brouillards_semaine": 0,
        "effectif_actif": 0,
        "plannings_attente": 0,
        "permissions_attente": 0,
        "montant_demandes_dg": 0,
    }
    demandes_dg = []
    brouillards = []
    plannings_attente = []

    week_ago = add_days(today(), -7)

    try:
        # Demandes Achat en attente DG (palier 3, ≥ 2M XOF)
        demandes_dg = frappe.get_all(
            "Demande Achat KYA",
            filters=[["workflow_state", "in", ("En attente DG", "En attente Direction")]],
            fields=["name", "objet", "montant_total", "demandeur_nom", "modified", "workflow_state"],
            order_by="modified desc",
            limit_page_length=15,
        )
        stats["demandes_dg"] = len(demandes_dg)
        stats["montant_demandes_dg"] = sum(flt(d.montant_total) for d in demandes_dg)
        for d in demandes_dg:
            d.date_label = formatdate(d.modified) if d.modified else ""
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: demandes DG")

    try:
        # Brouillards caisse de la semaine
        brouillards = frappe.get_all(
            "Brouillard Caisse",
            filters=[["creation", ">=", week_ago]],
            fields=["name", "date_brouillard", "caissiere", "total_entrees",
                    "total_sorties", "solde_final", "workflow_state"],
            order_by="date_brouillard desc",
            limit_page_length=15,
        )
        stats["brouillards_semaine"] = len(brouillards)
        for b in brouillards:
            b.date_label = formatdate(b.date_brouillard) if b.date_brouillard else ""
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: brouillards")

    try:
        # Effectif actif
        stats["effectif_actif"] = frappe.db.count("Employee", {"status": "Active"})
    except Exception:
        pass

    try:
        # Plannings congé en attente Direction
        plannings_attente = frappe.get_all(
            "Planning Conge",
            filters=[["workflow_state", "in", ("En attente Direction", "En attente DG")]],
            fields=["name", "employee_name", "date_debut", "date_fin", "nb_jours",
                    "workflow_state", "modified"],
            order_by="modified desc",
            limit_page_length=10,
        )
        stats["plannings_attente"] = len(plannings_attente)
        for p in plannings_attente:
            p.date_label = formatdate(p.date_debut) if p.date_debut else ""
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: plannings")

    try:
        # Permissions de sortie en attente DG (rare mais possible si palier élevé)
        stats["permissions_attente"] = frappe.db.count(
            "Permission Sortie Employe",
            {"workflow_state": ["in", ("En attente DG", "En attente Direction")]},
        )
    except Exception:
        pass

    context.stats = stats
    context.demandes_dg = demandes_dg
    context.brouillards = brouillards
    context.plannings_attente = plannings_attente
    context.no_breadcrumbs = True

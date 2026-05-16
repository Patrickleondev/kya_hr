import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate, add_months, today

no_cache = 1

_ALLOWED_ROLES = {
    "Chef Service", "DAAF", "DFC", "Auditeur Interne",
    "Directeur Général", "DGA", "Responsable RH",
    "Comptable", "Accounts Manager", "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la chaîne achats."), frappe.PermissionError)

    stats = {
        "demandes_en_cours": 0,
        "bons_commande_mois": 0,
        "montant_en_cours": 0,
        "appels_offre_actifs": 0,
    }
    par_palier = {"Palier 1 (Chef)": 0, "Palier 2 (DAAF)": 0, "Palier 3 (DG)": 0}
    derniers_bons = []
    demandes_attente = []
    appels = []

    end_states = ("Approuvé", "Approuve", "Rejeté", "Rejete", "Annulé", "Annule")

    try:
        # Demandes en cours (workflow non final)
        demandes = frappe.get_all(
            "Demande Achat KYA",
            filters=[["workflow_state", "not in", end_states]],
            fields=["name", "objet", "montant_total", "workflow_state", "modified",
                    "demandeur_nom", "date_demande"],
            order_by="modified desc",
            limit_page_length=15,
        )
        stats["demandes_en_cours"] = len(demandes)
        stats["montant_en_cours"] = sum(flt(d.montant_total) for d in demandes)
        for d in demandes:
            d.date_label = formatdate(d.date_demande) if d.date_demande else ""
            m = flt(d.montant_total)
            if m >= 2_000_000:
                par_palier["Palier 3 (DG)"] += 1
            elif m >= 100_000:
                par_palier["Palier 2 (DAAF)"] += 1
            else:
                par_palier["Palier 1 (Chef)"] += 1
        demandes_attente = demandes
    except Exception:
        frappe.log_error(frappe.get_traceback(), "achats-dashboard: demandes")

    try:
        # Bons de commande du mois en cours
        cutoff = add_months(today(), -1)
        bons = frappe.get_all(
            "Bon Commande KYA",
            filters=[["creation", ">=", cutoff]],
            fields=["name", "objet", "montant_total", "supplier", "workflow_state",
                    "creation", "modified"],
            order_by="creation desc",
            limit_page_length=10,
        )
        stats["bons_commande_mois"] = len(bons)
        for b in bons:
            b.date_label = formatdate(b.creation) if b.creation else ""
        derniers_bons = bons
    except Exception:
        frappe.log_error(frappe.get_traceback(), "achats-dashboard: bons")

    try:
        # Appels d'offres actifs (non clôturés)
        appels = frappe.get_all(
            "Appel Offre",
            filters=[["workflow_state", "not in", end_states + ("Attribué", "Attribue")]],
            fields=["name", "objet", "workflow_state", "date_publication", "modified"],
            order_by="modified desc",
            limit_page_length=10,
        )
        stats["appels_offre_actifs"] = len(appels)
        for a in appels:
            a.date_label = formatdate(a.date_publication) if a.date_publication else ""
    except Exception:
        # Le DocType Appel Offre peut être absent sur certains sites
        pass

    context.stats = stats
    context.par_palier = par_palier
    context.demandes = demandes_attente
    context.bons = derniers_bons
    context.appels = appels
    context.no_breadcrumbs = True

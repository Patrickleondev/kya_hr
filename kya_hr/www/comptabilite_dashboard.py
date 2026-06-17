import frappe
from frappe import _
from frappe.utils import flt, formatdate

no_cache = 1

_ALLOWED_ROLES = {
    "Caissier", "Comptable", "DFC", "DAAF", "Accounts Manager", "Accounts User",
    "Auditeur Interne", "Directeur Général", "DG", "DGA", "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la comptabilité."), frappe.PermissionError)

    imports = []
    stats = {"imports": 0, "lignes": 0, "debit": 0, "credit": 0, "salaires": 0, "factures": 0}
    type_counts = {}

    try:
        imports = frappe.get_all(
            "KYA Compta Import",
            fields=[
                "name", "type_document", "periode", "statut_import", "total_lignes",
                "total_debit", "total_credit", "total_salaire_net", "total_facture",
                "imported_by", "date_import", "source_file", "modified",
            ],
            order_by="modified desc",
            limit_page_length=20,
        )

        stats = {
            "imports": len(imports),
            "lignes": sum(flt(row.total_lignes) for row in imports),
            "debit": sum(flt(row.total_debit) for row in imports),
            "credit": sum(flt(row.total_credit) for row in imports),
            "salaires": sum(flt(row.total_salaire_net) for row in imports),
            "factures": sum(flt(row.total_facture) for row in imports),
        }

        for row in imports:
            type_counts[row.type_document] = type_counts.get(row.type_document, 0) + 1
            row.date_import_label = formatdate(row.date_import) if row.date_import else ""

    except Exception:
        frappe.log_error(frappe.get_traceback(), "comptabilite-dashboard: erreur chargement")

    # --- Brouillards de Caisse (vrais flux quotidiens de trésorerie) ---
    brouillards = []
    caisse = {"nb": 0, "en_attente": 0, "solde_actuel": 0,
              "total_entrees": 0, "total_sorties": 0}
    try:
        brouillards = frappe.get_all(
            "Brouillard Caisse",
            fields=[
                "name", "date_brouillard", "caissiere_name", "total_entrees",
                "total_sorties", "solde_final", "total_reel_caisse",
                "workflow_state", "statut", "modified",
            ],
            order_by="date_brouillard desc, modified desc",
            limit_page_length=15,
        )
        caisse["nb"] = frappe.db.count("Brouillard Caisse")
        caisse["en_attente"] = sum(
            1 for b in brouillards if "En attente" in (b.workflow_state or ""))
        caisse["total_entrees"] = sum(flt(b.total_entrees) for b in brouillards)
        caisse["total_sorties"] = sum(flt(b.total_sorties) for b in brouillards)
        if brouillards:
            # Solde le plus récent (1re ligne car tri date desc)
            caisse["solde_actuel"] = flt(brouillards[0].solde_final)
        for b in brouillards:
            b.date_label = formatdate(b.date_brouillard) if b.date_brouillard else ""
            b.etat_label = b.workflow_state or b.statut or ""
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "comptabilite-dashboard: erreur brouillards")

    # --- Etats Récap Chèques (suivi hebdomadaire des chèques) ---
    recaps = []
    cheques = {"nb": 0, "en_attente": 0, "total_montant": 0, "nombre": 0}
    try:
        recaps = frappe.get_all(
            "Etat Recap Cheques",
            fields=[
                "name", "date_etat", "redacteur_name", "libelle_periode",
                "total_montant", "nombre_cheques", "workflow_state",
                "statut", "modified",
            ],
            order_by="date_etat desc, modified desc",
            limit_page_length=15,
        )
        cheques["nb"] = frappe.db.count("Etat Recap Cheques")
        cheques["en_attente"] = sum(
            1 for r in recaps if "En attente" in (r.workflow_state or ""))
        cheques["total_montant"] = sum(flt(r.total_montant) for r in recaps)
        cheques["nombre"] = sum(int(r.nombre_cheques or 0) for r in recaps)
        for r in recaps:
            r.date_label = formatdate(r.date_etat) if r.date_etat else ""
            r.etat_label = r.workflow_state or r.statut or ""
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "comptabilite-dashboard: erreur recap cheques")

    context.imports = imports
    context.stats = stats
    context.type_counts = type_counts
    context.brouillards = brouillards
    context.caisse = caisse
    context.recaps = recaps
    context.cheques = cheques
    context.no_breadcrumbs = True

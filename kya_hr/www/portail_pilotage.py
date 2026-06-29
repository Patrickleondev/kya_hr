"""Page : Portail de pilotage (Accueil des tableaux de bord).

Route : /portail-pilotage

Hub listant les tableaux de bord KYA. Chaque carte n'apparaît que si
l'utilisateur a un rôle d'accès au module correspondant ; deux indicateurs
réels y sont affichés.
"""
from __future__ import annotations

import frappe


# Rôles transverses qui voient tout le portail
_DIR = {"System Manager", "Directeur General", "Directeur Général", "DG", "DGA",
        "Responsable RH", "HR Manager", "Auditeur Interne", "Auditeur"}

_HUB_ROLES = {
    "direction": _DIR,
    "rh": _DIR | {"HR User", "Responsable RH"},
    "achats": _DIR | {"Responsable Achats", "Purchase Manager", "Purchase User",
                      "Chef Service", "DAAF", "DFC", "Comptable"},
    "stocks": _DIR | {"Chargé des Stocks", "Responsable Stock", "Magasinier",
                      "Stock User", "Stock Manager", "Chef Service Achats"},
    "logistique": _DIR | {"Responsable Logistique", "Logisticien",
                          "Gestionnaire de Flotte", "Fleet Manager", "Chef Service"},
    "compta": _DIR | {"Caissier", "Comptable", "DFC", "DAAF",
                      "Accounts Manager", "Accounts User"},
    "technique": _DIR | {"Responsable Technique", "Chef de Projet", "Chef Service",
                         "Chef Equipe", "Chef d'Equipe", "Responsable Equipe"},
    "commercial": _DIR | {"Responsable Commercial", "Commercial", "Chargé Commercial",
                          "Sales Manager", "Sales User", "CRM Manager", "CRM User"},
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portail-pilotage"
        raise frappe.Redirect

    context.page_title = "Portail de pilotage KYA"
    context.no_cache = 1
    context.no_breadcrumbs = True
    try:
        import json as _json
        context.hubs_json = _json.dumps(get_hubs(), default=str)
    except Exception:
        context.hubs_json = "[]"
        frappe.log_error(frappe.get_traceback(), "portail-pilotage: hubs")
    return context


def _count(dt, filters=None):
    try:
        if not frappe.db.exists("DocType", dt):
            return 0
        return frappe.db.count(dt, filters or {})
    except Exception:
        return 0


@frappe.whitelist()
def get_hubs() -> list:
    """Cartes du portail, filtrées par rôle, avec 2 indicateurs réels chacune."""
    roles = set(frappe.get_roles(frappe.session.user))

    nb_emp = _count("Employee", {"status": "Active"})
    nb_equipes = _count("Equipe KYA", {"est_active": 1})

    # Achats
    da_attente = _count("Demande Achat KYA", {"workflow_state": ["not in",
                        ("Approuvé", "Approuve", "Rejeté", "Rejete", "Annulé", "Annule")]})
    bc = _count("Bon Commande KYA")

    # Stocks
    nb_refs = rupt = 0
    try:
        r = frappe.db.sql("SELECT COUNT(DISTINCT item_code) n FROM `tabBin` WHERE actual_qty != 0", as_dict=True)
        nb_refs = int(r[0].n or 0) if r else 0
        rr = frappe.db.sql("""SELECT COUNT(*) n FROM (SELECT item_code, SUM(actual_qty) q
                              FROM `tabBin` GROUP BY item_code HAVING q <= 0) t""", as_dict=True)
        rupt = int(rr[0].n or 0) if rr else 0
    except Exception:
        pass

    # Logistique
    total_v = _count("Vehicle")
    dispo_v = _count("Vehicle", {"kya_statut": "Disponible"})
    mission_v = _count("Vehicle", {"kya_statut": "En mission"})

    # Compta
    nb_brouillard = _count("Brouillard Caisse")
    nb_cheques = _count("Etat Recap Cheques")

    # Technique
    taches_cours = _count("Tache Equipe", {"statut": "En cours"})

    # Commercial
    leads_actifs = _count("Lead", {"status": ["not in", ("Converted", "Do Not Contact", "Lost Quotation")]})

    catalog = [
        {"key": "direction", "title": "Direction Générale", "route": "/direction-dashboard",
         "icon": "building", "color": "#0d7377", "bg": "rgba(13,115,119,.10)",
         "desc": "Vue consolidée des 4 départements, workflows et achats à valider.",
         "stat1": f"{nb_emp} employés", "stat2": "4 départements"},
        {"key": "rh", "title": "Ressources Humaines", "route": "/rapport-presence",
         "icon": "users", "color": "#0d7377", "bg": "rgba(13,115,119,.10)",
         "desc": "Effectif, présence, heures travaillées, congés et statistiques d'équipe.",
         "stat1": f"{nb_emp} actifs", "stat2": f"{nb_equipes} équipes"},
        {"key": "achats", "title": "Achats & Approvisionnement", "route": "/achats-dashboard",
         "icon": "cart", "color": "#d9700f", "bg": "rgba(245,130,32,.13)",
         "desc": "Workflow d'approbation, bons de commande, appels d'offres et marchés.",
         "stat1": f"{da_attente} en attente", "stat2": f"{bc} bons de commande"},
        {"key": "stocks", "title": "Stock & Inventaire", "route": "/kya-stocks-dashboard",
         "icon": "box", "color": "#5f9e2b", "bg": "rgba(141,198,63,.18)",
         "desc": "Mouvements entrée / sortie / retour, valorisation et top articles.",
         "stat1": f"{nb_refs} références", "stat2": f"{rupt} ruptures"},
        {"key": "logistique", "title": "Logistique & Flotte", "route": "/kya-logistique-dashboard",
         "icon": "truck", "color": "#0d7377", "bg": "rgba(13,115,119,.10)",
         "desc": "Sorties véhicule, consommation carburant et entretiens planifiés.",
         "stat1": f"{dispo_v}/{total_v} disponibles", "stat2": f"{mission_v} en mission"},
        {"key": "compta", "title": "Comptabilité & Finance", "route": "/comptabilite-dashboard",
         "icon": "coins", "color": "#d9700f", "bg": "rgba(245,130,32,.13)",
         "desc": "Trésorerie, brouillards de caisse et rapprochements de chèques.",
         "stat1": f"{nb_brouillard} brouillards", "stat2": f"{nb_cheques} états chèques"},
        {"key": "technique", "title": "Services Techniques & SAV", "route": "/services-techniques-dashboard",
         "icon": "wrench", "color": "#5f9e2b", "bg": "rgba(141,198,63,.18)",
         "desc": "Équipes techniques, interventions SAV, ordres de mission et charge.",
         "stat1": f"{nb_equipes} équipes", "stat2": f"{taches_cours} tâches en cours"},
        {"key": "commercial", "title": "Commercial & CRM", "route": "/commercial-dashboard",
         "icon": "trending", "color": "#0a5d61", "bg": "rgba(10,93,97,.10)",
         "desc": "Pipeline CRM, leads, tunnel de conversion devis et clients.",
         "stat1": f"{leads_actifs} leads", "stat2": f"{_count('Customer', {'disabled': 0})} clients"},
    ]

    return [h for h in catalog if roles & _HUB_ROLES.get(h["key"], set())]

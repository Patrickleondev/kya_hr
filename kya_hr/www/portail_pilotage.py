"""Page : Portail de pilotage (Accueil) — navigation Département → Équipe → Opérations.

Route : /portail-pilotage

Hub hiérarchique à 3 niveaux :
  1. les 4 départements (DG, DSS, DST, DSC) ;
  2. les équipes de chaque département ;
  3. les opérations (dashboards, web forms, listes) de chaque équipe.

Chaque département n'apparaît que si l'utilisateur a un rôle d'accès. Quelques
indicateurs réels sont calculés au niveau département. Tout est défensif.
"""
from __future__ import annotations

import frappe


# Rôles transverses qui voient tout le portail
_DIR = {"System Manager", "Directeur General", "Directeur Général", "DG", "DGA",
        "Responsable RH", "HR Manager", "Auditeur Interne", "Auditeur"}

_DEPT_ROLES = {
    "DG": _DIR,
    "DSS": _DIR | {
        "HR User", "Responsable RH",
        "Caissier", "Comptable", "DFC", "DAAF", "Accounts Manager", "Accounts User",
        "Responsable Achats", "Purchase Manager", "Purchase User", "Chef Service",
        "Chef Service Achats",
        "Chargé des Stocks", "Responsable Stock", "Magasinier", "Stock User", "Stock Manager",
        "Responsable Logistique", "Logisticien", "Gestionnaire de Flotte", "Fleet Manager",
    },
    "DST": _DIR | {"Responsable Technique", "Chef de Projet", "Chef Service",
                   "Chef Equipe", "Chef d'Equipe", "Responsable Equipe"},
    "DSC": _DIR | {"Responsable Commercial", "Commercial", "Chargé Commercial",
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
        context.tree_json = _json.dumps(get_portail_tree(), default=str)
    except Exception:
        context.tree_json = "[]"
        frappe.log_error(frappe.get_traceback(), "portail-pilotage: tree")
    return context


def _count(dt, filters=None):
    try:
        if not frappe.db.exists("DocType", dt):
            return 0
        return frappe.db.count(dt, filters or {})
    except Exception:
        return 0


def _op(label, route, icon="file"):
    return {"label": label, "route": route, "icon": icon}


@frappe.whitelist()
def get_portail_tree() -> list:
    """Arbre Département → Équipe → Opérations, filtré par rôle, + stats réelles."""
    roles = set(frappe.get_roles(frappe.session.user))

    # ── Indicateurs département (réels, légers) ──
    nb_emp = _count("Employee", {"status": "Active"})
    leads = _count("Lead", {"status": ["not in", ("Converted", "Do Not Contact", "Lost Quotation")]})
    da_attente = _count("Demande Achat KYA", {"workflow_state": ["not in",
                        ("Approuvé", "Approuve", "Rejeté", "Rejete", "Annulé", "Annule")]})
    sav = _count("fiche technique curative")
    missions = _count("fiche de mission")

    tree = [
        {
            "key": "DG", "code": "DG", "title": "Direction Générale", "icon": "building",
            "color": "#0d7377", "bg": "rgba(13,115,119,.10)",
            "desc": "Pilotage transverse, réunions, indicateurs.",
            "stat": f"{nb_emp} employés actifs",
            "teams": [
                {"name": "Pilotage & Direction", "icon": "building", "ops": [
                    _op("Vue consolidée (4 départements)", "/direction-dashboard", "chart"),
                    _op("Sorties & destinations (clients/projets)", "/dga-projets-clients", "truck"),
                    _op("Tableau de bord global", "/kya-tableau-de-bord", "chart"),
                ]},
                {"name": "Réunions & Visites", "icon": "users", "ops": [
                    _op("Réunions & Visites", "/kya-reunion-dashboard", "users"),
                ]},
            ],
        },
        {
            "key": "DSS", "code": "DSS", "title": "Services Supports", "icon": "package",
            "color": "#F58220", "bg": "rgba(245,130,32,.13)",
            "desc": "RH, Comptabilité, Achats, Stock & Logistique.",
            "stat": f"{da_attente} demandes d'achat en attente",
            "teams": [
                {"name": "Ressources Humaines", "icon": "users", "ops": [
                    _op("Présences", "/rapport-presence", "clock"),
                    _op("Gestion des congés", "/gestion-conges", "calendar"),
                    _op("Permissions de sortie", "/permission-sortie-employe", "file"),
                    _op("Formations", "/formation-dashboard", "chart"),
                ]},
                {"name": "Comptabilité & Finance", "icon": "coins", "ops": [
                    _op("Dashboard Comptabilité", "/comptabilite-dashboard", "chart"),
                    _op("Brouillard de caisse", "/brouillard-caisse", "file"),
                    _op("État récap. chèques", "/etat-recap", "file"),
                ]},
                {"name": "Achats & Approvisionnement", "icon": "cart", "ops": [
                    _op("Dashboard Achats", "/achats-dashboard", "chart"),
                    _op("Demande d'achat", "/demande-achat", "file"),
                    _op("Bon de commande", "/bon-commande", "file"),
                    _op("Appel d'offre", "/appel-offre", "file"),
                    _op("Marché", "/marche-kya", "file"),
                ]},
                {"name": "Stock & Logistique", "icon": "box", "ops": [
                    _op("Dashboard Stocks", "/kya-stocks-dashboard", "box"),
                    _op("Stock par état", "/stock-etat", "box"),
                    _op("Sorties par client / projet", "/dga-projets-clients", "truck"),
                    _op("Dashboard Logistique", "/kya-logistique-dashboard", "truck"),
                    _op("Inventaire & sorties", "/inventaire-dashboard", "file"),
                    _op("PV entrée matériel", "/pv-entree-materiel", "file"),
                    _op("PV sortie matériel", "/pv-sortie-materiel", "file"),
                    _op("Retour matériel", "/retour-materiel", "file"),
                    _op("Sortie véhicule", "/sortie-vehicule", "truck"),
                    _op("Plein de carburant", "/plein-carburant", "truck"),
                    _op("Entretien véhicule", "/entretien-vehicule", "truck"),
                ]},
            ],
        },
        {
            "key": "DST", "code": "DST", "title": "Services Techniques", "icon": "wrench",
            "color": "#5f9e2b", "bg": "rgba(141,198,63,.18)",
            "desc": "Installation, Maintenance & SAV, Offres, terrain.",
            "stat": f"{sav} interventions SAV · {missions} missions",
            "teams": [
                {"name": "Vue d'ensemble & équipes", "icon": "chart", "ops": [
                    _op("Dashboard Services Techniques & SAV", "/services-techniques-dashboard", "chart"),
                ]},
                {"name": "Interventions & SAV terrain", "icon": "wrench", "ops": [
                    _op("Intervention SAV (fiche curative)", "/prevention-curative", "wrench"),
                    _op("Ordre de mission", "/fiche-de-mission", "route"),
                    _op("Réception lampadaires", "/fiche-recept-lamp", "file"),
                    _op("Réception batteries", "/fiche-de-reception-de-batteries", "file"),
                ]},
            ],
        },
        {
            "key": "DSC", "code": "DSC", "title": "Services Commerciaux", "icon": "trending",
            "color": "#0a5d61", "bg": "rgba(10,93,97,.10)",
            "desc": "CRM, prospection, devis, clients.",
            "stat": f"{leads} leads actifs",
            "teams": [
                {"name": "Commercial & CRM", "icon": "trending", "ops": [
                    _op("Dashboard Commercial & CRM", "/commercial-dashboard", "chart"),
                    _op("Leads / prospects", "/app/lead", "trending"),
                    _op("Clients", "/app/customer", "users"),
                    _op("Enquête satisfaction client", "/enquête-satisfaction-client", "file"),
                ]},
                {"name": "Communication", "icon": "users", "ops": [
                    _op("Espace CRM", "/app/crm", "trending"),
                ]},
            ],
        },
    ]

    return [d for d in tree if roles & _DEPT_ROLES.get(d["key"], set())]

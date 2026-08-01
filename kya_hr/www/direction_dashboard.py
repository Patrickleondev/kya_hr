import json as _json

import frappe
from frappe import _
from frappe.utils import flt, formatdate, today, add_days

no_cache = 1

_ALLOWED_ROLES = {
    "Directeur Général", "DGA", "DAAF", "DFC",
    "Auditeur Interne", "System Manager",
}

# ════════════════════════════════════════════════════════════════════
#  Macro-départements (6 onglets, réorg 01/08/2026 : 5 Directions officielles
#  + DG/transversaux). Un onglet par Direction + un onglet DG qui regroupe
#  aussi les services transversaux (Audit, QHSE, IT, Laboratory, Institute,
#  Fondation, Prospection, Agence Niger) : trop petits/vacants pour mériter
#  chacun leur propre onglet pour l'instant.
#
#  Classification par ARBRE DE DÉPARTEMENT (pas par nom d'équipe) : une
#  équipe est classée en remontant `parent_department` jusqu'à retomber sur
#  l'une des 5 Directions/DG. Ancien système (liste de noms d'équipe en dur)
#  abandonné : il devenait faux dès qu'une équipe changeait de département
#  sans être renommée (cf. `Equipe KYA` ne supporte pas le renommage via API
#  — les noms d'équipe restent parfois datés même après une réorg réussie).
# ════════════════════════════════════════════════════════════════════
MACRO_ORDER = ["dg", "tech", "industrielle", "comm", "rh", "daf"]
MACRO_META = {
    "dg":           {"label": "Direction Générale",   "sub": "Informatique / SI · Audit · Transversaux DG"},
    "tech":         {"label": "Direction Technique & Projets", "sub": "Bureau d'études · Installations & Chantiers · SAV · Contrôle & Supervision"},
    "industrielle": {"label": "Direction Industrielle", "sub": "Production & Assemblage · Supply Chain & Magasins"},
    "comm":         {"label": "Développement Commercial", "sub": "Grands Comptes · Ventes & Distribution · Marketing & Communication"},
    "rh":           {"label": "Ressources Humaines (DRH)", "sub": "Recrutement · Administration & Paie · Formation · Relations Sociales"},
    "daf":          {"label": "Administrative & Financière (DAF)", "sub": "Achats & Approvisionnements · Comptabilité & Fiscalité · Moyens Généraux"},
}
# Direction (Department racine, is_group=1) -> onglet du dashboard.
_DIRECTION_TO_MACRO = {
    "direction générale": "dg",
    "direction technique & projets": "tech",
    "direction industrielle": "industrielle",
    "direction du développement commercial": "comm",
    "direction des ressources humaines (drh)": "rh",
    "direction administrative & financière (daf)": "daf",
    "informatique & logiciel (it)": "dg",
}
# Services transversaux rattachés directement au DG (pas sous une Direction).
_TRANSVERSAL_DG = {
    "audit interne & risques", "qhse", "kya-energy laboratory",
    "kya-institute of technology", "fondation kya",
    "prospection & développement du réseau d'agences",
    "agence kya-energy group niger",
}


def _department_ancestor_chain(dept_name: str | None) -> list[str]:
    """Chaîne [dept, parent, grand-parent, ...] jusqu'à la racine (noms en
    minuscule, sans le suffixe " - KYA"/" - D"). Mise en cache process (le
    tableau de bord se recharge à chaque requête, la table Department ne
    bouge pas assez souvent pour justifier plus)."""
    chain: list[str] = []
    seen = set()
    cur = dept_name
    while cur and cur not in seen:
        seen.add(cur)
        label = frappe.db.get_value("Department", cur, "department_name") or cur
        chain.append(label.strip().lower())
        cur = frappe.db.get_value("Department", cur, "parent_department")
    return chain


def _macro_of_team(equipe_name: str | None, dept_name: str | None = None) -> str:
    """Renvoie la clé macro-département (dg|tech|industrielle|comm|rh|daf)
    d'une équipe en remontant son Department jusqu'à la Direction/DG qui la porte."""
    chain = _department_ancestor_chain(dept_name)
    for label in chain:
        if label in _TRANSVERSAL_DG:
            return "dg"
        if label in _DIRECTION_TO_MACRO:
            return _DIRECTION_TO_MACRO[label]
    # Repli par mots-clés (équipe sans département résolu / instance locale
    # encore sur l'ancien arbre à 4 macro-départements, ex. environnement de
    # test qui n'a pas encore reçu la réorg du 01/08).
    blob = f"{(equipe_name or '').lower()} {(dept_name or '').lower()}"
    if any(k in blob for k in ("informat", "système d'info", "systeme d'info", " si ", "r&d", "research", "audit")):
        return "dg"
    if any(k in blob for k in ("rh", "ressources humaines", "recrutement", "gpec", "relations sociales")):
        return "rh"
    if any(k in blob for k in ("achat", "stock", "compt", "financ", "logist", "dispatch",
                                "approvision", "magasin", "moyens gen", "juridique", "tresorerie", "trésorerie")):
        return "daf"
    if any(k in blob for k in ("industr", "supply chain", "methode", "méthode", "qualite produit", "qualité produit")):
        return "industrielle"
    if any(k in blob for k in ("install", "maintenance", "sav", "fabric", "assembl", "offre",
                                "production", "operations", "technique", "génie", "genie", "controle", "contrôle")):
        return "tech"
    if any(k in blob for k in ("commerc", "vente", "sales", "communicat", "marketing")):
        return "comm"
    return "dg"  # administratif / rattaché à la DG par défaut


# ── Helpers défensifs : tout doctype peut être absent sur une instance ──
def _dt_exists(dt: str) -> bool:
    try:
        return bool(frappe.db.exists("DocType", dt))
    except Exception:
        return False


def _count(dt: str, filters=None) -> int:
    if not _dt_exists(dt):
        return 0
    try:
        return frappe.db.count(dt, filters or {})
    except Exception:
        return 0


def _waiting(dt: str, states) -> int:
    if not _dt_exists(dt):
        return 0
    try:
        return frappe.db.count(dt, {"workflow_state": ["in", tuple(states)]})
    except Exception:
        return 0


def _sum(dt: str, field: str, filters=None) -> float:
    if not _dt_exists(dt):
        return 0.0
    try:
        rows = frappe.get_all(dt, filters=filters or {}, fields=[f"SUM(`{field}`) as s"])
        return flt(rows[0].s) if rows and rows[0].s else 0.0
    except Exception:
        return 0.0


def _count_series(dt: str, prefix: str) -> int:
    """Compte uniquement les enregistrements dont le nom suit la naming_series
    réelle (ex. 'FTB-%'). Exclut les brouillons de test du collègue (noms au
    hasard saisis avant que la série ne soit branchée, ex. 'jop9cduv43',
    'test 1') sans dépendre d'un champ statut qui n'existe pas partout."""
    if not _dt_exists(dt):
        return 0
    try:
        return frappe.db.count(dt, {"name": ["like", f"{prefix}-%"]})
    except Exception:
        return 0


_WAIT_STATES = ("En attente Chef", "En attente DAAF", "En attente DG",
                "En attente Direction", "En attente RH", "En attente Audit",
                "En attente Magasin", "En attente Comptable", "En attente DFC",
                "En attente Achats & Stock", "En attente Signature Salarié",
                "En attente Resp. Stagiaires", "En attente Chef de Service",
                "En attente du Supérieur Immédiat", "En attente Signature")
_DG_STATES = ("En attente DG", "En attente Direction")


def _card(label, value, sub="", unit="", icon="layers", accent="slate", trend=None, dir=None):
    return {"label": label, "value": value, "sub": sub, "unit": unit,
            "icon": icon, "accent": accent, "trend": trend, "dir": dir}


def _fmt_m(xof: float) -> str:
    """Formate un montant XOF en 'X,Y M' (millions, virgule décimale FR)."""
    m = (xof or 0) / 1_000_000.0
    return f"{m:,.1f}".replace(",", " ").replace(".", ",")


def _build_overview() -> dict:
    """Construit la vue DG structurée par 4 macro-départements (données réelles)."""
    week_ago = add_days(today(), -7)

    # ── Équipes (effectif + présence du jour) classées par macro ──
    macro_teams = {k: [] for k in MACRO_ORDER}
    try:
        rows = frappe.db.sql(
            """
            SELECT eq.name AS equipe, eq.nom_equipe AS nom, eq.departement AS dept,
                   eq.chef_equipe_name AS chef,
                   COUNT(DISTINCT e.name) AS eff,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS pres,
                   SUM(CASE WHEN a.status IN ('On Leave','Half Day') THEN 1 ELSE 0 END) AS conges,
                   SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS abs
            FROM `tabEquipe KYA` eq
            LEFT JOIN `tabEmployee` e
                ON e.custom_kya_equipe = eq.name AND e.status='Active'
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = CURDATE()
            GROUP BY eq.name, eq.nom_equipe, eq.departement, eq.chef_equipe_name
            ORDER BY eff DESC
            """, as_dict=True)
        for r in rows:
            macro = _macro_of_team(r.nom or r.equipe, r.dept)
            macro_teams[macro].append({
                "equipe": r.nom or r.equipe, "chef": r.chef or "",
                "eff": int(r.eff or 0), "pres": int(r.pres or 0),
                "conges": int(r.conges or 0), "abs": int(r.abs or 0),
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "dg-overview: equipes")

    def _macro_eff(m):
        return sum(t["eff"] for t in macro_teams[m])

    def _macro_pres(m):
        return sum(t["pres"] for t in macro_teams[m])

    effectif_actif = _count("Employee", {"status": "Active"})
    presents_jour = _count("Attendance", {"attendance_date": today(), "status": "Present"})
    conges_jour = (_count("Attendance", {"attendance_date": today(), "status": "On Leave"})
                   or _waiting("Planning Conge", ("Approuvé", "Validé")))

    # ── Compteurs workflow « en attente » (tous modules) ──
    modules = {
        "Demandes d'achat": _waiting("Demande Achat KYA", _WAIT_STATES),
        "Bons de commande": _waiting("Bon Commande KYA", _WAIT_STATES),
        "Permissions sortie": (_waiting("Permission Sortie Employe", _WAIT_STATES)
                               + _waiting("Permission Sortie Stagiaire", _WAIT_STATES)),
        "Plannings congé": _waiting("Planning Conge", _WAIT_STATES),
        "PV matériel": (_waiting("PV Sortie Materiel", _WAIT_STATES)
                        + _waiting("PV Entree Materiel", _WAIT_STATES)
                        + _waiting("PV Retour Materiel", _WAIT_STATES)),
        "Inventaires": _waiting("Inventaire KYA", _WAIT_STATES),
        "Brouillards caisse": _waiting("Brouillard Caisse", _WAIT_STATES),
        "Contrats": _waiting("KYA Contrat", _WAIT_STATES),
    }
    modules_total = sum(modules.values())

    achat_dg_n = _waiting("Demande Achat KYA", _DG_STATES)
    achat_dg_m = _sum("Demande Achat KYA", "montant_total",
                      {"workflow_state": ["in", _DG_STATES]})

    # ════════ HERO (global) ════════
    hero = [
        _card("Effectif actif", str(effectif_actif), f"{effectif_actif} postes", icon="users"),
        _card("Présents aujourd'hui", str(presents_jour),
              (f"{round(presents_jour / effectif_actif * 100)} % de l'effectif" if effectif_actif else "—"),
              icon="usercheck"),
        _card("Congés en cours", str(conges_jour), "", icon="calendar"),
        _card("En attente de visa", str(modules_total), "tous départements",
              unit="workflows", icon="inbox"),
        _card("Demandes d'achat à valider", _fmt_m(achat_dg_m), f"{achat_dg_n} demandes",
              unit="M FCFA", icon="wallet"),
    ]

    # ════════ DG : Informatique / SI + administratif ════════
    contrats_attente = _waiting("KYA Contrat", ("En attente Signature", "En attente DG",
                                                "En attente Direction"))
    dg_cards = [
        _card("Demandes d'achat — attente DG", str(achat_dg_n), _fmt_m(achat_dg_m) + " M FCFA",
              icon="cart", accent="orange"),
        _card("Plannings congé à valider", str(_waiting("Planning Conge", _DG_STATES)),
              "", icon="calendar", accent="teal"),
        _card("Contrats à signer", str(contrats_attente), "", icon="filecheck", accent="teal"),
        _card("Parc informatique", str(_count("Asset")), "", unit="actifs",
              icon="monitor", accent="green"),
        _card("Tickets / incidents SI", str(_count("Issue", {"status": ["in", ("Open", "Replied")]})),
              "ouverts", icon="ticket", accent="orange"),
    ]
    contrat_rows = []
    try:
        if _dt_exists("KYA Contrat"):
            for c in frappe.get_all("KYA Contrat",
                                    filters={"workflow_state": ["in", ("En attente Signature",
                                                                       "En attente DG", "En attente Direction")]},
                                    fields=["name", "employee_name", "designation", "workflow_state"],
                                    limit_page_length=6):
                contrat_rows.append({"objet": c.get("name"), "partie": c.get("employee_name") or "—",
                                     "info": c.get("designation") or "", "statut": c.get("workflow_state") or ""})
    except Exception:
        pass

    # ════════ DAF : Achats & Stock + Comptabilité & Finance + Moyens Généraux ════════
    achats_cards = [
        _card("Demandes d'achat en attente", str(_waiting("Demande Achat KYA", _WAIT_STATES)),
              "", icon="cart", accent="orange"),
        _card("Bons de commande en attente", str(_waiting("Bon Commande KYA", _WAIT_STATES)),
              "", icon="file", accent="teal"),
        _card("Appels d'offres", str(_count("Appel Offre KYA")), "", icon="file", accent="slate"),
        _card("Inventaires en attente", str(_waiting("Inventaire KYA", _WAIT_STATES)),
              "", icon="package", accent="teal"),
        _card("PV matériel en attente",
              str(_waiting("PV Sortie Materiel", _WAIT_STATES)
                  + _waiting("PV Entree Materiel", _WAIT_STATES)
                  + _waiting("PV Retour Materiel", _WAIT_STATES)),
              "réception / retour", icon="filecheck", accent="slate"),
    ]
    # Caisse (semaine)
    ent_sem = _sum("Brouillard Caisse", "total_entrees", {"date_brouillard": [">=", week_ago]})
    sor_sem = _sum("Brouillard Caisse", "total_sorties", {"date_brouillard": [">=", week_ago]})
    solde = _sum("Brouillard Caisse", "total_entrees") - _sum("Brouillard Caisse", "total_sorties")
    compta_cards = [
        _card("Brouillards caisse (sem.)", str(_count("Brouillard Caisse", {"date_brouillard": [">=", week_ago]})),
              "à clôturer", icon="receipt", accent="teal"),
        _card("Entrées (semaine)", _fmt_m(ent_sem), "caisse + banque", unit="M FCFA",
              icon="arrowup", accent="green"),
        _card("Sorties (semaine)", _fmt_m(sor_sem), "décaissements", unit="M FCFA",
              icon="arrowdown", accent="orange"),
        _card("Solde caisse", _fmt_m(solde), "cumulé", unit="M FCFA", icon="coins", accent="teal"),
    ]
    # Ordres de mission + fiches budgétaires (prod) — masqués si absents
    for dt_, lbl, ic in [("Ordre de Mission", "Ordres de mission en attente", "route"),
                         ("Ordre de mission", "Ordres de mission en attente", "route")]:
        if _dt_exists(dt_):
            compta_cards.append(_card(lbl, str(_waiting(dt_, _WAIT_STATES)), "", icon=ic, accent="teal"))
            break
    for dt_ in ("Fiche Budgetaire Mission", "Fiche Budgétaire de Mission", "Fiche Budgetaire de Mission"):
        if _dt_exists(dt_):
            compta_cards.append(_card("Fiches budgétaires mission", str(_waiting(dt_, _WAIT_STATES)),
                                      "en attente de visa", icon="briefcase", accent="orange"))
            break

    # ════════ INDUSTRIELLE : Production & Assemblage + Supply Chain & Magasins ════════
    # Direction neuve (réorg 01/08/2026), coordonnée par le DG en attendant un
    # directeur nommé — peu de doctypes dédiés encore, on s'appuie sur les
    # équipes (effectif/présence) + le stock (Supply Chain & Magasins = stock).
    industrielle_teams = [t for t in macro_teams["industrielle"] if t["eff"] > 0]
    # Fiches techniques produit (nouvelles web pages du collègue technique,
    # remplacent les anciens web forms/doctypes CRM du même nom) — contrôle
    # qualité batterie/lampadaire en sortie d'assemblage.
    ftb_count = _count_series("Fiche Technique Batterie", "FTB")
    ftl_count = _count_series("Fiche Technique Lampadaire", "FTL")
    industrielle_cards = [
        _card("Effectif industriel", str(_macro_eff("industrielle")),
              (f"{_macro_pres('industrielle')} présents" if _macro_eff("industrielle") else ""),
              icon="users", accent="teal"),
        _card("Articles au catalogue", str(_count("Article KYA")), "Production & Supply Chain",
              icon="package", accent="slate"),
        _card("Inventaires en attente", str(_waiting("Inventaire KYA", _WAIT_STATES)),
              "Supply Chain & Magasins", icon="filecheck", accent="orange"),
        _card("Mouvements stock (sem.)", str(_count("Mouvement Stock KYA", {"creation": [">=", week_ago]})),
              "entrées/sorties", icon="route", accent="teal"),
        _card("Fiches techniques produit", str(ftb_count + ftl_count),
              f"{ftb_count} batteries · {ftl_count} lampadaires", icon="filecheck", accent="green"),
    ]
    industrielle_rows = []
    for t in sorted(industrielle_teams, key=lambda x: -x["eff"]):
        charge = round(t["pres"] / t["eff"] * 100) if t["eff"] else 0
        industrielle_rows.append({"equipe": t["equipe"], "eff": t["eff"], "pres": t["pres"], "charge": charge})

    # ════════ RH (DRH) : effectif, congés, permissions, contrats, documents ════════
    docs_rh_attente = (_waiting("Document RH KYA", _WAIT_STATES)
                        + _waiting("Avenant Contrat KYA", _WAIT_STATES)
                        + _waiting("Contrat Stage Immersion KYA", _WAIT_STATES)
                        + _waiting("Fiche de Poste KYA", _WAIT_STATES))
    rh_cards = [
        _card("Effectif RH (équipe)", str(_macro_eff("rh")),
              (f"{_macro_pres('rh')} présents" if _macro_eff("rh") else ""),
              icon="users", accent="teal"),
        _card("Effectif KYA total", str(effectif_actif), "tous départements", icon="usercheck", accent="slate"),
        _card("Congés/permissions en attente", str(modules["Plannings congé"] + modules["Permissions sortie"]),
              "", icon="calendar", accent="orange"),
        _card("Contrats en attente", str(contrats_attente), "signature en cours", icon="filecheck", accent="teal"),
        _card("Documents RH en attente", str(docs_rh_attente),
              "certificats · avenants · immersion · fiches de poste", icon="file", accent="orange"),
    ]

    # ════════ TECHNIQUES : équipes + ops terrain réelles (prod) ════════
    # 01/08/2026 : le collègue technique a abandonné ses anciens web forms/
    # doctypes module CRM (fiche technique curative, fiche de mission,
    # fiche_recep_tech_lampa, fiche de recpt de batt — laissés en l'état,
    # plus alimentés) au profit de nouvelles Web Page (Frappe CMS + JS,
    # signature terrain) adossées à de nouveaux doctypes "KYA HR"/"Custom" :
    #   - Fiche Compte Rendu Intervention (FCRI-...) : SAV/maintenance curative.
    #   - Ordre de mission2 : déplacements terrain (remplace "fiche de mission").
    #   - Fiche Installation (+ Cellule PV Mesuree, Siege KYA) : installation &
    #     audit contrôle double-signature technicien/auditeur — circuit prêt
    #     mais tout juste mis en service (peut afficher 0 le temps que les
    #     premières fiches terrain arrivent).
    tech_teams = [t for t in macro_teams["tech"] if t["eff"] > 0]
    sav_count = _count_series("Fiche Compte Rendu Intervention", "FCRI") or _count("fiche technique curative")
    sav_ok = _count("Fiche Compte Rendu Intervention", {"etat_final": "Fonctionnel"})
    mission_count = (_count("Ordre de mission2") or _count("Ordre de Mission")
                     or _count("fiche de mission"))
    install_count = _count("Fiche Installation")
    install_cloture = _count("Fiche Installation", {"statut": "Cloture"})
    tech_cards = [
        _card("Effectif technique", str(_macro_eff("tech")),
              (f"{_macro_pres('tech')} présents" if _macro_eff("tech") else ""),
              icon="users", accent="teal"),
        _card("Interventions SAV", str(sav_count),
              (f"{round(sav_ok / sav_count * 100)} % « Fonctionnel »" if sav_count else "fiches d'intervention"),
              icon="wrench", accent="orange"),
        _card("Ordres de mission", str(mission_count), "déplacements terrain",
              icon="route", accent="teal"),
        _card("Installations & audits", str(install_count),
              (f"{install_cloture} clôturées" if install_count else "circuit prêt, en attente des 1ères fiches"),
              icon="filecheck", accent="green"),
    ]
    tech_rows = []
    for t in sorted(tech_teams, key=lambda x: -x["eff"]):
        charge = round(t["pres"] / t["eff"] * 100) if t["eff"] else 0
        tech_rows.append({"equipe": t["equipe"], "eff": t["eff"], "pres": t["pres"], "charge": charge})

    # ════════ COMMERCIAUX : équipes + CRM (leads, opp, devis, clients) ════════
    leads_total = _count("Lead", {"status": ["not in", ("Converted", "Do Not Contact", "Lost Quotation")]})
    comm_cards = [
        _card("Leads actifs", str(leads_total), "pipeline CRM", icon="trending", accent="teal"),
        _card("Clients", str(_count("Customer", {"disabled": 0})), "comptes actifs", icon="userplus", accent="green"),
        _card("Effectif commercial", str(_macro_eff("comm")),
              (f"{_macro_pres('comm')} présents" if _macro_eff("comm") else ""),
              icon="users", accent="teal"),
        _card("Devis / opportunités", str(_count("Opportunity", {"status": ["in", ("Open", "Quotation", "Replied")]})
              + _count("Quotation", {"status": ["in", ("Draft", "Open", "Submitted")]})),
              "en cours", icon="file", accent="orange"),
    ]
    # Équipes commerciales (effectif / présence / charge)
    comm_teams = []
    for t in sorted([x for x in macro_teams["comm"] if x["eff"] > 0], key=lambda x: -x["eff"]):
        charge = round(t["pres"] / t["eff"] * 100) if t["eff"] else 0
        comm_teams.append({"equipe": t["equipe"], "eff": t["eff"], "pres": t["pres"], "charge": charge})
    # Pipeline réel : répartition des leads par statut (CRM natif)
    leads_status = []
    try:
        if _dt_exists("Lead"):
            rows = frappe.db.sql(
                """SELECT COALESCE(NULLIF(status,''),'Lead') AS statut, COUNT(*) AS n
                   FROM `tabLead` WHERE status NOT IN ('Converted','Do Not Contact','Lost Quotation')
                   GROUP BY statut ORDER BY n DESC LIMIT 8""", as_dict=True)
            tot = sum(int(r.n) for r in rows) or 1
            for r in rows:
                leads_status.append({"statut": r.statut, "n": int(r.n),
                                     "part": round(int(r.n) / tot * 100)})
    except Exception:
        pass
    # Pipeline opportunités (si le module CRM Opportunity est utilisé)
    pipe_rows = []
    try:
        if _dt_exists("Opportunity"):
            rows = frappe.db.sql(
                """SELECT COALESCE(NULLIF(sales_stage,''),'Prospection') AS etape,
                          COUNT(*) AS opp, COALESCE(SUM(opportunity_amount),0) AS montant
                   FROM `tabOpportunity` WHERE status IN ('Open','Quotation','Replied')
                   GROUP BY etape ORDER BY montant DESC LIMIT 6""", as_dict=True)
            tot = sum(flt(r.montant) for r in rows) or 1
            for r in rows:
                pipe_rows.append({"etape": r.etape, "opp": int(r.opp),
                                  "montant": _fmt_m(r.montant) + " M",
                                  "part": round(flt(r.montant) / tot * 100)})
    except Exception:
        pass

    # ════════ Charts (réels) ════════
    pres_labels, pres_p, pres_c, pres_a = [], [], [], []
    for m in MACRO_ORDER:
        pres_labels.append(MACRO_META[m]["label"].replace("Services ", ""))
        pres_p.append(sum(t["pres"] for t in macro_teams[m]))
        pres_c.append(sum(t["conges"] for t in macro_teams[m]))
        pres_a.append(sum(t["abs"] for t in macro_teams[m]))
    presence_chart = {"labels": pres_labels, "presents": pres_p, "conges": pres_c, "absents": pres_a}

    wf_counts = {"En attente": 0, "Approuvé": 0, "Rejeté": 0, "Brouillon": 0}
    for dt_ in ("Demande Achat KYA", "Bon Commande KYA", "Permission Sortie Employe",
                "Planning Conge", "PV Sortie Materiel", "PV Entree Materiel",
                "Inventaire KYA", "Brouillard Caisse", "KYA Contrat"):
        if not _dt_exists(dt_):
            continue
        try:
            for r in frappe.db.sql(f"SELECT workflow_state ws, COUNT(*) n FROM `tab{dt_}` GROUP BY ws",
                                   as_dict=True):
                st = (r.ws or "").lower()
                if "attente" in st:
                    wf_counts["En attente"] += r.n
                elif any(k in st for k in ("approuv", "valid", "archiv", "signé", "signe", "clôtur", "clotur")):
                    wf_counts["Approuvé"] += r.n
                elif any(k in st for k in ("rejet", "annul", "refus")):
                    wf_counts["Rejeté"] += r.n
                else:
                    wf_counts["Brouillon"] += r.n
        except Exception:
            pass

    caisse_chart = {"labels": [], "entrees": [], "sorties": []}
    try:
        if _dt_exists("Brouillard Caisse"):
            for r in frappe.db.sql(
                """SELECT CONCAT(YEAR(date_brouillard),'-',LPAD(MONTH(date_brouillard),2,'0')) mois,
                          SUM(total_entrees) ent, SUM(total_sorties) sor
                   FROM `tabBrouillard Caisse`
                   WHERE date_brouillard >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                   GROUP BY mois ORDER BY mois""", as_dict=True):
                caisse_chart["labels"].append(r.mois or "")
                caisse_chart["entrees"].append(round(flt(r.ent) / 1_000_000, 2))
                caisse_chart["sorties"].append(round(flt(r.sor) / 1_000_000, 2))
    except Exception:
        pass

    counts = {
        "dg": len(contrat_rows) + achat_dg_n,
        "daf": modules["Demandes d'achat"] + modules["Bons de commande"]
               + modules["Inventaires"] + modules["PV matériel"],
        "industrielle": _waiting("Inventaire KYA", _WAIT_STATES),
        "tech": sav_count + mission_count,
        "comm": leads_total,
        "rh": modules["Plannings congé"] + modules["Permissions sortie"] + docs_rh_attente,
    }

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero,
        "depts": {
            "dg": {"meta": MACRO_META["dg"], "count": counts["dg"], "cards": dg_cards,
                   "contrats": contrat_rows},
            "tech": {"meta": MACRO_META["tech"], "count": counts["tech"],
                     "cards": tech_cards, "teams": tech_rows},
            "industrielle": {"meta": MACRO_META["industrielle"], "count": counts["industrielle"],
                              "cards": industrielle_cards, "teams": industrielle_rows},
            "comm": {"meta": MACRO_META["comm"], "count": counts["comm"],
                     "cards": comm_cards, "teams": comm_teams,
                     "leads_status": leads_status, "pipeline": pipe_rows},
            "rh": {"meta": MACRO_META["rh"], "count": counts["rh"], "cards": rh_cards},
            "daf": {"meta": MACRO_META["daf"], "count": counts["daf"],
                    "achats": achats_cards, "compta": compta_cards},
        },
        "charts": {"presence": presence_chart, "workflows": wf_counts, "caisse": caisse_chart},
        "modules": modules, "modules_total": modules_total,
    }


@frappe.whitelist()
def get_dg_overview() -> dict:
    """Endpoint rafraîchissement du tableau de bord DG (4 macro-départements)."""
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la Direction Générale."), frappe.PermissionError)
    return _build_overview()


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la Direction Générale."), frappe.PermissionError)

    # Nouvelle vue par macro-départements (maquette DG). Rendu initial + refresh
    # via get_dg_overview(). Défensif : si ça casse, on garde l'ancien contexte.
    try:
        context.overview_json = _json.dumps(_build_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: overview")

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

    # ── 5.1 Synthèse par DÉPARTEMENT (toutes les équipes en un écran) ──
    departements = []
    try:
        rows = frappe.db.sql(
            """
            SELECT
                COALESCE(e.department, '(Sans département)') AS dept,
                COUNT(DISTINCT e.name) AS effectif,
                SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS presents,
                SUM(CASE WHEN a.late_entry=1 THEN 1 ELSE 0 END) AS retards,
                SUM(CASE WHEN a.status IN ('On Leave','Half Day') THEN 1 ELSE 0 END) AS conges,
                SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absents
            FROM `tabEmployee` e
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = CURDATE()
            WHERE e.status='Active'
            GROUP BY dept
            ORDER BY effectif DESC
            """,
            as_dict=True,
        )
        departements = rows
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: departements")

    # ── 5.1 Synthèse par ÉQUIPE (Employee.custom_kya_equipe -> Equipe KYA) ──
    # En prod, chaque employé est rattaché à une équipe : cette vue se peuple
    # automatiquement. Sur une instance sans équipes, la liste reste vide.
    equipes = []
    try:
        rows = frappe.db.sql(
            """
            SELECT
                eq.name AS equipe,
                eq.nom_equipe AS nom,
                eq.departement AS departement,
                eq.chef_equipe_name AS chef,
                COUNT(DISTINCT e.name) AS effectif,
                SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS presents,
                SUM(CASE WHEN a.late_entry=1 THEN 1 ELSE 0 END) AS retards,
                SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absents
            FROM `tabEquipe KYA` eq
            LEFT JOIN `tabEmployee` e
                ON e.custom_kya_equipe = eq.name AND e.status='Active'
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = CURDATE()
            GROUP BY eq.name, eq.nom_equipe, eq.departement, eq.chef_equipe_name
            HAVING effectif > 0
            ORDER BY effectif DESC
            """,
            as_dict=True,
        )
        equipes = rows
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: equipes")

    # ── 5.1 Bandeau MULTI-MODULES : tout ce qui est "en attente" partout ──
    def _count_waiting(doctype, states):
        try:
            return frappe.db.count(doctype, {"workflow_state": ["in", states]})
        except Exception:
            return 0

    waiting_states = ("En attente Chef", "En attente DAAF", "En attente DG",
                      "En attente Direction", "En attente RH", "En attente Audit",
                      "En attente Magasin", "En attente Comptable", "En attente DFC",
                      "En attente Achats & Stock", "En attente Signature Salarié",
                      "En attente Resp. Stagiaires", "En attente Chef de Service",
                      "En attente du Supérieur Immédiat")
    modules = {
        "Demandes d'achat": _count_waiting("Demande Achat KYA", waiting_states),
        "Permissions sortie": (_count_waiting("Permission Sortie Employe", waiting_states)
                                + _count_waiting("Permission Sortie Stagiaire", waiting_states)),
        "Plannings congé": _count_waiting("Planning Conge", waiting_states),
        "PV matériel": (_count_waiting("PV Sortie Materiel", waiting_states)
                        + _count_waiting("PV Entree Materiel", waiting_states)),
        "Inventaires": _count_waiting("Inventaire KYA", waiting_states),
        "Brouillards caisse": _count_waiting("Brouillard Caisse", waiting_states),
        "Contrats": _count_waiting("KYA Contrat", waiting_states),
    }
    modules_total = sum(modules.values())

    # ── Graphes Chart.js (toutes données réelles) ──
    import json as _json

    # 1. Présence par département (barres empilées)
    presence_chart = {
        "labels": [d.get("dept") or "—" for d in departements],
        "presents": [int(d.get("presents") or 0) for d in departements],
        "absents": [int(d.get("absents") or 0) for d in departements],
        "conges": [int(d.get("conges") or 0) for d in departements],
    }

    # 2. Workflows par statut (camembert) : agrège les états sur les doctypes clés
    wf_doctypes = ["Demande Achat KYA", "Permission Sortie Employe",
                   "Permission Sortie Stagiaire", "Planning Conge",
                   "PV Sortie Materiel", "PV Entree Materiel", "Inventaire KYA",
                   "Brouillard Caisse", "Leave Application", "KYA Contrat"]
    wf_counts = {"En attente": 0, "Approuvé": 0, "Rejeté": 0, "Brouillon": 0}
    for dt in wf_doctypes:
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            rows = frappe.db.sql(
                f"SELECT workflow_state, COUNT(*) n FROM `tab{dt}` GROUP BY workflow_state",
                as_dict=True)
            for r in rows:
                st = (r.workflow_state or "").lower()
                if "attente" in st:
                    wf_counts["En attente"] += r.n
                elif "approuv" in st or "valid" in st or "archiv" in st:
                    wf_counts["Approuvé"] += r.n
                elif "rejet" in st or "annul" in st:
                    wf_counts["Rejeté"] += r.n
                else:
                    wf_counts["Brouillon"] += r.n
        except Exception:
            pass

    # 3. Évolution caisse 6 derniers mois (entrées vs sorties) — réel
    caisse_chart = {"labels": [], "entrees": [], "sorties": []}
    try:
        rows = frappe.db.sql(
            """
            SELECT CONCAT(YEAR(date_brouillard), '-', LPAD(MONTH(date_brouillard), 2, '0')) AS mois,
                   SUM(total_entrees) AS ent, SUM(total_sorties) AS sor
            FROM `tabBrouillard Caisse`
            WHERE date_brouillard >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY mois ORDER BY mois
            """, as_dict=True)
        for r in rows:
            caisse_chart["labels"].append(r.mois or "")
            caisse_chart["entrees"].append(float(r.ent or 0))
            caisse_chart["sorties"].append(float(r.sor or 0))
    except Exception:
        pass

    # ── Services transverses (kya_services) : enquêtes, évaluations, tâches ──
    # Vue synthétique des flux du module Services (formulaires de satisfaction,
    # évaluations, tâches d'équipe) avec leur TAUX DE LIVRAISON (soumis/total).
    services = {
        "forms_actifs": 0, "form_invites": 0, "form_soumis": 0, "form_attente": 0,
        "form_taux": 0,
        "evals_total": 0, "evals_soumis": 0, "evals_attente": 0, "evals_taux": 0,
        "taches_total": 0, "taches_en_cours": 0, "taches_terminees": 0,
        "plans_trimestriels": 0,
    }
    try:
        if frappe.db.exists("DocType", "KYA Form"):
            services["forms_actifs"] = frappe.db.count("KYA Form", {"statut": "Actif"})
        if frappe.db.exists("DocType", "KYA Form Response"):
            services["form_invites"] = frappe.db.count("KYA Form Response")
            services["form_soumis"] = frappe.db.sql(
                "SELECT COUNT(*) FROM `tabKYA Form Response` WHERE soumis_le IS NOT NULL AND soumis_le != ''"
            )[0][0] or 0
            services["form_attente"] = max(0, services["form_invites"] - services["form_soumis"])
            if services["form_invites"]:
                services["form_taux"] = round(services["form_soumis"] / services["form_invites"] * 100, 1)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: kya forms")
    try:
        if frappe.db.exists("DocType", "KYA Evaluation"):
            services["evals_total"] = frappe.db.count("KYA Evaluation")
            services["evals_soumis"] = frappe.db.sql(
                "SELECT COUNT(*) FROM `tabKYA Evaluation` WHERE soumis_le IS NOT NULL AND soumis_le != ''"
            )[0][0] or 0
            services["evals_attente"] = max(0, services["evals_total"] - services["evals_soumis"])
            if services["evals_total"]:
                services["evals_taux"] = round(services["evals_soumis"] / services["evals_total"] * 100, 1)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: kya evals")
    try:
        if frappe.db.exists("DocType", "Tache Equipe"):
            services["taches_total"] = frappe.db.count("Tache Equipe")
            services["taches_terminees"] = frappe.db.count("Tache Equipe", {"statut": ["like", "%ermin%"]})
            services["taches_en_cours"] = max(0, services["taches_total"] - services["taches_terminees"])
        if frappe.db.exists("DocType", "Plan Trimestriel"):
            services["plans_trimestriels"] = frappe.db.count("Plan Trimestriel")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: kya taches")

    context.services = services

    # ── Intégrations externes : visiteurs (KYA Guest Visit) + réunions ──
    # DocTypes custom alimentés par les apps des collègues (peuvent être absents).
    integrations = {
        "guest_actif": False, "visites_jour": 0, "visites_en_cours": 0, "visites_semaine": 0,
        "meeting_actif": False, "reunions_actives": 0, "reunions_semaine": 0, "presences_semaine": 0,
    }
    try:
        if frappe.db.exists("DocType", "KYA Guest Visit"):
            integrations["guest_actif"] = True
            integrations["visites_jour"] = frappe.db.sql(
                "SELECT COUNT(*) FROM `tabKYA Guest Visit` WHERE DATE(check_in)=CURDATE()")[0][0] or 0
            integrations["visites_en_cours"] = frappe.db.count("KYA Guest Visit", {"statut": "En cours"})
            integrations["visites_semaine"] = frappe.db.sql(
                "SELECT COUNT(*) FROM `tabKYA Guest Visit` WHERE check_in >= %s", (week_ago,))[0][0] or 0
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: guest visits")
    try:
        # Réunions : doctypes réels (app, alimentés par kya_hr.api.kya_reunion.sync_meeting)
        if frappe.db.exists("DocType", "KYA Reunion Meeting"):
            integrations["meeting_actif"] = True
            integrations["reunions_actives"] = frappe.db.count("KYA Reunion Meeting", {"status": "active"})
            integrations["reunions_semaine"] = frappe.db.sql(
                "SELECT COUNT(*) FROM `tabKYA Reunion Meeting` WHERE start_at >= %s", (week_ago,))[0][0] or 0
        if frappe.db.exists("DocType", "KYA Reunion Presence"):
            integrations["presences_semaine"] = frappe.db.sql(
                "SELECT COUNT(*) FROM `tabKYA Reunion Presence` WHERE creation >= %s", (week_ago,))[0][0] or 0
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: meetings")

    context.integrations = integrations
    context.stats = stats
    context.demandes_dg = demandes_dg
    context.brouillards = brouillards
    context.plannings_attente = plannings_attente
    context.departements = departements
    context.equipes = equipes
    context.modules = modules
    context.modules_total = modules_total
    context.presence_chart_json = _json.dumps(presence_chart)
    context.wf_chart_json = _json.dumps(wf_counts)
    context.caisse_chart_json = _json.dumps(caisse_chart)
    context.no_breadcrumbs = True

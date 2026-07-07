"""Page : Vue d'ensemble Services Supports (DSS).

Route : /services-supports-dashboard

Vue consolidée du macro-département Services Supports — les 4 fonctions
support de KYA réunies sur un seul écran, avec graphiques parlants :
  • Ressources Humaines (effectif, présence, congés, permissions) ;
  • Comptabilité & Finance (trésorerie caisse, brouillards) ;
  • Achats & Stocks (demandes, bons de commande, marchés) ;
  • Logistique (flotte, sorties véhicule, entretiens).

Même pattern que les autres dashboards départementaux (hero + bandes +
tables + Chart.js), libellés FR neutres, données réelles, défensif :
chaque doctype peut être absent (local) → dégrade à 0 sans casser.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, today, add_days, formatdate

no_cache = 1

ACCESS_ROLES = {
    "System Manager", "Directeur General", "Directeur Général", "DG", "DGA",
    "DAAF", "DFC", "Responsable Comptable", "Accounts Manager", "Accounts User",
    "Comptable", "Caissier",
    "Responsable Achats", "Chef Service Achats", "Purchase Manager", "Purchase User",
    "Chargé des Stocks", "Responsable Stock", "Magasinier", "Stock Manager", "Stock User",
    "Responsable Logistique", "Gestionnaire de Flotte", "Fleet Manager", "Logisticien",
    "Responsable RH", "HR Manager", "HR User",
    "Auditeur Interne", "Auditeur", "Chef Service",
}


# ── Helpers défensifs ──────────────────────────────────────────────
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


def _fmt_m(xof: float) -> str:
    """Montant XOF -> 'X,Y' millions (virgule décimale FR, 0 si quasi nul)."""
    m = (xof or 0) / 1_000_000.0
    if abs(m) < 0.05:
        m = 0.0
    return f"{m:,.1f}".replace(",", " ").replace(".", ",")


# Détection des équipes « supports » (mêmes clés que le dashboard DG).
_SUPPORTS_KW = ("achat", "stock", "compt", "financ", "rh", "ressources humaines",
                "logist", "dispatch", "approvision", "magasin", "flotte")
_SUPPORTS_NAMES = {
    "equipe achats et stocks", "equipe comptabilité et finance",
    "equipe comptabilite et finance", "equipe rh",
    "logistique", "logistique et flotte",
}


def _is_supports(equipe: str | None, dept: str | None) -> bool:
    key = (equipe or "").strip().lower()
    if key in _SUPPORTS_NAMES:
        return True
    blob = f"{key} {(dept or '').lower()}"
    return any(k in blob for k in _SUPPORTS_KW)


_WAIT_STATES = ("En attente Chef", "En attente DAAF", "En attente DG",
                "En attente Direction", "En attente RH", "En attente Audit",
                "En attente Magasin", "En attente Comptable", "En attente DFC",
                "En attente Achats & Stock", "En attente Signature Salarié",
                "En attente Resp. Stagiaires", "En attente Chef de Service",
                "En attente du Supérieur Immédiat", "En attente Signature")

# Doctypes du périmètre supports (pour les compteurs « en attente » + camembert).
_SUPPORTS_DT = ("Demande Achat KYA", "Bon Commande KYA", "PV Sortie Materiel",
                "PV Entree Materiel", "PV Retour Materiel", "Inventaire KYA",
                "Brouillard Caisse", "Planning Conge", "Permission Sortie Employe",
                "Permission Sortie Stagiaire")


def _card(label, value, sub="", unit="", icon="layers", accent="slate"):
    return {"label": label, "value": value, "sub": sub, "unit": unit,
            "icon": icon, "accent": accent}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/services-supports-dashboard"
        raise frappe.Redirect
    if not (set(frappe.get_roles(user)) & ACCESS_ROLES):
        frappe.throw(_("Accès réservé aux Services Supports et à la Direction."),
                     frappe.PermissionError)

    context.page_title = "Vue d'ensemble — Services Supports"
    context.no_cache = 1
    context.no_breadcrumbs = True
    try:
        import json as _json
        context.overview_json = _json.dumps(get_ss_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "services-supports-dashboard: overview")
    return context


@frappe.whitelist()
def get_ss_overview() -> dict:
    """Indicateurs consolidés Services Supports (RH, Compta, Achats, Logistique)."""
    if not (set(frappe.get_roles(frappe.session.user)) & ACCESS_ROLES):
        frappe.throw(_("Accès réservé."), frappe.PermissionError)

    week_ago = add_days(today(), -7)
    month_ago = add_days(today(), -30)

    # ── Équipes supports : effectif + présence du jour ──
    teams = []
    try:
        rows = frappe.db.sql(
            """
            SELECT eq.name AS equipe, eq.nom_equipe AS nom, eq.departement AS dept,
                   eq.chef_equipe_name AS chef,
                   COUNT(DISTINCT e.name) AS eff,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS pres,
                   SUM(CASE WHEN a.status IN ('On Leave','Half Day') THEN 1 ELSE 0 END) AS conges
            FROM `tabEquipe KYA` eq
            LEFT JOIN `tabEmployee` e
                ON e.custom_kya_equipe = eq.name AND e.status='Active'
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = CURDATE()
            GROUP BY eq.name, eq.nom_equipe, eq.departement, eq.chef_equipe_name
            ORDER BY eff DESC
            """, as_dict=True)
        for r in rows:
            if not _is_supports(r.nom or r.equipe, r.dept):
                continue
            eff = int(r.eff or 0)
            pres = int(r.pres or 0)
            teams.append({
                "equipe": r.nom or r.equipe, "chef": r.chef or "—",
                "eff": eff, "pres": pres, "conges": int(r.conges or 0),
                "charge": round(pres / eff * 100) if eff else 0,
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ss-overview: equipes")

    sup_eff = sum(t["eff"] for t in teams)
    sup_pres = sum(t["pres"] for t in teams)
    sup_conges = sum(t["conges"] for t in teams)

    # ── Compteurs « en attente » du périmètre supports ──
    wait = {dt: _waiting(dt, _WAIT_STATES) for dt in _SUPPORTS_DT}
    wait_total = sum(wait.values())

    da_n = _waiting("Demande Achat KYA", _WAIT_STATES)
    da_m = _sum("Demande Achat KYA", "montant_total", {"workflow_state": ["in", _WAIT_STATES]})
    pv_wait = (wait["PV Sortie Materiel"] + wait["PV Entree Materiel"] + wait["PV Retour Materiel"])

    # Trésorerie caisse
    ent_sem = _sum("Brouillard Caisse", "total_entrees", {"date_brouillard": [">=", week_ago]})
    sor_sem = _sum("Brouillard Caisse", "total_sorties", {"date_brouillard": [">=", week_ago]})
    solde = _sum("Brouillard Caisse", "total_entrees") - _sum("Brouillard Caisse", "total_sorties")

    # Flotte
    veh_total = _count("Vehicle")
    veh_dispo = _count("Vehicle", {"kya_statut": "Disponible"})

    # ════════ HERO (6) ════════
    hero = [
        _card("Effectif supports", str(sup_eff),
              (f"{sup_pres} présents aujourd'hui" if sup_eff else "—"), icon="users"),
        _card("En attente de visa", str(wait_total), "RH · Achats & Stocks · Logistique · Compta",
              unit="dossiers", icon="inbox"),
        _card("Demandes d'achat à valider", str(da_n), _fmt_m(da_m) + " M FCFA",
              icon="cart"),
        _card("Brouillards à clôturer", str(_count("Brouillard Caisse",
              {"date_brouillard": [">=", week_ago]})), "cette semaine", icon="receipt"),
        _card("Solde caisse", _fmt_m(solde), "cumulé", unit="M FCFA", icon="coins"),
        _card("Véhicules disponibles", str(veh_dispo), f"sur {veh_total} au parc",
              icon="truck"),
    ]

    # ════════ RH ════════
    conges_attente = _waiting("Planning Conge", _WAIT_STATES) or _count("Leave Application",
                              {"status": "Open"})
    perms_attente = (_waiting("Permission Sortie Employe", _WAIT_STATES)
                     + _waiting("Permission Sortie Stagiaire", _WAIT_STATES))
    rh_cards = [
        _card("Effectif supports", str(sup_eff), "employés actifs", icon="users", accent="teal"),
        _card("Présents aujourd'hui", str(sup_pres),
              (f"{round(sup_pres / sup_eff * 100)} % de l'effectif" if sup_eff else "—"),
              icon="usercheck", accent="green"),
        _card("Congés à valider", str(conges_attente), "plannings en attente",
              icon="calendar", accent="orange"),
        _card("Permissions à valider", str(perms_attente), "sorties en attente",
              icon="clock", accent="teal"),
    ]

    # ════════ ACHATS ════════
    achats_cards = [
        _card("Demandes d'achat en attente", str(da_n), _fmt_m(da_m) + " M FCFA",
              icon="cart", accent="orange"),
        _card("Bons de commande en attente", str(_waiting("Bon Commande KYA", _WAIT_STATES)),
              "", icon="file", accent="teal"),
        _card("Appels d'offres", str(_count("Appel Offre KYA")), "ouverts", icon="file", accent="slate"),
        _card("Marchés", str(_count("Marche KYA")), "suivis", icon="briefcase", accent="teal"),
    ]
    achats_rows = []
    if _dt_exists("Demande Achat KYA"):
        try:
            for d in frappe.get_all("Demande Achat KYA",
                    filters=[["workflow_state", "in", _WAIT_STATES]],
                    fields=["name", "objet", "montant_total", "employee_name",
                            "workflow_state", "modified"],
                    order_by="modified desc", limit_page_length=8):
                achats_rows.append({
                    "ref": d.name, "objet": d.objet or "—",
                    "demandeur": d.employee_name or "—",
                    "montant": _fmt_m(d.montant_total) + " M",
                    "etat": d.workflow_state or "—", "accent": "wait",
                })
        except Exception:
            frappe.log_error(frappe.get_traceback(), "ss-overview: demandes achat")

    # ════════ COMPTABILITÉ ════════
    compta_cards = [
        _card("Brouillards (semaine)", str(_count("Brouillard Caisse",
              {"date_brouillard": [">=", week_ago]})), "à clôturer", icon="receipt", accent="teal"),
        _card("Entrées (semaine)", _fmt_m(ent_sem), "encaissements", unit="M FCFA",
              icon="arrowup", accent="green"),
        _card("Sorties (semaine)", _fmt_m(sor_sem), "décaissements", unit="M FCFA",
              icon="arrowdown", accent="orange"),
        _card("Solde caisse", _fmt_m(solde), "cumulé", unit="M FCFA", icon="coins", accent="teal"),
    ]
    compta_rows = []
    if _dt_exists("Brouillard Caisse"):
        try:
            for b in frappe.get_all("Brouillard Caisse",
                    filters=[["date_brouillard", ">=", month_ago]],
                    fields=["name", "date_brouillard", "caissiere_name", "total_entrees",
                            "total_sorties", "solde_final", "workflow_state"],
                    order_by="date_brouillard desc", limit_page_length=8):
                st = (b.workflow_state or "").lower()
                compta_rows.append({
                    "ref": b.name,
                    "date": formatdate(b.date_brouillard, "dd/MM/y") if b.date_brouillard else "—",
                    "saisi_par": b.caissiere_name or "—",
                    "entrees": _fmt_m(b.total_entrees) + " M",
                    "sorties": _fmt_m(b.total_sorties) + " M",
                    "solde": _fmt_m(b.solde_final) + " M",
                    "etat": b.workflow_state or "—",
                    "accent": ("ok" if any(k in st for k in ("clôtur", "clotur", "valid", "approuv"))
                               else "wait"),
                })
        except Exception:
            frappe.log_error(frappe.get_traceback(), "ss-overview: brouillards")

    # ════════ STOCK & LOGISTIQUE ════════
    pleins_mois = _count("Plein Carburant KYA", {"creation": [">=", month_ago]})
    entretiens = _count("Entretien Vehicule KYA")
    logi_cards = [
        _card("Mouvements matériel en attente", str(pv_wait), "PV entrée/sortie/retour",
              icon="package", accent="orange"),
        _card("Inventaires en attente", str(_waiting("Inventaire KYA", _WAIT_STATES)),
              "", icon="filecheck", accent="teal"),
        _card("Pleins de carburant (mois)", str(pleins_mois), "30 derniers jours",
              icon="droplet", accent="teal"),
        _card("Entretiens véhicules", str(entretiens), "enregistrés", icon="wrench", accent="slate"),
    ]
    veh_rows = []
    if _dt_exists("Vehicle"):
        try:
            for v in frappe.get_all("Vehicle",
                    fields=["name", "license_plate", "make", "model",
                            "kya_statut", "kya_chauffeur_principal"],
                    order_by="kya_statut asc", limit_page_length=12):
                st = (v.kya_statut or "").lower()
                accent = ("ok" if "disponible" in st else
                          "wait" if "mission" in st else
                          "warn" if "entretien" in st else
                          "bad" if "hors" in st else "slate")
                veh_rows.append({
                    "immat": v.license_plate or v.name,
                    "modele": " ".join(x for x in (v.make, v.model) if x) or "—",
                    "statut": v.kya_statut or "—",
                    "chauffeur": v.kya_chauffeur_principal or "—",
                    "accent": accent,
                })
        except Exception:
            frappe.log_error(frappe.get_traceback(), "ss-overview: vehicules")

    # ════════ CHARTS ════════
    # 1. Workflows supports par état (camembert)
    wf = {"En attente": 0, "Approuvé": 0, "Rejeté": 0, "Brouillon": 0}
    for dt in _SUPPORTS_DT:
        if not _dt_exists(dt):
            continue
        try:
            for r in frappe.db.sql(f"SELECT workflow_state ws, COUNT(*) n FROM `tab{dt}` GROUP BY ws",
                                   as_dict=True):
                s = (r.ws or "").lower()
                if "attente" in s:
                    wf["En attente"] += r.n
                elif any(k in s for k in ("approuv", "valid", "archiv", "signé", "signe",
                                          "clôtur", "clotur")):
                    wf["Approuvé"] += r.n
                elif any(k in s for k in ("rejet", "annul", "refus")):
                    wf["Rejeté"] += r.n
                else:
                    wf["Brouillon"] += r.n
        except Exception:
            pass
    workflows = {"labels": list(wf.keys()), "data": list(wf.values())}

    # 2. Trésorerie caisse 6 derniers mois (entrées vs sorties, en millions)
    caisse = {"labels": [], "entrees": [], "sorties": []}
    if _dt_exists("Brouillard Caisse"):
        try:
            for r in frappe.db.sql(
                """SELECT CONCAT(YEAR(date_brouillard),'-',LPAD(MONTH(date_brouillard),2,'0')) mois,
                          SUM(total_entrees) ent, SUM(total_sorties) sor
                   FROM `tabBrouillard Caisse`
                   WHERE date_brouillard >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                   GROUP BY mois ORDER BY mois""", as_dict=True):
                caisse["labels"].append(r.mois or "")
                caisse["entrees"].append(round(flt(r.ent) / 1_000_000, 2))
                caisse["sorties"].append(round(flt(r.sor) / 1_000_000, 2))
        except Exception:
            pass

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero,
        "rh": {"cards": rh_cards, "teams": teams},
        "achats": {"cards": achats_cards, "rows": achats_rows},
        "compta": {"cards": compta_cards, "rows": compta_rows},
        "logistique": {"cards": logi_cards, "vehicules": veh_rows},
        "charts": {"workflows": workflows, "caisse": caisse},
        "rh_label": f"{sup_eff} employés · {sup_pres} présents",
        "achats_label": f"{da_n} en attente",
        "compta_label": _fmt_m(solde) + " M FCFA de solde",
        "logi_label": f"{veh_dispo}/{veh_total} véhicules dispo",
        "wait_total": wait_total,
    }

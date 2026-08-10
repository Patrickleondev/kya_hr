"""Page : Dashboard Stocks Generalise KYA.

Route : /kya-stocks-dashboard
"""
from __future__ import annotations

import frappe


STOCK_ACCESS_ROLES = {
    "Chargé des Stocks", "Responsable Stock", "Magasinier",
    "Stock User", "Stock Manager", "System Manager",
    "Directeur Général", "Directeur General", "DG", "DGA",
    "Responsable RH", "Chef Service", "Chef Service Achats",
    "Responsable Achats", "Auditeur Interne", "Auditeur",
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/kya-stocks-dashboard"
        raise frappe.Redirect

    user_roles = set(frappe.get_roles(user))
    if not (user_roles & STOCK_ACCESS_ROLES):
        frappe.throw(
            "Acces refuse - vous devez avoir un role Stock (Stock User, "
            "Stock Manager, Auditeur, DG, DGA, Responsable RH, ou Chef Service Achats).",
            frappe.PermissionError,
        )

    # Listes pour les filtres
    context.item_groups = frappe.db.sql_list(
        "SELECT name FROM `tabItem Group` WHERE is_group=0 ORDER BY name"
    )
    context.warehouses = frappe.db.sql_list(
        "SELECT name FROM `tabWarehouse` WHERE disabled=0 AND is_group=0 ORDER BY name"
    )

    context.page_title = "Dashboard Stocks KYA"
    context.no_cache = 1
    context.no_breadcrumbs = True
    try:
        import json as _json
        context.overview_json = _json.dumps(get_stock_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "stocks-dashboard: overview")
    return context


# ════════════════════════════════════════════════════════════════════
#  Vue d'ensemble Stock (maquette boards/Dashboard Stocks) — données réelles
# ════════════════════════════════════════════════════════════════════
def _exists(dt):
    try:
        return bool(frappe.db.exists("DocType", dt))
    except Exception:
        return False


def _count(dt, filters=None):
    if not _exists(dt):
        return 0
    try:
        f = dict(filters or {})
        f.setdefault("docstatus", ["!=", 2])
        return frappe.db.count(dt, f)
    except Exception:
        return 0


def _fmt_m(xof):
    m = (xof or 0) / 1_000_000.0
    if abs(m) < 0.05:
        m = 0.0
    return f"{m:,.1f}".replace(",", " ").replace(".", ",")


@frappe.whitelist()
def get_stock_overview() -> dict:
    """Indicateurs Stock & Inventaire — branchés sur le JOURNAL DE STOCK MAISON
    (Mouvement Stock KYA), plus ERPNext Bin/SLE. Unités (pas de valorisation)."""
    if not (set(frappe.get_roles(frappe.session.user)) & STOCK_ACCESS_ROLES):
        frappe.throw("Accès réservé au magasin et à la Direction.", frappe.PermissionError)

    from frappe.utils import add_days, today, formatdate
    from kya_hr.api import stock_kya

    # ── Soldes calculés depuis le journal ──
    try:
        soldes = stock_kya.soldes(only_nonzero=1)
    except Exception:
        soldes = []
    nb_refs = len({d["item"] for d in soldes})
    nb_mag = len({d["magasin"] for d in soldes})
    total_unites = round(sum(d["total"] for d in soldes), 2)
    nb_reparation = sum(1 for d in soldes if d["reparation"] > 0)
    nb_rupture = sum(1 for d in soldes if d["total"] <= 0)

    # Alertes réappro (mêmes règles que le cockpit : dispo = bon état,
    # seuils par catégorie du responsable stock pris en compte).
    alertes = {"ruptures": 0, "a_commander": 0, "defectueux_refs": 0}
    try:
        cats = {a["name"]: (a.get("categorie") or "Non classé")
                for a in frappe.get_all("Article KYA", fields=["name", "categorie"])}
        for d in soldes:
            ev = stock_kya.evaluer_ligne(d["bon_etat"], d["reparation"],
                                         d.get("defectueux", 0),
                                         categorie=cats.get(d["item"], "Non classé"))
            if ev["statut"] == "RUPTURE":
                alertes["ruptures"] += 1
            elif ev["statut"] == "A COMMANDER":
                alertes["a_commander"] += 1
            if d.get("defectueux", 0) > 0:
                alertes["defectueux_refs"] += 1
    except Exception:
        frappe.log_error(frappe.get_traceback(), "stock-overview: alertes")

    month_start = today()[:8] + "01"
    six_m = add_days(today(), -180)

    hero = [
        {"label": "Unités en stock", "value": f"{total_unites:g}", "unit": "u.",
         "sub": f"{nb_refs} articles · {nb_mag} magasins", "icon": "coins"},
        {"label": "Articles en réparation", "value": str(nb_reparation), "sub": "immobilisés", "icon": "alert"},
        {"label": "PV d'entrée (mois)", "value": str(_count("PV Entree Materiel", {"creation": [">=", month_start]})),
         "sub": "matériel reçu", "icon": "arrowdown"},
        {"label": "PV de sortie (mois)", "value": str(_count("PV Sortie Materiel", {"creation": [">=", month_start]})),
         "sub": "vers chantiers", "icon": "arrowup"},
        {"label": "Retours matériel", "value": str(_count("Retour Materiel KYA",
         {"workflow_state": ["in", ("Brouillon", "En attente Magasin")]})), "sub": "à traiter", "icon": "undo"},
        {"label": "Inventaires en cours", "value": str(_count("Inventaire KYA",
         {"workflow_state": ["not in", ("Approuvé", "Rejeté")]})), "sub": "magasin", "icon": "clipboard"},
    ]

    doc_cards = [
        {"label": "PV Entrée Matériel", "value": str(_count("PV Entree Materiel", {"creation": [">=", month_start]})),
         "sub": "ce mois", "icon": "arrowdown", "accent": "green"},
        {"label": "PV Sortie Matériel", "value": str(_count("PV Sortie Materiel", {"creation": [">=", month_start]})),
         "sub": "ce mois", "icon": "arrowup", "accent": "orange"},
        {"label": "Retour Matériel", "value": str(_count("Retour Materiel KYA",
         {"workflow_state": ["in", ("Brouillon", "En attente Magasin")]})), "sub": "en attente", "icon": "undo", "accent": "teal"},
        {"label": "Inventaire", "value": str(_count("Inventaire KYA",
         {"workflow_state": ["not in", ("Approuvé", "Rejeté")]})), "sub": "en cours", "icon": "clipboard", "accent": "teal"},
        {"label": "Mouvements (mois)", "value": str(_count("Mouvement Stock KYA", {"date_mouvement": [">=", month_start]})),
         "sub": "journal de stock", "icon": "receipt", "accent": "slate"},
    ]

    # ── Derniers mouvements (journal maison) ──
    mouvements = []
    try:
        rows = frappe.db.sql(
            """SELECT item_name, magasin, type_mouvement, quantite, date_mouvement,
                      reference_name, owner
               FROM `tabMouvement Stock KYA`
               ORDER BY creation DESC LIMIT 12""", as_dict=True)
        for r in rows:
            qty = float(r.quantite or 0)
            mouvements.append({
                "type": r.type_mouvement or ("Entrée" if qty > 0 else "Sortie"),
                "accent": "green" if qty > 0 else "orange",
                "ref": r.reference_name or "", "article": r.item_name or "",
                "qte": ("+" if qty > 0 else "") + (f"{qty:g}"),
                "date": formatdate(r.date_mouvement, "dd/MM") if r.date_mouvement else "",
                "par": frappe.utils.get_fullname(r.owner) if r.owner else "",
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "stock-overview: mouvements")

    # ── Top articles par quantité en stock ──
    top = []
    tot_q = sum(d["total"] for d in soldes) or 1
    for d in sorted(soldes, key=lambda x: x["total"], reverse=True)[:8]:
        grp = frappe.db.get_value("Article KYA", d["item"], "categorie") \
            or frappe.db.get_value("Item", d["item"], "item_group") or "—"
        top.append({
            "article": d["item_name"], "cat": grp,
            "qte": f"{d['total']:g}",
            "valeur": f"{d['bon_etat']:g} bon / {d['reparation']:g} rép.",
            "part": round(d["total"] / tot_q * 100),
        })

    # ── Flux entrées/sorties 6 mois (unités) ──
    flux = {"labels": [], "entrees": [], "sorties": []}
    try:
        rows = frappe.db.sql(
            """SELECT CONCAT(YEAR(date_mouvement),'-',LPAD(MONTH(date_mouvement),2,'0')) mois,
                      SUM(CASE WHEN quantite>0 THEN quantite ELSE 0 END) ent,
                      SUM(CASE WHEN quantite<0 THEN -quantite ELSE 0 END) sor
               FROM `tabMouvement Stock KYA`
               WHERE date_mouvement >= %s
               GROUP BY mois ORDER BY mois""", (six_m,), as_dict=True)
        for r in rows:
            flux["labels"].append(r.mois or "")
            flux["entrees"].append(round(float(r.ent or 0), 2))
            flux["sorties"].append(round(float(r.sor or 0), 2))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "stock-overview: flux")

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "doc_cards": doc_cards, "mouvements": mouvements,
        "top": top, "flux": flux, "alertes": alertes,
        "valeur_stock_label": f"{total_unites:g} unités",
    }

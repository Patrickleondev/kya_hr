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
        return frappe.db.count(dt, filters or {})
    except Exception:
        return 0


def _fmt_m(xof):
    m = (xof or 0) / 1_000_000.0
    if abs(m) < 0.05:
        m = 0.0
    return f"{m:,.1f}".replace(",", " ").replace(".", ",")


@frappe.whitelist()
def get_stock_overview() -> dict:
    """Indicateurs Stock & Inventaire (valeur, ruptures, documents, mouvements,
    top articles, flux 6 mois). Tout est réel ; défensif si doctype absent."""
    if not (set(frappe.get_roles(frappe.session.user)) & STOCK_ACCESS_ROLES):
        frappe.throw("Accès réservé au magasin et à la Direction.", frappe.PermissionError)

    from frappe.utils import add_days, today, formatdate

    # ── Valeur totale du stock + nb références ──
    val_rows = frappe.db.sql(
        "SELECT COALESCE(SUM(actual_qty*valuation_rate),0) v, "
        "COUNT(DISTINCT item_code) n FROM `tabBin` WHERE actual_qty != 0", as_dict=True)
    valeur_stock = float(val_rows[0].v or 0) if val_rows else 0
    nb_refs = int(val_rows[0].n or 0) if val_rows else 0

    # ── Ruptures (stock total <= 0) + critiques (sous le seuil de réappro) ──
    rupt = frappe.db.sql(
        """SELECT COUNT(*) n FROM (
              SELECT b.item_code, SUM(b.actual_qty) q
              FROM `tabBin` b GROUP BY b.item_code HAVING q <= 0
           ) t""", as_dict=True)
    nb_rupture = int(rupt[0].n or 0) if rupt else 0

    month_start = today()[:8] + "01"
    d48 = add_days(today(), -2)
    six_m = add_days(today(), -180)

    # ── Hero ──
    hero = [
        {"label": "Valeur totale du stock", "value": _fmt_m(valeur_stock), "unit": "M FCFA",
         "sub": f"{nb_refs} références", "icon": "coins"},
        {"label": "Articles en rupture", "value": str(nb_rupture), "sub": "stock épuisé", "icon": "alert"},
        {"label": "PV d'entrée (mois)", "value": str(_count("PV Entree Materiel", {"creation": [">=", month_start]})),
         "sub": "matériel reçu", "icon": "arrowdown"},
        {"label": "PV de sortie (mois)", "value": str(_count("PV Sortie Materiel", {"creation": [">=", month_start]})),
         "sub": "vers chantiers", "icon": "arrowup"},
        {"label": "Retours matériel", "value": str(_count("Retour Materiel KYA",
         {"workflow_state": ["in", ("Brouillon", "En attente Magasin")]})), "sub": "à traiter", "icon": "undo"},
        {"label": "Inventaires en cours", "value": str(_count("Inventaire KYA",
         {"workflow_state": ["not in", ("Approuvé", "Rejeté")]})), "sub": "magasin", "icon": "clipboard"},
    ]

    # ── Documents de stock ──
    doc_cards = [
        {"label": "PV Entrée Matériel", "value": str(_count("PV Entree Materiel", {"creation": [">=", month_start]})),
         "sub": "ce mois", "icon": "arrowdown", "accent": "green"},
        {"label": "PV Sortie Matériel", "value": str(_count("PV Sortie Materiel", {"creation": [">=", month_start]})),
         "sub": "ce mois", "icon": "arrowup", "accent": "orange"},
        {"label": "Retour Matériel", "value": str(_count("Retour Materiel KYA",
         {"workflow_state": ["in", ("Brouillon", "En attente Magasin")]})), "sub": "en attente", "icon": "undo", "accent": "teal"},
        {"label": "Inventaire", "value": str(_count("Inventaire KYA",
         {"workflow_state": ["not in", ("Approuvé", "Rejeté")]})), "sub": "en cours", "icon": "clipboard", "accent": "teal"},
        {"label": "Réceptions (Material Receipt)", "value": str(_count("Stock Entry",
         {"stock_entry_type": "Material Receipt", "creation": [">=", month_start], "docstatus": 1})),
         "sub": "ce mois", "icon": "receipt", "accent": "slate"},
    ]

    # ── Derniers mouvements (Stock Ledger Entry, ~7 jours) ──
    mouvements = []
    try:
        rows = frappe.db.sql(
            """SELECT sle.item_code, it.item_name, sle.warehouse, sle.actual_qty,
                      sle.posting_date, sle.voucher_type, sle.voucher_no, sle.owner
               FROM `tabStock Ledger Entry` sle
               INNER JOIN `tabItem` it ON it.name = sle.item_code
               WHERE sle.is_cancelled = 0 AND sle.posting_date >= %s
               ORDER BY sle.posting_date DESC, sle.creation DESC LIMIT 12""",
            (add_days(today(), -7),), as_dict=True)
        for r in rows:
            qty = float(r.actual_qty or 0)
            mouvements.append({
                "type": "Entrée" if qty > 0 else "Sortie",
                "accent": "green" if qty > 0 else "orange",
                "ref": r.voucher_no or "", "article": r.item_name or r.item_code,
                "qte": ("+" if qty > 0 else "") + (f"{qty:g}"),
                "date": formatdate(r.posting_date, "dd/MM"),
                "par": frappe.utils.get_fullname(r.owner) if r.owner else "",
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "stock-overview: mouvements")

    # ── Top articles par valeur ──
    top = []
    try:
        rows = frappe.db.sql(
            """SELECT b.item_code, it.item_name, it.item_group, it.stock_uom,
                      SUM(b.actual_qty) qte, SUM(b.actual_qty*b.valuation_rate) val
               FROM `tabBin` b INNER JOIN `tabItem` it ON it.name = b.item_code
               WHERE b.actual_qty != 0
               GROUP BY b.item_code, it.item_name, it.item_group, it.stock_uom
               ORDER BY val DESC LIMIT 8""", as_dict=True)
        tot = sum(float(r.val or 0) for r in rows) or 1
        for r in rows:
            top.append({
                "article": r.item_name or r.item_code, "cat": r.item_group or "—",
                "qte": f"{float(r.qte or 0):g} {r.stock_uom or ''}".strip(),
                "valeur": _fmt_m(r.val) + " M",
                "part": round(float(r.val or 0) / tot * 100),
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "stock-overview: top")

    # ── Flux entrées/sorties 6 mois (valeur, M FCFA) ──
    flux = {"labels": [], "entrees": [], "sorties": []}
    try:
        rows = frappe.db.sql(
            """SELECT CONCAT(YEAR(posting_date),'-',LPAD(MONTH(posting_date),2,'0')) mois,
                      SUM(CASE WHEN actual_qty>0 THEN actual_qty*valuation_rate ELSE 0 END) ent,
                      SUM(CASE WHEN actual_qty<0 THEN -actual_qty*valuation_rate ELSE 0 END) sor
               FROM `tabStock Ledger Entry`
               WHERE is_cancelled=0 AND posting_date >= %s
               GROUP BY mois ORDER BY mois""", (six_m,), as_dict=True)
        for r in rows:
            flux["labels"].append(r.mois or "")
            flux["entrees"].append(round(float(r.ent or 0) / 1_000_000, 2))
            flux["sorties"].append(round(float(r.sor or 0) / 1_000_000, 2))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "stock-overview: flux")

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "doc_cards": doc_cards, "mouvements": mouvements,
        "top": top, "flux": flux,
        "valeur_stock_label": _fmt_m(valeur_stock) + " M FCFA",
    }

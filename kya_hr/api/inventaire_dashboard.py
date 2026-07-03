# -*- coding: utf-8 -*-
"""API du dashboard Inventaire KYA — stats temps réel + création inline"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, today


@frappe.whitelist()
def get_dashboard_stats(warehouse=None, period="30"):
    """KPIs principaux + données pour graphiques."""
    period = int(period or 30)
    date_from = add_days(today(), -period)

    # Filtre warehouse
    wh_filter = ""
    args = {"date_from": date_from}
    if warehouse:
        wh_filter = "AND warehouse_filter = %(warehouse)s"
        args["warehouse"] = warehouse

    # KPIs
    total_inv = frappe.db.sql(f"""
        SELECT COUNT(*) FROM `tabInventaire KYA`
        WHERE date_inventaire >= %(date_from)s {wh_filter}
        AND docstatus < 2
    """, args)[0][0] or 0

    pending = frappe.db.sql(f"""
        SELECT COUNT(*) FROM `tabInventaire KYA`
        WHERE statut = 'En attente Magasin' {wh_filter}
        AND docstatus < 2
    """, args)[0][0] or 0

    approved = frappe.db.sql(f"""
        SELECT COUNT(*) FROM `tabInventaire KYA`
        WHERE statut = 'Approuvé' AND date_inventaire >= %(date_from)s {wh_filter}
        AND docstatus < 2
    """, args)[0][0] or 0

    valeur_ecart = frappe.db.sql(f"""
        SELECT COALESCE(SUM(valeur_ecart_total), 0) FROM `tabInventaire KYA`
        WHERE date_inventaire >= %(date_from)s {wh_filter}
        AND docstatus < 2
    """, args)[0][0] or 0

    # Évolution sur la période
    evolution = frappe.db.sql(f"""
        SELECT DATE(date_inventaire) AS d,
               COUNT(*) AS cnt,
               COALESCE(SUM(valeur_ecart_total), 0) AS ecart
        FROM `tabInventaire KYA`
        WHERE date_inventaire >= %(date_from)s {wh_filter}
        AND docstatus < 2
        GROUP BY DATE(date_inventaire)
        ORDER BY d
    """, args, as_dict=True)

    # Top articles avec écarts (depuis Stock Reconciliation liée)
    top_ecarts = frappe.db.sql(f"""
        SELECT i.item_code, i.item_name,
               COUNT(*) AS occurrences,
               COALESCE(SUM(i.amount_difference), 0) AS valeur_ecart
        FROM `tabInventaire KYA` inv
        JOIN `tabStock Reconciliation Item` i ON i.parent = inv.stock_reconciliation
        WHERE inv.date_inventaire >= %(date_from)s {wh_filter}
        AND inv.docstatus < 2
        GROUP BY i.item_code
        ORDER BY ABS(COALESCE(SUM(i.amount_difference), 0)) DESC
        LIMIT 10
    """, args, as_dict=True)

    # Inventaires récents
    recents = frappe.db.sql(f"""
        SELECT name, objet, date_inventaire, statut,
               warehouse_filter, total_lignes, lignes_avec_ecart, valeur_ecart_total
        FROM `tabInventaire KYA`
        WHERE 1=1 {wh_filter}
        AND docstatus < 2
        ORDER BY date_inventaire DESC, modified DESC
        LIMIT 15
    """, args, as_dict=True)

    # Répartition par statut
    par_statut = frappe.db.sql(f"""
        SELECT statut, COUNT(*) AS cnt
        FROM `tabInventaire KYA`
        WHERE date_inventaire >= %(date_from)s {wh_filter}
        AND docstatus < 2
        GROUP BY statut
    """, args, as_dict=True)

    # Liste des magasins disponibles
    warehouses = frappe.get_all(
        "Warehouse",
        filters={"disabled": 0, "is_group": 0},
        fields=["name", "warehouse_name"],
        order_by="warehouse_name",
        limit=100,
    )

    mouvements = get_stock_movements(warehouse=warehouse, period=period)

    return {
        "kpis": {
            "total": total_inv,
            "pending": pending,
            "approved": approved,
            "valeur_ecart": flt(valeur_ecart),
            "entrees_qty": mouvements["totals"]["entrees_qty"],
            "sorties_qty": mouvements["totals"]["sorties_qty"],
            "mouvements": mouvements["totals"]["mouvements"],
        },
        "evolution": evolution,
        "top_ecarts": top_ecarts,
        "recents": recents,
        "par_statut": par_statut,
        "warehouses": warehouses,
        "mouvements_stock": mouvements["rows"],
        "currency": "XOF",
    }


@frappe.whitelist()
def create_inventaire(objet, date_inventaire=None, warehouse=None, type_inventaire="Partiel"):
    """Création rapide d'un inventaire depuis le dashboard."""
    if not warehouse:
        frappe.throw(_("Veuillez choisir un magasin pour créer un inventaire depuis le dashboard."))

    user = frappe.session.user
    emp_name = frappe.db.get_value("Employee", {"user_id": user}, "employee_name") or user

    doc = frappe.new_doc("Inventaire KYA")
    doc.objet = objet
    doc.date_inventaire = date_inventaire or today()
    doc.warehouse_filter = warehouse
    doc.type_inventaire = type_inventaire
    doc.responsable_nom = emp_name
    doc.responsable_date = today()
    doc.statut = "Brouillon"

    for row in _get_stock_rows(warehouse):
        doc.append("items", {
            "item_code": row.item_code,
            "designation": row.designation,
            "uom": row.uom,
            "warehouse": row.warehouse,
            "qte_theorique": row.qte_theorique,
            "qte_comptee": row.qte_theorique,
            "valuation_rate": row.valuation_rate,
        })

    if not doc.items:
        frappe.throw(_("Aucun article avec stock positif trouvé dans le magasin {0}.").format(warehouse))

    doc.insert(ignore_permissions=False)
    return {"name": doc.name, "url": f"/app/inventaire-kya/{doc.name}"}


def _get_stock_rows(warehouse):
    """Lignes de stock d'un magasin depuis le grand livre maison (pas Bin).
    qte_theorique = solde total (bon état + réparation) ; pas de valorisation."""
    from kya_hr.api import stock_kya
    out = []
    for d in stock_kya.soldes(magasin=warehouse, only_nonzero=1):
        out.append(frappe._dict({
            "item_code": d["item"], "warehouse": warehouse,
            "qte_theorique": d["total"], "valuation_rate": 0,
            "designation": d["item_name"],
            "uom": frappe.db.get_value("Article KYA", d["item"], "unite") or "",
        }))
    return out


@frappe.whitelist()
def get_stock_movements(warehouse=None, period="30"):
    """Entrées/sorties de stock, depuis le grand livre maison Mouvement Stock KYA
    (plus de Stock Entry ERPNext)."""
    period = int(period or 30)
    date_from = add_days(today(), -period)
    args = {"date_from": date_from}

    wh_condition = ""
    if warehouse:
        wh_condition = "AND m.magasin = %(warehouse)s"
        args["warehouse"] = warehouse

    rows = frappe.db.sql(f"""
        SELECT m.name, m.date_mouvement AS posting_date, m.type_mouvement AS purpose,
               m.reference_doctype, m.reference_name,
               m.item AS item_code, m.item_name, ABS(m.quantite) AS qty,
               m.magasin AS warehouse, m.etat, 0 AS amount
        FROM `tabMouvement Stock KYA` m
        WHERE m.date_mouvement >= %(date_from)s
          AND m.type_mouvement IN ('Entrée', 'Sortie')
          {wh_condition}
        ORDER BY m.date_mouvement DESC, m.modified DESC
        LIMIT 30
    """, args, as_dict=True)

    totals = {"entrees_qty": 0, "sorties_qty": 0, "mouvements": len(rows)}
    for row in rows:
        if row.purpose == "Entrée":
            totals["entrees_qty"] += flt(row.qty)
        elif row.purpose == "Sortie":
            totals["sorties_qty"] += flt(row.qty)

    return {"totals": totals, "rows": rows}


@frappe.whitelist()
def get_stock_summary(warehouse=None):
    """Résumé stock actuel par article depuis le grand livre maison (pas Bin).
    Quantités uniquement (pas de valorisation en maison)."""
    from kya_hr.api import stock_kya
    agg = {}
    for d in stock_kya.soldes(magasin=warehouse, only_nonzero=1):
        e = agg.setdefault(d["item"], {"item_code": d["item"],
                                       "item_name": d["item_name"],
                                       "qty": 0.0, "valeur": 0})
        e["qty"] += flt(d["total"])
    rows = sorted(agg.values(), key=lambda r: -r["qty"])[:20]
    return rows

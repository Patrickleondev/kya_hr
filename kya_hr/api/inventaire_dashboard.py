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
    return frappe.db.sql(
        """
        SELECT b.item_code, b.warehouse, b.actual_qty AS qte_theorique, b.valuation_rate,
               i.item_name AS designation, i.stock_uom AS uom
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE b.warehouse = %s AND b.actual_qty > 0 AND i.disabled = 0
        ORDER BY i.item_name
        """,
        (warehouse,),
        as_dict=True,
    )


@frappe.whitelist()
def get_stock_movements(warehouse=None, period="30"):
    """Entrées/sorties de stock soumises, utilisées par le dashboard inventaire."""
    period = int(period or 30)
    date_from = add_days(today(), -period)
    args = {"date_from": date_from}

    wh_condition = ""
    if warehouse:
        wh_condition = "AND COALESCE(d.t_warehouse, d.s_warehouse) = %(warehouse)s"
        args["warehouse"] = warehouse

    rows = frappe.db.sql(f"""
        SELECT se.name, se.posting_date, se.stock_entry_type, se.purpose,
               se.pv_entree_materiel, se.pv_sortie_materiel,
               d.item_code, d.item_name, d.qty,
               COALESCE(d.t_warehouse, d.s_warehouse) AS warehouse,
               COALESCE(d.amount, d.basic_amount, 0) AS amount
        FROM `tabStock Entry` se
        INNER JOIN `tabStock Entry Detail` d ON d.parent = se.name
        WHERE se.docstatus = 1
          AND se.posting_date >= %(date_from)s
          AND se.purpose IN ('Material Receipt', 'Material Issue')
          {wh_condition}
        ORDER BY se.posting_date DESC, se.modified DESC
        LIMIT 30
    """, args, as_dict=True)

    totals = {"entrees_qty": 0, "sorties_qty": 0, "mouvements": len(rows)}
    for row in rows:
        if row.purpose == "Material Receipt":
            totals["entrees_qty"] += flt(row.qty)
        elif row.purpose == "Material Issue":
            totals["sorties_qty"] += flt(row.qty)

    return {"totals": totals, "rows": rows}


@frappe.whitelist()
def get_stock_summary(warehouse=None):
    """Résumé stock actuel par article (pour graphique répartition)."""
    args = {}
    wh_filter = ""
    if warehouse:
        wh_filter = "AND warehouse = %(warehouse)s"
        args["warehouse"] = warehouse

    rows = frappe.db.sql(f"""
        SELECT b.item_code, i.item_name,
               SUM(b.actual_qty) AS qty,
               SUM(b.actual_qty * COALESCE(b.valuation_rate, 0)) AS valeur
        FROM `tabBin` b
        JOIN `tabItem` i ON i.name = b.item_code
        WHERE b.actual_qty > 0 {wh_filter}
        GROUP BY b.item_code
        ORDER BY valeur DESC
        LIMIT 20
    """, args, as_dict=True)

    return rows

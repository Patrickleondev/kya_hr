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
        ORDER BY ABS(valeur_ecart) DESC
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

    return {
        "kpis": {
            "total": total_inv,
            "pending": pending,
            "approved": approved,
            "valeur_ecart": flt(valeur_ecart),
        },
        "evolution": evolution,
        "top_ecarts": top_ecarts,
        "recents": recents,
        "par_statut": par_statut,
        "warehouses": warehouses,
        "currency": "XOF",
    }


@frappe.whitelist()
def create_inventaire(objet, date_inventaire=None, warehouse=None, type_inventaire="Partiel"):
    """Création rapide d'un inventaire depuis le dashboard."""
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
    doc.insert(ignore_permissions=False)
    return {"name": doc.name, "url": f"/app/inventaire-kya/{doc.name}"}


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

"""Dashboard Logistique — agrégation stock + achats + mouvements + véhicules.

Accessible aux rôles : Stock Manager, Stock User, Chargé des Stocks, Responsable
Logistique, Responsable Achats, Purchase Manager, DAAF, DGA, DG, System Manager.
"""
import frappe
from frappe.utils import add_days, flt, today, cint


no_cache = 1


_ALLOWED_ROLES = {
    "System Manager", "Administrator",
    "Stock Manager", "Stock User", "Chargé des Stocks", "Responsable Stock",
    "Purchase Manager", "Purchase User", "Responsable Achats",
    "Fleet Manager", "Gestionnaire de Flotte",
    "DAAF", "DGA", "Directeur Général", "DG",
    "DST - Responsable Logistique",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/logistique-dashboard"
        raise frappe.Redirect

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not (_ALLOWED_ROLES & user_roles):
        frappe.throw("Accès réservé à la logistique / direction.", frappe.PermissionError)

    period = cint(frappe.form_dict.get("period") or 30)
    date_from = add_days(today(), -period)

    context.title = "Dashboard Logistique"
    context.no_breadcrumbs = True
    context.period = period
    context.date_from = date_from
    context.date_to = today()

    # ─── STOCK GLOBAL (ERPNext Item + Bin) ──────────────────────────────
    stock_kpis = _stock_kpis()
    context.stock = stock_kpis

    # ─── ACHATS (Demandes + Bons de Commande) ───────────────────────────
    context.achats = _achats_kpis(date_from)

    # ─── MOUVEMENTS STOCK (Stock Entry) ─────────────────────────────────
    context.mouvements = _mouvements_kpis(date_from)

    # ─── INVENTAIRES KYA ─────────────────────────────────────────────────
    context.inventaires = _inventaires_kpis(date_from)

    # ─── VEHICULES + DOCUMENTS (si DocType present) ─────────────────────
    context.vehicules = _vehicules_kpis()

    # ─── TOP ITEMS PAR VALEUR ───────────────────────────────────────────
    context.top_items = _top_items_by_value()

    # ─── ACTIVITE PAR WAREHOUSE ─────────────────────────────────────────
    context.par_warehouse = _par_warehouse()


def _stock_kpis():
    items_total = frappe.db.count("Item", {"is_stock_item": 1, "disabled": 0})
    bins_stock = frappe.db.sql(
        "SELECT COALESCE(SUM(actual_qty), 0), COALESCE(SUM(actual_qty * valuation_rate), 0) "
        "FROM `tabBin` WHERE actual_qty > 0",
        as_dict=False,
    )
    total_qty = flt(bins_stock[0][0]) if bins_stock else 0
    total_value = flt(bins_stock[0][1]) if bins_stock else 0
    warehouses = frappe.db.count("Warehouse", {"disabled": 0, "is_group": 0})
    items_with_stock = frappe.db.sql(
        "SELECT COUNT(DISTINCT item_code) FROM `tabBin` WHERE actual_qty > 0"
    )[0][0]
    items_rupture = items_total - items_with_stock if items_total > items_with_stock else 0
    return {
        "items_total": items_total,
        "items_with_stock": items_with_stock,
        "items_rupture": items_rupture,
        "warehouses": warehouses,
        "total_qty": round(total_qty, 0),
        "total_value": round(total_value, 0),
    }


def _achats_kpis(date_from):
    # Demandes d'Achat KYA
    da_total = 0
    da_approved = 0
    da_amount = 0
    if frappe.db.exists("DocType", "Demande Achat KYA"):
        rows = frappe.get_all(
            "Demande Achat KYA",
            filters={"creation": [">=", date_from]},
            fields=["name", "workflow_state", "montant_total"],
            limit_page_length=0,
        )
        da_total = len(rows)
        for r in rows:
            if (r.workflow_state or "").startswith("Approuv"):
                da_approved += 1
                da_amount += flt(r.montant_total or 0)
    # Bons de Commande KYA (statut + total_ttc)
    bc_total = 0
    bc_amount = 0
    if frappe.db.exists("DocType", "Bon Commande KYA"):
        rows = frappe.get_all(
            "Bon Commande KYA",
            filters={"creation": [">=", date_from]},
            fields=["name", "statut", "total_ttc"],
            limit_page_length=0,
        )
        bc_total = len(rows)
        bc_amount = sum(flt(r.total_ttc or 0) for r in rows)
    return {
        "da_total": da_total,
        "da_approved": da_approved,
        "da_amount": da_amount,
        "bc_total": bc_total,
        "bc_amount": bc_amount,
    }


def _mouvements_kpis(date_from):
    rows = frappe.db.sql(
        """
        SELECT stock_entry_type, COUNT(*) AS nb, COALESCE(SUM(total_outgoing_value), 0) AS val
        FROM `tabStock Entry`
        WHERE docstatus = 1 AND posting_date >= %s
        GROUP BY stock_entry_type
        """,
        (date_from,), as_dict=True,
    )
    total_mvt = sum(r.nb for r in rows)
    total_value = sum(flt(r.val) for r in rows)
    by_type = {r.stock_entry_type: {"nb": r.nb, "val": flt(r.val)} for r in rows}
    return {
        "total_mouvements": total_mvt,
        "total_value": round(total_value, 0),
        "by_type": by_type,
    }


def _inventaires_kpis(date_from):
    if not frappe.db.exists("DocType", "Inventaire KYA"):
        return {"total": 0, "approved": 0, "pending": 0, "valeur_ecart": 0}
    rows = frappe.get_all(
        "Inventaire KYA",
        filters={"date_inventaire": [">=", date_from]},
        fields=["name", "statut", "valeur_ecart_total"],
    )
    return {
        "total": len(rows),
        "approved": sum(1 for r in rows if r.statut == "Approuvé"),
        "pending": sum(1 for r in rows if (r.statut or "").startswith("En attente")),
        "valeur_ecart": round(sum(flt(r.valeur_ecart_total or 0) for r in rows), 0),
    }


def _vehicules_kpis():
    if not frappe.db.exists("DocType", "Vehicle"):
        return {"total": 0, "docs_expires": 0}
    total = frappe.db.count("Vehicle")
    docs_expires = 0
    if frappe.db.exists("DocType", "Document Vehicule"):
        docs_expires = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDocument Vehicule` "
            "WHERE date_expiration IS NOT NULL AND date_expiration < CURDATE()"
        )[0][0]
    return {"total": total, "docs_expires": docs_expires}


def _top_items_by_value():
    rows = frappe.db.sql(
        """
        SELECT b.item_code, i.item_name,
               SUM(b.actual_qty) AS qty,
               SUM(b.actual_qty * b.valuation_rate) AS value
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE b.actual_qty > 0
        GROUP BY b.item_code, i.item_name
        ORDER BY value DESC
        LIMIT 10
        """,
        as_dict=True,
    )
    for r in rows:
        r["qty"] = round(flt(r.qty), 0)
        r["value"] = round(flt(r.value), 0)
    return rows


def _par_warehouse():
    rows = frappe.db.sql(
        """
        SELECT b.warehouse,
               COUNT(DISTINCT b.item_code) AS items,
               SUM(b.actual_qty) AS qty,
               SUM(b.actual_qty * b.valuation_rate) AS value
        FROM `tabBin` b
        WHERE b.actual_qty > 0
        GROUP BY b.warehouse
        ORDER BY value DESC
        """,
        as_dict=True,
    )
    for r in rows:
        r["qty"] = round(flt(r.qty), 0)
        r["value"] = round(flt(r.value), 0)
    return rows

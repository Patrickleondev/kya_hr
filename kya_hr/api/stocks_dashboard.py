"""API Dashboard Stocks Generalise KYA.

Fournit aux pages /kya-stocks-dashboard les KPIs + tables :
- Vue globale : nb articles, valeur stock totale, ruptures, mouvements 30j
- Par entrepot : stock value, item count, dernier mouvement
- Par groupe d'article : qty totale, valeur
- Mouvements recents (Stock Ledger Entry)
- Articles en rupture / alerte

Toutes les fonctions sont @frappe.whitelist() avec verification des roles
(Stock User, Stock Manager, System Manager, DG, DGA, Responsable RH).
"""
from __future__ import annotations

import frappe
from frappe.utils import flt, getdate, add_days, today


STOCK_ROLES = {
    "Stock User", "Stock Manager", "System Manager",
    "Directeur General", "DG", "DGA",
    "Responsable RH", "Chef Service Achats", "Auditeur",
}


def _check_role():
    """Bloque l'acces si l'utilisateur n'a aucun role autorise."""
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not (user_roles & STOCK_ROLES):
        frappe.throw("Acces refuse - role Stock requis", frappe.PermissionError)


@frappe.whitelist()
def get_dashboard_overview() -> dict:
    """KPIs globaux : nb articles, valeur stock totale, ruptures, mouvements 30j."""
    _check_role()

    # Nombre d'articles actifs (non disabled)
    total_items = frappe.db.count("Item", {"disabled": 0})

    # Stock global : sum(actual_qty * valuation_rate) depuis Bin
    stock_value = frappe.db.sql("""
        SELECT
            COALESCE(SUM(b.actual_qty * b.valuation_rate), 0) as total_value,
            COALESCE(SUM(b.actual_qty), 0) as total_qty,
            COUNT(DISTINCT b.item_code) as items_in_stock
        FROM `tabBin` b
        WHERE b.actual_qty > 0
    """, as_dict=True)[0]

    # Articles en rupture (actual_qty = 0 ou negative ou < reorder_level)
    rupture = frappe.db.sql("""
        SELECT COUNT(DISTINCT item_code) AS n
        FROM `tabBin`
        WHERE actual_qty <= 0
    """)[0][0]

    # Mouvements 30 derniers jours
    from_date = add_days(today(), -30)
    movements = frappe.db.sql("""
        SELECT
            COUNT(*) AS total_entries,
            COALESCE(SUM(CASE WHEN actual_qty > 0 THEN 1 ELSE 0 END), 0) AS receipts,
            COALESCE(SUM(CASE WHEN actual_qty < 0 THEN 1 ELSE 0 END), 0) AS issues
        FROM `tabStock Ledger Entry`
        WHERE posting_date >= %(from_date)s
          AND is_cancelled = 0
    """, {"from_date": from_date}, as_dict=True)[0]

    return {
        "total_items": total_items,
        "items_in_stock": stock_value["items_in_stock"],
        "stock_value": flt(stock_value["total_value"], 2),
        "total_qty": flt(stock_value["total_qty"], 2),
        "rupture_count": rupture,
        "movements_30d": movements,
        "as_of": today(),
    }


@frappe.whitelist()
def get_warehouses_summary() -> list[dict]:
    """Pour chaque warehouse : stock value, item count, dernier mouvement."""
    _check_role()

    rows = frappe.db.sql("""
        SELECT
            w.name AS warehouse,
            w.warehouse_name,
            w.company,
            COUNT(DISTINCT CASE WHEN b.actual_qty > 0 THEN b.item_code END) AS items_in_stock,
            COALESCE(SUM(b.actual_qty), 0) AS total_qty,
            COALESCE(SUM(b.actual_qty * b.valuation_rate), 0) AS stock_value,
            (SELECT MAX(sle.posting_date)
             FROM `tabStock Ledger Entry` sle
             WHERE sle.warehouse = w.name AND sle.is_cancelled = 0
            ) AS last_movement
        FROM `tabWarehouse` w
        LEFT JOIN `tabBin` b ON b.warehouse = w.name
        WHERE w.disabled = 0 AND w.is_group = 0
        GROUP BY w.name, w.warehouse_name, w.company
        ORDER BY stock_value DESC
    """, as_dict=True)

    for r in rows:
        r["stock_value"] = flt(r["stock_value"], 2)
        r["total_qty"] = flt(r["total_qty"], 2)
    return rows


@frappe.whitelist()
def get_items_by_group() -> list[dict]:
    """Pour chaque Item Group : nb items, qty totale, valeur stock."""
    _check_role()

    rows = frappe.db.sql("""
        SELECT
            i.item_group,
            COUNT(DISTINCT i.name) AS items_count,
            COALESCE(SUM(b.actual_qty), 0) AS total_qty,
            COALESCE(SUM(b.actual_qty * b.valuation_rate), 0) AS stock_value
        FROM `tabItem` i
        LEFT JOIN `tabBin` b ON b.item_code = i.name
        WHERE i.disabled = 0 AND i.item_group IS NOT NULL
        GROUP BY i.item_group
        ORDER BY items_count DESC
    """, as_dict=True)

    for r in rows:
        r["stock_value"] = flt(r["stock_value"], 2)
        r["total_qty"] = flt(r["total_qty"], 2)
    return rows


@frappe.whitelist()
def get_recent_movements(limit: int = 50) -> list[dict]:
    """Derniers mouvements de stock (entries + issues), tous warehouses."""
    _check_role()
    try:
        limit = max(1, min(int(limit), 200))
    except (ValueError, TypeError):
        limit = 50

    return frappe.db.sql("""
        SELECT
            sle.posting_date,
            sle.posting_time,
            sle.item_code,
            i.item_name,
            sle.warehouse,
            sle.actual_qty,
            sle.qty_after_transaction,
            sle.valuation_rate,
            sle.voucher_type,
            sle.voucher_no
        FROM `tabStock Ledger Entry` sle
        LEFT JOIN `tabItem` i ON i.name = sle.item_code
        WHERE sle.is_cancelled = 0
        ORDER BY sle.posting_date DESC, sle.posting_time DESC
        LIMIT %(limit)s
    """, {"limit": limit}, as_dict=True)


@frappe.whitelist()
def get_low_stock(threshold: float = 0) -> list[dict]:
    """Articles dont actual_qty <= threshold dans au moins un warehouse."""
    _check_role()
    try:
        threshold = flt(threshold)
    except (ValueError, TypeError):
        threshold = 0

    return frappe.db.sql("""
        SELECT
            b.item_code,
            i.item_name,
            i.item_group,
            b.warehouse,
            b.actual_qty,
            b.valuation_rate,
            i.disabled
        FROM `tabBin` b
        LEFT JOIN `tabItem` i ON i.name = b.item_code
        WHERE b.actual_qty <= %(threshold)s
          AND COALESCE(i.disabled, 0) = 0
        ORDER BY b.actual_qty ASC, b.item_code
        LIMIT 100
    """, {"threshold": threshold}, as_dict=True)


@frappe.whitelist()
def get_items_filtered(
    item_group: str = "",
    warehouse: str = "",
    search: str = "",
    limit: int = 100,
) -> list[dict]:
    """Liste filtree des Items avec leur stock par entrepot."""
    _check_role()
    try:
        limit = max(1, min(int(limit), 500))
    except (ValueError, TypeError):
        limit = 100

    where_clauses = ["i.disabled = 0"]
    params: dict = {"limit": limit}

    if item_group:
        where_clauses.append("i.item_group = %(item_group)s")
        params["item_group"] = item_group
    if search:
        where_clauses.append("(i.name LIKE %(s)s OR i.item_name LIKE %(s)s)")
        params["s"] = f"%{search}%"
    if warehouse:
        where_clauses.append("b.warehouse = %(warehouse)s")
        params["warehouse"] = warehouse

    where = " AND ".join(where_clauses)

    return frappe.db.sql(f"""
        SELECT
            i.name AS item_code,
            i.item_name,
            i.item_group,
            i.stock_uom,
            b.warehouse,
            COALESCE(b.actual_qty, 0) AS actual_qty,
            COALESCE(b.valuation_rate, 0) AS valuation_rate,
            COALESCE(b.actual_qty * b.valuation_rate, 0) AS stock_value
        FROM `tabItem` i
        LEFT JOIN `tabBin` b ON b.item_code = i.name
        WHERE {where}
        ORDER BY i.item_group, i.name
        LIMIT %(limit)s
    """, params, as_dict=True)

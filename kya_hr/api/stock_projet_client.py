# -*- coding: utf-8 -*-
"""API du dashboard Stock par Projet / Client."""
import frappe
from frappe.utils import flt, add_days, today


@frappe.whitelist()
def get_filters():
    """Liste projets + clients + magasins pour dropdowns."""
    projects = frappe.get_all(
        "Project",
        filters={"status": ["!=", "Cancelled"]},
        fields=["name", "project_name"],
        order_by="project_name",
        limit=500,
    )
    customers = frappe.get_all(
        "Customer",
        filters={"disabled": 0},
        fields=["name", "customer_name"],
        order_by="customer_name",
        limit=500,
    )
    warehouses = frappe.get_all(
        "Warehouse",
        filters={"disabled": 0, "is_group": 0},
        fields=["name", "warehouse_name"],
        order_by="warehouse_name",
        limit=200,
    )
    return {"projects": projects, "customers": customers, "warehouses": warehouses}


@frappe.whitelist()
def get_report(project=None, customer=None, warehouse=None, period="90"):
    """Rapport stock filtrable par projet / client / magasin + période."""
    period = int(period or 90)
    date_from = add_days(today(), -period)
    args = {"date_from": date_from}

    # Filtres SQL dynamiques
    se_filters = []
    if project:
        se_filters.append("se.project = %(project)s")
        args["project"] = project
    if warehouse:
        se_filters.append("(sed.s_warehouse = %(warehouse)s OR sed.t_warehouse = %(warehouse)s)")
        args["warehouse"] = warehouse
    se_where = (" AND " + " AND ".join(se_filters)) if se_filters else ""

    # Mouvements de stock liés au projet (Stock Entry)
    mouvements = frappe.db.sql(f"""
        SELECT se.name, se.posting_date, se.stock_entry_type, se.project,
               sed.item_code, sed.item_name, sed.qty, sed.uom,
               sed.s_warehouse, sed.t_warehouse,
               sed.basic_rate, sed.basic_amount
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.docstatus = 1
          AND se.posting_date >= %(date_from)s
          {se_where}
        ORDER BY se.posting_date DESC
        LIMIT 200
    """, args, as_dict=True)

    # Bons de livraison au client
    dn_filters = []
    dn_args = {"date_from": date_from}
    if customer:
        dn_filters.append("dn.customer = %(customer)s")
        dn_args["customer"] = customer
    if project:
        dn_filters.append("dn.project = %(project)s")
        dn_args["project"] = project
    if warehouse:
        dn_filters.append("dni.warehouse = %(warehouse)s")
        dn_args["warehouse"] = warehouse
    dn_where = (" AND " + " AND ".join(dn_filters)) if dn_filters else ""

    livraisons = frappe.db.sql(f"""
        SELECT dn.name, dn.posting_date, dn.customer, dn.customer_name, dn.project,
               dni.item_code, dni.item_name, dni.qty, dni.uom,
               dni.warehouse, dni.rate, dni.amount
        FROM `tabDelivery Note` dn
        JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
        WHERE dn.docstatus = 1
          AND dn.posting_date >= %(date_from)s
          {dn_where}
        ORDER BY dn.posting_date DESC
        LIMIT 200
    """, dn_args, as_dict=True)

    # Synthèse par article (consolidée Stock Entry + Delivery Note)
    synthese_args = {"date_from": date_from}
    syn_filter_se = []
    syn_filter_dn = []
    if project:
        syn_filter_se.append("se.project = %(project)s")
        syn_filter_dn.append("dn.project = %(project)s")
        synthese_args["project"] = project
    if warehouse:
        syn_filter_se.append("(sed.s_warehouse = %(warehouse)s OR sed.t_warehouse = %(warehouse)s)")
        syn_filter_dn.append("dni.warehouse = %(warehouse)s")
        synthese_args["warehouse"] = warehouse
    if customer:
        syn_filter_dn.append("dn.customer = %(customer)s")
        synthese_args["customer"] = customer

    syn_se_where = (" AND " + " AND ".join(syn_filter_se)) if syn_filter_se else ""
    syn_dn_where = (" AND " + " AND ".join(syn_filter_dn)) if syn_filter_dn else ""

    try:
        synthese = frappe.db.sql(f"""
            SELECT item_code, item_name,
                   SUM(qty_se) AS qty_entree,
                   SUM(qty_dn) AS qty_sortie,
                   SUM(val_se + val_dn) AS valeur_totale
            FROM (
                SELECT sed.item_code, sed.item_name, sed.qty AS qty_se, 0 AS qty_dn,
                       COALESCE(sed.basic_amount, 0) AS val_se, 0 AS val_dn
                FROM `tabStock Entry` se
                JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
                WHERE se.docstatus = 1 AND se.posting_date >= %(date_from)s {syn_se_where}
                UNION ALL
                SELECT dni.item_code, dni.item_name, 0, dni.qty,
                       0, COALESCE(dni.amount, 0)
                FROM `tabDelivery Note` dn
                JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
                WHERE dn.docstatus = 1 AND dn.posting_date >= %(date_from)s {syn_dn_where}
            ) t
            GROUP BY item_code, item_name
            ORDER BY valeur_totale DESC
            LIMIT 50
        """, synthese_args, as_dict=True)
    except Exception:
        synthese = []

    # KPIs
    total_mouvements = len(mouvements)
    total_livraisons = len(livraisons)
    valeur_livrée = sum(flt(l.amount) for l in livraisons)
    valeur_stock_mouv = sum(flt(m.basic_amount) for m in mouvements)

    # Répartition par projet (si pas de projet filtré)
    par_projet = []
    if not project:
        par_projet = frappe.db.sql("""
            SELECT se.project, p.project_name,
                   COUNT(DISTINCT se.name) AS nb_mouvements,
                   COALESCE(SUM(sed.basic_amount), 0) AS valeur
            FROM `tabStock Entry` se
            LEFT JOIN `tabProject` p ON p.name = se.project
            JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
            WHERE se.docstatus = 1 AND se.posting_date >= %(date_from)s
              AND se.project IS NOT NULL AND se.project != ''
            GROUP BY se.project
            ORDER BY valeur DESC
            LIMIT 20
        """, {"date_from": date_from}, as_dict=True)

    # Répartition par client
    par_client = []
    if not customer:
        par_client = frappe.db.sql("""
            SELECT dn.customer, dn.customer_name,
                   COUNT(DISTINCT dn.name) AS nb_livraisons,
                   COALESCE(SUM(dni.amount), 0) AS valeur
            FROM `tabDelivery Note` dn
            JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
            WHERE dn.docstatus = 1 AND dn.posting_date >= %(date_from)s
            GROUP BY dn.customer
            ORDER BY valeur DESC
            LIMIT 20
        """, {"date_from": date_from}, as_dict=True)

    # === SORTIES / ENTRÉES MATÉRIEL KYA (doctypes custom) ================
    # Ventilation par client pour le livre d'inventaire KYA
    pv_sorties_par_client = []
    try:
        pv_sorties_par_client = frappe.db.sql("""
            SELECT
                COALESCE(pv.customer, pv.customer_manuel, 'Interne') AS client,
                pv.destination_type,
                COUNT(DISTINCT pv.name) AS nb_pv,
                COALESCE(SUM(pvi.qte_reellement_sortie), 0) AS qte_totale
            FROM `tabPV Sortie Materiel` pv
            JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent = pv.name
            WHERE pv.date_sortie >= %(date_from)s
              AND (pv.workflow_state IS NULL OR pv.workflow_state NOT IN ('Rejeté', 'Brouillon'))
            GROUP BY client, pv.destination_type
            ORDER BY qte_totale DESC
            LIMIT 30
        """, {"date_from": date_from}, as_dict=True)
    except Exception as e:
        frappe.logger().info(f"[stock_projet_client] PV Sortie aggregation skip: {e}")
        pv_sorties_par_client = []

    # Livre d'inventaire : entrées vs sorties par article (PV Sortie + PV Entrée)
    livre_inventaire = []
    try:
        livre_inventaire = frappe.db.sql("""
            SELECT item_code, designation,
                   SUM(entree) AS total_entree,
                   SUM(sortie) AS total_sortie,
                   SUM(entree) - SUM(sortie) AS solde
            FROM (
                SELECT pvi.item_code, pvi.designation, 0 AS entree, COALESCE(pvi.qte_reellement_sortie,0) AS sortie
                FROM `tabPV Sortie Materiel` pv
                JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent = pv.name
                WHERE pv.date_sortie >= %(date_from)s
                  AND (pv.workflow_state IS NULL OR pv.workflow_state NOT IN ('Rejeté', 'Brouillon'))
                UNION ALL
                SELECT pei.item_code, pei.designation,
                       COALESCE(pei.qte_reellement_entree, pei.qte_attendue, 0) AS entree, 0 AS sortie
                FROM `tabPV Entree Materiel` pe
                JOIN `tabPV Entree Materiel Item` pei ON pei.parent = pe.name
                WHERE pe.date_entree >= %(date_from)s
                  AND (pe.workflow_state IS NULL OR pe.workflow_state NOT IN ('Rejeté', 'Brouillon'))
            ) t
            GROUP BY item_code, designation
            HAVING (total_entree > 0 OR total_sortie > 0)
            ORDER BY (total_entree + total_sortie) DESC
            LIMIT 100
        """, {"date_from": date_from}, as_dict=True)
    except Exception as e:
        frappe.logger().info(f"[stock_projet_client] Livre inventaire skip: {e}")
        livre_inventaire = []

    return {
        "kpis": {
            "nb_mouvements": total_mouvements,
            "nb_livraisons": total_livraisons,
            "valeur_livree": valeur_livrée,
            "valeur_mouvements": valeur_stock_mouv,
        },
        "mouvements": mouvements,
        "livraisons": livraisons,
        "synthese": synthese,
        "par_projet": par_projet,
        "par_client": par_client,
        "pv_sorties_par_client": pv_sorties_par_client,
        "livre_inventaire": livre_inventaire,
    }

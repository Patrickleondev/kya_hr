# -*- coding: utf-8 -*-
"""API du dashboard Stock par Projet / Client."""
import frappe
from frappe import _
from frappe.utils import flt, add_days, today


@frappe.whitelist()
def export_xlsx(rows, sheet="Export"):
    """Exporte une liste de lignes (onglet courant) en vrai fichier Excel (.xlsx).
    On travaille en Excel ici, jamais en CSV."""
    import base64
    import json
    from frappe.utils.xlsxutils import make_xlsx
    if isinstance(rows, str):
        rows = json.loads(rows or "[]")
    if not rows:
        frappe.throw(_("Aucune donnée à exporter."))
    keys = list(rows[0].keys())
    data = [keys] + [[r.get(k, "") for k in keys] for r in rows]
    xlsx = make_xlsx(data, sheet[:31] or "Export")
    return {"filename": "kya-stock-{0}-{1}.xlsx".format(sheet, today()),
            "content_base64": base64.b64encode(xlsx.getvalue()).decode("ascii")}


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
    """Rapport des SORTIES matériel (données maison PV Sortie / PV Entrée).

    Objectif métier : voir QUELS articles sont sortis, en QUELLE quantité, pour
    QUELLE destination / QUEL client / QUEL projet. Pas de valorisation (la
    compta/finance n'utilise pas ERPNext) — la métrique est la QUANTITÉ.
    """
    period = int(period or 90)
    date_from = add_days(today(), -period)
    args = {"date_from": date_from}

    # Expressions communes
    QTE = ("CASE WHEN COALESCE(pvi.qte_reellement_sortie,0) > 0 "
           "THEN pvi.qte_reellement_sortie ELSE COALESCE(pvi.qte_demandee,0) END")
    CLIENT = ("COALESCE((SELECT customer_name FROM `tabCustomer` c WHERE c.name = pv.customer), "
              "NULLIF(pv.customer_manuel,''), NULLIF(pv.customer,''), 'Interne')")
    PROJET = ("COALESCE((SELECT project_name FROM `tabProject` p WHERE p.name = pv.project), "
              "NULLIF(pv.project_manuel,''), NULLIF(pv.project,''), '—')")

    conds = ["pv.date_sortie >= %(date_from)s",
             "(pv.workflow_state IS NULL OR pv.workflow_state NOT IN ('Rejeté','Brouillon'))"]
    if project:
        conds.append("(pv.project = %(project)s OR pv.project_manuel = %(project)s)")
        args["project"] = project
    if customer:
        conds.append("(pv.customer = %(customer)s OR pv.customer_manuel = %(customer)s)")
        args["customer"] = customer
    if warehouse:
        conds.append("pvi.warehouse = %(warehouse)s")
        args["warehouse"] = warehouse
    where = " AND ".join(conds)

    # Lignes de sortie détaillées (onglet « Mouvements »)
    mouvements = frappe.db.sql(f"""
        SELECT pv.name, pv.date_sortie AS posting_date, 'Sortie' AS stock_entry_type,
               {PROJET} AS project, pvi.item_code, pvi.designation AS item_name,
               {QTE} AS qty, pvi.uom, pvi.warehouse AS s_warehouse,
               {CLIENT} AS t_warehouse, pv.destination_type
        FROM `tabPV Sortie Materiel` pv
        JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent = pv.name
        WHERE {where}
        ORDER BY pv.date_sortie DESC
        LIMIT 300
    """, args, as_dict=True)

    # Sorties vers un client/projet (onglet « Livraisons »)
    livraisons = []
    for m in mouvements:
        if (m.get("destination_type") or "") == "Client / Projet":
            livraisons.append({
                "name": m["name"], "posting_date": m["posting_date"],
                "customer": m["t_warehouse"], "customer_name": m["t_warehouse"],
                "project": m["project"], "item_code": m["item_code"],
                "item_name": m["item_name"], "qty": m["qty"], "uom": m.get("uom"),
                "warehouse": m["s_warehouse"], "amount": 0,
            })

    # Synthèse par article : entrées vs sorties (livre d'inventaire)
    synthese = frappe.db.sql(f"""
        SELECT item_code, item_name,
               SUM(entree) AS qty_entree, SUM(sortie) AS qty_sortie,
               SUM(entree) - SUM(sortie) AS valeur_totale
        FROM (
            SELECT pvi.item_code, pvi.designation AS item_name,
                   0 AS entree, {QTE} AS sortie
            FROM `tabPV Sortie Materiel` pv
            JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent = pv.name
            WHERE {where}
            UNION ALL
            SELECT pei.item_code, pei.designation AS item_name,
                   COALESCE(pei.qte_recue, pei.qte_commandee, 0) AS entree, 0 AS sortie
            FROM `tabPV Entree Materiel` pe
            JOIN `tabPV Entree Materiel Item` pei ON pei.parent = pe.name
            WHERE pe.date_entree >= %(date_from)s
              AND (pe.workflow_state IS NULL OR pe.workflow_state NOT IN ('Rejeté','Brouillon'))
        ) t
        GROUP BY item_code, item_name
        HAVING (SUM(entree) > 0 OR SUM(sortie) > 0)
        ORDER BY (SUM(entree) + SUM(sortie)) DESC
        LIMIT 100
    """, args, as_dict=True)

    # Répartition par PROJET (quantité sortie)
    par_projet = frappe.db.sql(f"""
        SELECT {PROJET} AS project, {PROJET} AS project_name,
               COUNT(DISTINCT pv.name) AS nb_mouvements, SUM({QTE}) AS valeur
        FROM `tabPV Sortie Materiel` pv
        JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent = pv.name
        WHERE {where}
        GROUP BY {PROJET} ORDER BY valeur DESC LIMIT 20
    """, args, as_dict=True)

    # Répartition par CLIENT (quantité sortie)
    par_client = frappe.db.sql(f"""
        SELECT {CLIENT} AS customer, {CLIENT} AS customer_name,
               COUNT(DISTINCT pv.name) AS nb_livraisons, SUM({QTE}) AS valeur
        FROM `tabPV Sortie Materiel` pv
        JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent = pv.name
        WHERE {where}
        GROUP BY {CLIENT} ORDER BY valeur DESC LIMIT 20
    """, args, as_dict=True)

    # KPIs (quantités, pas de valorisation)
    qte_totale_sortie = sum(flt(m["qty"]) for m in mouvements)
    qte_vers_clients = sum(flt(l["qty"]) for l in livraisons)

    return {
        "kpis": {
            "nb_mouvements": len(mouvements),
            "nb_livraisons": len(livraisons),
            "valeur_livree": qte_vers_clients,     # réinterprété : quantité vers clients
            "valeur_mouvements": qte_totale_sortie, # réinterprété : quantité totale sortie
        },
        "mouvements": mouvements,
        "livraisons": livraisons,
        "synthese": synthese,
        "par_projet": par_projet,
        "par_client": par_client,
    }

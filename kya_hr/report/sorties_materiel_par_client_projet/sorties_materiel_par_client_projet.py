"""
Query Report : Sorties Matériel par Client / Projet
Filtres dynamiques temps réel pour DG/DGA
"""
import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data, None, get_chart(data), get_summary(data)


def get_columns():
    return [
        {"label": _("PV"), "fieldname": "pv", "fieldtype": "Link", "options": "PV Sortie Materiel", "width": 140},
        {"label": _("Date"), "fieldname": "date_sortie", "fieldtype": "Date", "width": 100},
        {"label": _("Client"), "fieldname": "client_name", "fieldtype": "Data", "width": 180},
        {"label": _("Projet"), "fieldname": "projet", "fieldtype": "Link", "options": "Project", "width": 140},
        {"label": _("Chantier"), "fieldname": "chantier_libre", "fieldtype": "Data", "width": 140},
        {"label": _("Article"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": _("Désignation"), "fieldname": "designation", "fieldtype": "Data", "width": 220},
        {"label": _("Magasin"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130},
        {"label": _("Qté demandée"), "fieldname": "qte_demandee", "fieldtype": "Float", "width": 110},
        {"label": _("Qté sortie"), "fieldname": "qte_reellement_sortie", "fieldtype": "Float", "width": 110},
        {"label": _("PU (XOF)"), "fieldname": "valeur_unitaire", "fieldtype": "Currency", "options": "currency", "width": 110},
        {"label": _("Total (XOF)"), "fieldname": "valeur_totale", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Statut"), "fieldname": "statut", "fieldtype": "Data", "width": 130},
        {"label": _("Demandeur"), "fieldname": "demandeur_nom", "fieldtype": "Data", "width": 140},
    ]


def get_data(filters):
    conditions = ["pv.docstatus < 2"]
    params = {}

    if filters.get("date_from"):
        conditions.append("pv.date_sortie >= %(date_from)s")
        params["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("pv.date_sortie <= %(date_to)s")
        params["date_to"] = filters["date_to"]
    if filters.get("client"):
        conditions.append("pv.client = %(client)s")
        params["client"] = filters["client"]
    if filters.get("projet"):
        conditions.append("pv.projet = %(projet)s")
        params["projet"] = filters["projet"]
    if filters.get("item_code"):
        conditions.append("it.item_code = %(item_code)s")
        params["item_code"] = filters["item_code"]
    if filters.get("warehouse"):
        conditions.append("it.warehouse = %(warehouse)s")
        params["warehouse"] = filters["warehouse"]
    if filters.get("statut"):
        conditions.append("pv.statut = %(statut)s")
        params["statut"] = filters["statut"]

    where = " AND ".join(conditions)
    sql = f"""
        SELECT
            pv.name AS pv,
            pv.date_sortie,
            pv.client_name,
            pv.projet,
            pv.chantier_libre,
            it.item_code,
            it.designation,
            it.warehouse,
            it.qte_demandee,
            it.qte_reellement_sortie,
            it.valeur_unitaire,
            it.valeur_totale,
            pv.statut,
            pv.demandeur_nom
        FROM `tabPV Sortie Materiel` pv
        INNER JOIN `tabPV Sortie Materiel Item` it ON it.parent = pv.name
        WHERE {where}
        ORDER BY pv.date_sortie DESC, pv.name DESC
    """
    return frappe.db.sql(sql, params, as_dict=True)


def get_chart(data):
    if not data:
        return None
    by_client = {}
    for r in data:
        key = r.get("client_name") or _("(sans client)")
        by_client[key] = by_client.get(key, 0) + (r.get("valeur_totale") or 0)
    top = sorted(by_client.items(), key=lambda x: -x[1])[:10]
    return {
        "data": {
            "labels": [k for k, _v in top],
            "datasets": [{"name": _("Valeur sortie XOF"), "values": [v for _k, v in top]}],
        },
        "type": "bar",
        "colors": ["#2c5aa0"],
    }


def get_summary(data):
    total_val = sum((r.get("valeur_totale") or 0) for r in data)
    total_qty = sum((r.get("qte_reellement_sortie") or r.get("qte_demandee") or 0) for r in data)
    nb_pv = len(set(r["pv"] for r in data))
    return [
        {"label": _("Lignes"), "datatype": "Int", "value": len(data)},
        {"label": _("PV distincts"), "datatype": "Int", "value": nb_pv},
        {"label": _("Quantité totale"), "datatype": "Float", "value": total_qty},
        {"label": _("Valeur totale (XOF)"), "datatype": "Currency", "value": total_val},
    ]

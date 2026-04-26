# Copyright (c) 2026, KYA-Energy Group
"""Crée les Number Cards et synchronise le Workspace Logistique."""
import frappe


NUMBER_CARDS = [
    {
        "name": "Véhicules Disponibles",
        "label": "Véhicules Disponibles",
        "document_type": "Vehicle",
        "function": "Count",
        "filters_json": '[["Vehicle","kya_statut","=","Disponible",false]]',
        "color": "#22c55e",
    },
    {
        "name": "Véhicules En Mission",
        "label": "Véhicules En Mission",
        "document_type": "Vehicle",
        "function": "Count",
        "filters_json": '[["Vehicle","kya_statut","=","En mission",false]]',
        "color": "#f59e0b",
    },
    {
        "name": "Sorties du Mois",
        "label": "Sorties du Mois",
        "document_type": "Sortie Vehicule",
        "function": "Count",
        "filters_json": '[["Sortie Vehicule","date_depart","Timespan","this month",false]]',
        "color": "#3b82f6",
    },
    {
        "name": "Docs Expirant 30j",
        "label": "Docs Expirant 30j",
        "document_type": "Document Vehicule",
        "function": "Count",
        "filters_json": '[["Document Vehicule","date_expiration","Timespan","next 30 days",false]]',
        "color": "#ef4444",
    },
]


def _ensure_number_card(spec):
    if frappe.db.exists("Number Card", spec["name"]):
        nc = frappe.get_doc("Number Card", spec["name"])
        for k, v in spec.items():
            if k != "name":
                nc.set(k, v)
        nc.is_public = 1
        nc.save(ignore_permissions=True)
        return f"updated NC: {spec['name']}"
    nc = frappe.new_doc("Number Card")
    nc.name = spec["name"]
    nc.label = spec["label"]
    nc.document_type = spec["document_type"]
    nc.function = spec["function"]
    nc.filters_json = spec["filters_json"]
    nc.color = spec.get("color")
    nc.is_public = 1
    nc.show_percentage_stats = 0
    nc.insert(ignore_permissions=True)
    return f"created NC: {spec['name']}"


def run():
    log = []
    for spec in NUMBER_CARDS:
        if frappe.db.exists("DocType", spec["document_type"]):
            log.append(_ensure_number_card(spec))
    frappe.db.commit()
    for line in log:
        print(f"  • {line}")
    print(f"✓ Number Cards Logistique configurés ({len(log)}).")
    return log


import frappe
import json

def setup_analytics():
    # 1. Create Dashboard Charts
    charts = [
        {
            "chart_name": "Répartition par Statut Stagiaire",
            "chart_type": "Count",
            "document_type": "Employee",
            "filters_json": json.dumps([["Employee", "employment_type", "=", "Intern", False]]),
            "group_by_based_on": "status",
            "type": "Donut",
            "label": "Stagiaires par Statut",
            "is_standard": 1,
            "module": "KYA HR"
        },
        {
            "chart_name": "Permissions par Mois",
            "chart_type": "Count",
            "document_type": "KYA Permission Request",
            "filters_json": json.dumps([]),
            "group_by_based_on": "creation",
            "group_by_type": "Monthly",
            "type": "Bar",
            "label": "Permissions mensuelles",
            "is_standard": 1,
            "module": "KYA HR"
        },
        {
            "chart_name": "Consommation Carburant par Véhicule",
            "chart_type": "Sum",
            "document_type": "KYA Fuel Log",
            "filters_json": json.dumps([]),
            "group_by_based_on": "vehicle",
            "aggregate_function_based_on": "cost",
            "type": "Bar",
            "label": "Coût Carburant",
            "is_standard": 1,
            "module": "KYA HR"
        }
    ]

    for chart in charts:
        if not frappe.db.exists("Dashboard Chart", chart["chart_name"]):
            doc = frappe.get_doc({"doctype": "Dashboard Chart", **chart})
            doc.insert(ignore_permissions=True)
            print(f"Chart {chart['chart_name']} created")
        else:
            print(f"Chart {chart['chart_name']} already exists")

    # 2. Create Number Cards
    cards = [
        {
            "label": "Stagiaires Actifs",
            "document_type": "Employee",
            "function": "Count",
            "filters_json": json.dumps([["Employee", "employment_type", "=", "Intern", False], ["Employee", "status", "=", "Active", False]]),
            "module": "KYA HR"
        },
        {
            "label": "Permissions en Attente",
            "document_type": "KYA Permission Request",
            "function": "Count",
            "filters_json": json.dumps([["KYA Permission Request", "status", "=", "En attente", False]]),
            "module": "KYA HR"
        }
    ]

    for card in cards:
        if not frappe.db.exists("Number Card", card["label"]):
            doc = frappe.get_doc({"doctype": "Number Card", **card, "is_standard": 1})
            doc.insert(ignore_permissions=True)
            print(f"Number Card {card['label']} created")
        else:
            print(f"Number Card {card['label']} already exists")

    frappe.db.commit()

if __name__ == "__main__":
    setup_analytics()

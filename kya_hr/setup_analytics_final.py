
import frappe
import json

def execute():
    # Dashboard Charts
    charts = [
        {
            "chart_name": "Répartition par Statut Stagiaire",
            "chart_type": "Count",
            "document_type": "Employee",
            "filters_json": json.dumps([["Employee", "employment_type", "=", "Intern", False]]),
            "group_by_based_on": "status",
            "type": "Donut",
            "number_of_groups": 10,
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
        },
        {
            "chart_name": "Utilisation des Véhicules (Sorties)",
            "chart_type": "Count",
            "document_type": "KYA Exit Ticket",
            "filters_json": json.dumps([]),
            "group_by_based_on": "vehicle",
            "type": "Bar",
            "label": "Nombre de Sorties",
            "is_standard": 1,
            "module": "KYA HR"
        }
    ]

    for chart in charts:
        if not frappe.db.exists("Dashboard Chart", chart["chart_name"]):
            frappe.get_doc({
                "doctype": "Dashboard Chart",
                **chart
            }).insert()
            print(f"Chart {chart['chart_name']} created")
        else:
            doc = frappe.get_doc("Dashboard Chart", chart["chart_name"])
            doc.update(chart)
            doc.save()
            print(f"Chart {chart['chart_name']} updated")

    # Number Cards
    cards = [
        {
            "name": "Stagiaires Actifs",
            "dt": "Employee",
            "filters": [["Employee", "employment_type", "=", "Intern", False], ["Employee", "status", "=", "Active", False]],
            "function": "Count"
        },
        {
            "name": "Permissions en Attente",
            "dt": "KYA Permission Request",
            "filters": [["KYA Permission Request", "status", "=", "En attente", False]],
            "function": "Count"
        },
        {
            "name": "Tickets de Sortie du Jour",
            "dt": "KYA Exit Ticket",
            "filters": [["KYA Exit Ticket", "departure_time", "Between", ["Today", "Today"], False]],
            "function": "Count"
        }
    ]
    
    for card in cards:
        if not frappe.db.exists("Number Card", card["name"]):
            frappe.get_doc({
                "doctype": "Number Card",
                "label": card["name"],
                "document_type": card["dt"],
                "function": card["function"],
                "filters_json": json.dumps(card["filters"]),
                "is_standard": 1,
                "module": "KYA HR"
            }).insert()
            print(f"Number Card {card['name']} created")
        else:
            doc = frappe.get_doc("Number Card", card["name"])
            doc.update({
                "document_type": card["dt"],
                "function": card["function"],
                "filters_json": json.dumps(card["filters"]),
                "module": "KYA HR"
            })
            doc.save()
            print(f"Number Card {card['name']} updated")

    frappe.db.commit()

if __name__ == "__main__":
    execute()

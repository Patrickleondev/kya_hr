import frappe
import json

def execute():
    # 1. Create Dashboard Charts for Interns
    create_intern_charts()
    
    # 2. Create Dashboard Charts for Logistics
    create_logistics_charts()
    
    # 3. Create Number Cards
    create_number_cards()

    frappe.db.commit()
    print("✅ Dashboards and Charts for KYA Extensions created successfully!")

def create_intern_charts():
    # Chart: Distribution by Status
    chart_name = "Répartition par Statut Stagiaire"
    if not frappe.db.exists("Dashboard Chart", chart_name):
        frappe.get_doc({
            "doctype": "Dashboard Chart",
            "chart_name": chart_name,
            "chart_type": "Count",
            "document_type": "Employee",
            "filters_json": json.dumps([["Employee", "employment_type", "=", "Intern", False]]),
            "group_by_based_on": "status",
            "type": "Donut",
            "number_of_groups": 10,
            "label": "Stagiaires par Statut",
            "is_standard": 1,
            "module": "kya_hr"
        }).insert()
        print(f"Chart {chart_name} created")

    # Chart: Permissions by Month
    chart_name = "Permissions par Mois"
    if not frappe.db.exists("Dashboard Chart", chart_name):
        frappe.get_doc({
            "doctype": "Dashboard Chart",
            "chart_name": chart_name,
            "chart_type": "Count",
            "document_type": "KYA Permission Request",
            "based_on": "from_date",
            "timeseries": 1,
            "time_interval": "Monthly",
            "type": "Bar",
            "label": "Volume de Permissions",
            "is_standard": 1,
            "module": "kya_hr"
        }).insert()
        print(f"Chart {chart_name} created")

def create_logistics_charts():
    # Chart: Fuel consumption per Vehicle
    chart_name = "Consommation Carburant par Véhicule"
    if not frappe.db.exists("Dashboard Chart", chart_name):
        frappe.get_doc({
            "doctype": "Dashboard Chart",
            "chart_name": chart_name,
            "chart_type": "Sum",
            "document_type": "KYA Fuel Log",
            "based_on_sum_field": "amount",
            "group_by_based_on": "vehicle",
            "type": "Bar",
            "number_of_groups": 10,
            "label": "Dépenses Carburant Total",
            "is_standard": 1,
            "module": "kya_hr"
        }).insert()
        print(f"Chart {chart_name} created")

    # Chart: Exit Tickets by Vehicle
    chart_name = "Utilisation des Véhicules (Sorties)"
    if not frappe.db.exists("Dashboard Chart", chart_name):
        frappe.get_doc({
            "doctype": "Dashboard Chart",
            "chart_name": chart_name,
            "chart_type": "Count",
            "document_type": "KYA Exit Ticket",
            "group_by_based_on": "vehicle",
            "type": "Donut",
            "label": "Fréquence de Sortie",
            "is_standard": 1,
            "module": "kya_hr"
        }).insert()
        print(f"Chart {chart_name} created")

def create_number_cards():
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
                "module": "kya_hr"
            }).insert()
            print(f"Number Card {card['name']} created")

if __name__ == "__main__":
    execute()

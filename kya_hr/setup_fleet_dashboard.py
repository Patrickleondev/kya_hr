"""
Setup Dashboard Logistique DG/DGA — KYA-Energy Group
Crée 8 Dashboard Charts + 1 Dashboard "Tableau de Bord Flotte" + 6 Number Cards
exécuté via after_migrate hook
"""
import frappe


# ───────────────────────── DASHBOARD CHARTS ─────────────────────────
DASHBOARD_CHARTS = [
    {
        "name": "Sorties Véhicules par Mois",
        "chart_type": "Count",
        "type": "Bar",
        "document_type": "Sortie Vehicule",
        "based_on": "date_depart",
        "time_interval": "Monthly",
        "timespan": "Last Year",
        "timeseries": 1,
        "color": "#2c5aa0",
        "group_by_type": "Count",
        "filters_json": "[]",
    },
    {
        "name": "Sorties par Véhicule",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Sortie Vehicule",
        "group_by_based_on": "license_plate",
        "group_by_type": "Count",
        "number_of_groups": 6,
        "color": "#28a745",
        "filters_json": "[]",
    },
    {
        "name": "Statut de la Flotte",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Vehicle",
        "group_by_based_on": "kya_statut",
        "group_by_type": "Count",
        "number_of_groups": 4,
        "color": "#ffc107",
        "filters_json": "[]",
    },
    {
        "name": "Kilométrage par Véhicule",
        "chart_type": "Sum",
        "type": "Bar",
        "document_type": "Sortie Vehicule",
        "based_on": "license_plate",
        "value_based_on": "km_parcourus",
        "group_by_type": "Sum",
        "color": "#17a2b8",
        "filters_json": '[["docstatus","=",1],["statut","=","Retour confirmé"]]',
    },
    {
        "name": "Top 10 Chauffeurs (missions)",
        "chart_type": "Group By",
        "type": "Bar",
        "document_type": "Sortie Vehicule",
        "group_by_based_on": "chauffeur_name",
        "group_by_type": "Count",
        "number_of_groups": 10,
        "color": "#6f42c1",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Sorties par Statut",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Sortie Vehicule",
        "group_by_based_on": "statut",
        "group_by_type": "Count",
        "number_of_groups": 5,
        "color": "#dc3545",
        "filters_json": "[]",
    },
    {
        "name": "Documents par Type",
        "chart_type": "Group By",
        "type": "Bar",
        "document_type": "Document Vehicule",
        "group_by_based_on": "type_document",
        "group_by_type": "Count",
        "number_of_groups": 6,
        "color": "#fd7e14",
        "filters_json": "[]",
    },
    {
        "name": "Coûts Documents par Véhicule (XOF)",
        "chart_type": "Sum",
        "type": "Bar",
        "document_type": "Document Vehicule",
        "based_on": "license_plate",
        "value_based_on": "cout_xof",
        "group_by_type": "Sum",
        "color": "#e83e8c",
        "filters_json": "[]",
    },
]


# ───────────────────────── NUMBER CARDS DG/DGA ─────────────────────────
NUMBER_CARDS = [
    {
        "name": "Total Véhicules",
        "document_type": "Vehicle",
        "function": "Count",
        "label": "Parc Total Véhicules",
        "color": "#2c5aa0",
        "filters_json": "[]",
    },
    {
        "name": "Sorties Cette Année",
        "document_type": "Sortie Vehicule",
        "function": "Count",
        "label": "Sorties cette année",
        "color": "#28a745",
        "filters_json": '[["date_depart","Timespan","this year"],["docstatus","=",1]]',
    },
    {
        "name": "Km Total Parcouru",
        "document_type": "Sortie Vehicule",
        "function": "Sum",
        "aggregate_function_based_on": "km_parcourus",
        "label": "Km parcourus (total)",
        "color": "#17a2b8",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Sorties En Cours",
        "document_type": "Sortie Vehicule",
        "function": "Count",
        "label": "Missions en cours",
        "color": "#ffc107",
        "filters_json": '[["statut","=","En mission"]]',
    },
    {
        "name": "Documents Expirés",
        "document_type": "Document Vehicule",
        "function": "Count",
        "label": "Documents expirés",
        "color": "#dc3545",
        "filters_json": '[["date_expiration","<","Today"]]',
    },
    {
        "name": "Coût Documents Année",
        "document_type": "Document Vehicule",
        "function": "Sum",
        "aggregate_function_based_on": "cout_xof",
        "label": "Coût docs cette année (XOF)",
        "color": "#6f42c1",
        "filters_json": '[["date_emission","Timespan","this year"]]',
    },
]


# ───────────────────────── DASHBOARD ─────────────────────────
DASHBOARD = {
    "name": "Tableau de Bord Flotte",
    "dashboard_name": "Tableau de Bord Flotte",
    "module": "KYA HR",
    "is_standard": 0,
    "charts": [
        {"chart": "Sorties Véhicules par Mois", "width": "Full"},
        {"chart": "Statut de la Flotte", "width": "Half"},
        {"chart": "Sorties par Statut", "width": "Half"},
        {"chart": "Sorties par Véhicule", "width": "Half"},
        {"chart": "Top 10 Chauffeurs (missions)", "width": "Half"},
        {"chart": "Kilométrage par Véhicule", "width": "Full"},
        {"chart": "Documents par Type", "width": "Half"},
        {"chart": "Coûts Documents par Véhicule (XOF)", "width": "Half"},
    ],
    "cards": [
        {"card": "Parc Total Véhicules"},
        {"card": "Sorties cette année"},
        {"card": "Km parcourus (total)"},
        {"card": "Missions en cours"},
        {"card": "Documents expirés"},
        {"card": "Coût docs cette année (XOF)"},
    ],
}


# ───────────────────────── HELPERS ─────────────────────────
def _upsert_chart(cfg):
    name = cfg["name"]
    if frappe.db.exists("Dashboard Chart", name):
        doc = frappe.get_doc("Dashboard Chart", name)
    else:
        doc = frappe.new_doc("Dashboard Chart")
        doc.chart_name = name
    for k, v in cfg.items():
        if k == "name":
            continue
        setattr(doc, k, v)
    doc.is_public = 1
    doc.is_standard = 0
    doc.save(ignore_permissions=True)
    print(f"  ✓ Chart: {name}")


def _upsert_number_card(cfg):
    label = cfg["label"]
    existing = frappe.db.exists("Number Card", {"label": label})
    if existing:
        doc = frappe.get_doc("Number Card", existing)
    else:
        doc = frappe.new_doc("Number Card")
        doc.label = label
    for k, v in cfg.items():
        if k == "name":
            continue
        setattr(doc, k, v)
    doc.is_public = 1
    doc.show_percentage_stats = 1
    doc.stats_time_interval = "Monthly"
    doc.save(ignore_permissions=True)
    print(f"  ✓ Number Card: {label}")


def _upsert_dashboard(cfg):
    name = cfg["name"]
    if frappe.db.exists("Dashboard", name):
        doc = frappe.get_doc("Dashboard", name)
        doc.charts = []
        doc.cards = []
    else:
        doc = frappe.new_doc("Dashboard")
        doc.dashboard_name = cfg["dashboard_name"]
    doc.module = cfg["module"]
    doc.is_standard = cfg.get("is_standard", 0)
    for c in cfg["charts"]:
        doc.append("charts", {"chart": c["chart"], "width": c.get("width", "Half")})
    for c in cfg["cards"]:
        doc.append("cards", {"card": c["card"]})
    doc.save(ignore_permissions=True)
    print(f"  ✓ Dashboard: {name}")


def run():
    print("=== Setup Dashboard Logistique DG/DGA ===")
    print("\n[1/3] Création des Dashboard Charts...")
    for c in DASHBOARD_CHARTS:
        try:
            _upsert_chart(c)
        except Exception as e:
            print(f"  ✗ {c['name']}: {e}")

    print("\n[2/3] Création des Number Cards...")
    for c in NUMBER_CARDS:
        try:
            _upsert_number_card(c)
        except Exception as e:
            print(f"  ✗ {c['label']}: {e}")

    print("\n[3/3] Création du Dashboard global...")
    try:
        _upsert_dashboard(DASHBOARD)
    except Exception as e:
        print(f"  ✗ Dashboard: {e}")

    frappe.db.commit()
    frappe.clear_cache()
    print(f"\n✅ Dashboard Flotte configuré ({len(DASHBOARD_CHARTS)} charts, {len(NUMBER_CARDS)} cards)")

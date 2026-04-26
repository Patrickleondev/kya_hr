"""
Dashboard Inventaire & Sorties Matériel — DG / DGA
─────────────────────────────────────────────────────────────────────
- Charts dynamiques sur PV Sortie Matériel (filtres client/projet)
- Charts inventaire (Bin, Item, Stock Entry)
- Number Cards stratégiques temps réel
- Dashboard global "Inventaire & Sorties Matériel"
"""
import frappe


# ───────────────────────── DASHBOARD CHARTS ─────────────────────────
DASHBOARD_CHARTS = [
    # ─── SORTIES MATÉRIEL ───
    {
        "name": "Sorties Matériel par Mois",
        "chart_type": "Sum",
        "type": "Line",
        "document_type": "PV Sortie Materiel",
        "based_on": "date_sortie",
        "value_based_on": "valeur_totale_xof",
        "time_interval": "Monthly",
        "timespan": "Last Year",
        "timeseries": 1,
        "color": "#2c5aa0",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Sorties Matériel par Client",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "PV Sortie Materiel",
        "group_by_based_on": "client_name",
        "group_by_type": "Sum",
        "aggregate_function_based_on": "valeur_totale_xof",
        "number_of_groups": 10,
        "color": "#28a745",
        "filters_json": '[["docstatus","=",1],["client","is","set"]]',
    },
    {
        "name": "Sorties Matériel par Projet",
        "chart_type": "Group By",
        "type": "Bar",
        "document_type": "PV Sortie Materiel",
        "group_by_based_on": "projet",
        "group_by_type": "Sum",
        "aggregate_function_based_on": "valeur_totale_xof",
        "number_of_groups": 10,
        "color": "#17a2b8",
        "filters_json": '[["docstatus","=",1],["projet","is","set"]]',
    },
    {
        "name": "Nombre de Sorties par Client",
        "chart_type": "Group By",
        "type": "Bar",
        "document_type": "PV Sortie Materiel",
        "group_by_based_on": "client_name",
        "group_by_type": "Count",
        "number_of_groups": 10,
        "color": "#fd7e14",
        "filters_json": '[["docstatus","=",1],["client","is","set"]]',
    },
    {
        "name": "Sorties par Statut Workflow",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "PV Sortie Materiel",
        "group_by_based_on": "statut",
        "group_by_type": "Count",
        "number_of_groups": 7,
        "color": "#6f42c1",
        "filters_json": "[]",
    },
    # ─── INVENTAIRE / STOCK ───
    {
        "name": "Mouvements Stock par Mois",
        "chart_type": "Count",
        "type": "Bar",
        "document_type": "Stock Entry",
        "based_on": "posting_date",
        "time_interval": "Monthly",
        "timespan": "Last Year",
        "timeseries": 1,
        "color": "#ffc107",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Stock Entries par Type",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Stock Entry",
        "group_by_based_on": "stock_entry_type",
        "group_by_type": "Count",
        "number_of_groups": 8,
        "color": "#20c997",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Articles par Groupe",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Item",
        "group_by_based_on": "item_group",
        "group_by_type": "Count",
        "number_of_groups": 10,
        "color": "#e83e8c",
        "filters_json": '[["disabled","=",0]]',
    },
]


# ───────────────────────── NUMBER CARDS ─────────────────────────
NUMBER_CARDS = [
    {
        "label": "Valeur Stock Total (XOF)",
        "document_type": "Bin",
        "function": "Sum",
        "aggregate_function_based_on": "stock_value",
        "color": "#2c5aa0",
        "filters_json": "[]",
    },
    {
        "label": "Articles en Stock",
        "document_type": "Item",
        "function": "Count",
        "color": "#28a745",
        "filters_json": '[["disabled","=",0]]',
    },
    {
        "label": "Articles Rupture",
        "document_type": "Bin",
        "function": "Count",
        "color": "#dc3545",
        "filters_json": '[["actual_qty","<=",0]]',
    },
    {
        "label": "Sorties Matériel cette année",
        "document_type": "PV Sortie Materiel",
        "function": "Count",
        "color": "#17a2b8",
        "filters_json": '[["date_sortie","Timespan","this year"],["docstatus","=",1]]',
    },
    {
        "label": "Valeur Sorties cette année (XOF)",
        "document_type": "PV Sortie Materiel",
        "function": "Sum",
        "aggregate_function_based_on": "valeur_totale_xof",
        "color": "#6f42c1",
        "filters_json": '[["date_sortie","Timespan","this year"],["docstatus","=",1]]',
    },
    {
        "label": "Sorties en attente approbation",
        "document_type": "PV Sortie Materiel",
        "function": "Count",
        "color": "#ffc107",
        "filters_json": '[["statut","in",["En attente Chef","En attente Magasin","En attente Audit","En attente DGA"]]]',
    },
    {
        "label": "Projets actifs avec sorties",
        "document_type": "PV Sortie Materiel",
        "function": "Count",
        "color": "#fd7e14",
        "filters_json": '[["projet","is","set"],["date_sortie","Timespan","this year"]]',
    },
    {
        "label": "Clients avec sorties",
        "document_type": "PV Sortie Materiel",
        "function": "Count",
        "color": "#e83e8c",
        "filters_json": '[["client","is","set"],["date_sortie","Timespan","this year"]]',
    },
]


# ───────────────────────── DASHBOARD ─────────────────────────
DASHBOARD = {
    "name": "Inventaire & Sorties Matériel",
    "dashboard_name": "Inventaire & Sorties Matériel",
    "module": "KYA HR",
    "is_standard": 0,
    "charts": [
        {"chart": "Sorties Matériel par Mois", "width": "Full"},
        {"chart": "Sorties Matériel par Client", "width": "Half"},
        {"chart": "Sorties Matériel par Projet", "width": "Half"},
        {"chart": "Nombre de Sorties par Client", "width": "Half"},
        {"chart": "Sorties par Statut Workflow", "width": "Half"},
        {"chart": "Mouvements Stock par Mois", "width": "Full"},
        {"chart": "Stock Entries par Type", "width": "Half"},
        {"chart": "Articles par Groupe", "width": "Half"},
    ],
    "cards": [
        {"card": "Valeur Stock Total (XOF)"},
        {"card": "Articles en Stock"},
        {"card": "Articles Rupture"},
        {"card": "Sorties Matériel cette année"},
        {"card": "Valeur Sorties cette année (XOF)"},
        {"card": "Sorties en attente approbation"},
        {"card": "Projets actifs avec sorties"},
        {"card": "Clients avec sorties"},
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
        # Skip charts with custom source if not registered yet — we'll handle them via DocType "Dashboard Chart Source"
        try:
            doc.append("charts", {"chart": c["chart"], "width": c.get("width", "Half")})
        except Exception as e:
            print(f"  ⚠ skip chart {c['chart']}: {e}")
    for c in cfg["cards"]:
        doc.append("cards", {"card": c["card"]})
    doc.save(ignore_permissions=True)
    print(f"  ✓ Dashboard: {name}")


def run():
    print("=== Setup Dashboard Inventaire & Sorties Matériel ===")
    print("\n[1/3] Dashboard Charts...")
    for c in DASHBOARD_CHARTS:
        try:
            _upsert_chart(c)
        except Exception as e:
            print(f"  ✗ {c['name']}: {e}")

    print("\n[2/3] Number Cards...")
    for c in NUMBER_CARDS:
        try:
            _upsert_number_card(c)
        except Exception as e:
            print(f"  ✗ {c['label']}: {e}")

    print("\n[3/3] Dashboard global...")
    try:
        _upsert_dashboard(DASHBOARD)
    except Exception as e:
        print(f"  ✗ Dashboard: {e}")

    frappe.db.commit()
    frappe.clear_cache()
    print(f"\n✅ Dashboard Inventaire & Sorties Matériel configuré "
          f"({len(DASHBOARD_CHARTS)} charts, {len(NUMBER_CARDS)} cards)")

"""Dashboard RH KYA — Chef de Service / RH / DG.

Vue agrégée sur :
  - Permissions de sortie (Employé + Stagiaire) : volumes par mois, par
    service, par employé.
  - Plannings de congé : statuts, total jours planifiés.
  - Demandes de congé (HRMS Leave Application) : approuvés / en attente.

Patterns alignés avec setup_inventaire_dashboard.py pour cohérence.
"""

import frappe


DASHBOARD_CHARTS = [
    {
        "name": "Permissions Employé par Mois",
        "chart_type": "Count",
        "type": "Line",
        "document_type": "Permission Sortie Employe",
        "based_on": "date_sortie",
        "time_interval": "Monthly",
        "timespan": "Last Year",
        "timeseries": 1,
        "color": "#1976d2",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Permissions Stagiaire par Mois",
        "chart_type": "Count",
        "type": "Line",
        "document_type": "Permission Sortie Stagiaire",
        "based_on": "date_sortie",
        "time_interval": "Monthly",
        "timespan": "Last Year",
        "timeseries": 1,
        "color": "#7c4dff",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Permissions par Service",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Permission Sortie Employe",
        "group_by_based_on": "department",
        "group_by_type": "Count",
        "number_of_groups": 10,
        "color": "#0288d1",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Plannings Congé par Statut",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Planning Conge",
        "group_by_based_on": "statut",
        "group_by_type": "Count",
        "number_of_groups": 7,
        "color": "#43a047",
        "filters_json": "[]",
    },
    {
        "name": "Total Jours Congés Planifiés par Année",
        "chart_type": "Sum",
        "type": "Bar",
        "document_type": "Planning Conge",
        "based_on": "annee",
        "value_based_on": "total_jours",
        "color": "#388e3c",
        "filters_json": '[["docstatus","=",1]]',
    },
    {
        "name": "Leave Applications par Statut (HRMS)",
        "chart_type": "Group By",
        "type": "Donut",
        "document_type": "Leave Application",
        "group_by_based_on": "status",
        "group_by_type": "Count",
        "number_of_groups": 5,
        "color": "#ff9800",
        "filters_json": "[]",
    },
]


NUMBER_CARDS = [
    {
        "label": "Permissions Employé ce mois",
        "document_type": "Permission Sortie Employe",
        "function": "Count",
        "color": "#1976d2",
        "filters_json": '[["date_sortie","Timespan","this month"],["docstatus","=",1]]',
    },
    {
        "label": "Permissions Stagiaire ce mois",
        "document_type": "Permission Sortie Stagiaire",
        "function": "Count",
        "color": "#7c4dff",
        "filters_json": '[["date_sortie","Timespan","this month"],["docstatus","=",1]]',
    },
    {
        "label": "Permissions en attente approbation",
        "document_type": "Permission Sortie Employe",
        "function": "Count",
        "color": "#fbc02d",
        "filters_json": '[["statut","in",["Brouillon","En attente Chef","En attente RH","En attente DGA","En attente DG"]]]',
    },
    {
        "label": "Plannings Congé approuvés cette année",
        "document_type": "Planning Conge",
        "function": "Count",
        "color": "#43a047",
        "filters_json": '[["statut","=","Approuvé"],["docstatus","=",1]]',
    },
    {
        "label": "Total jours planifiés cette année",
        "document_type": "Planning Conge",
        "function": "Sum",
        "aggregate_function_based_on": "total_jours",
        "color": "#2e7d32",
        "filters_json": '[["annee","=",frappe.utils.now_datetime().year],["docstatus","=",1]]',
    },
    {
        "label": "Leave Applications en attente",
        "document_type": "Leave Application",
        "function": "Count",
        "color": "#ff9800",
        "filters_json": '[["status","=","Open"]]',
    },
]


DASHBOARD = {
    "name": "Tableau de Bord RH",
    "dashboard_name": "Tableau de Bord RH",
    "module": "KYA HR",
    "is_standard": 0,
    "charts": [
        {"chart": "Permissions Employé par Mois", "width": "Half"},
        {"chart": "Permissions Stagiaire par Mois", "width": "Half"},
        {"chart": "Permissions par Service", "width": "Half"},
        {"chart": "Plannings Congé par Statut", "width": "Half"},
        {"chart": "Total Jours Congés Planifiés par Année", "width": "Full"},
        {"chart": "Leave Applications par Statut (HRMS)", "width": "Half"},
    ],
    "cards": [
        {"card": "Permissions Employé ce mois"},
        {"card": "Permissions Stagiaire ce mois"},
        {"card": "Permissions en attente approbation"},
        {"card": "Plannings Congé approuvés cette année"},
        {"card": "Total jours planifiés cette année"},
        {"card": "Leave Applications en attente"},
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
    print(f"  ✓ Chart RH: {name}")


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
    print(f"  ✓ Number Card RH: {label}")


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
        try:
            doc.append("charts", {"chart": c["chart"], "width": c.get("width", "Half")})
        except Exception as e:
            print(f"  ⚠ skip chart {c['chart']}: {e}")
    for c in cfg["cards"]:
        try:
            doc.append("cards", {"card": c["card"]})
        except Exception as e:
            print(f"  ⚠ skip card {c['card']}: {e}")
    doc.save(ignore_permissions=True)
    print(f"  ✓ Dashboard RH: {name}")


def run():
    print("=== Setup Dashboard RH ===")
    print("\n[1/3] Dashboard Charts RH...")
    for c in DASHBOARD_CHARTS:
        try:
            _upsert_chart(c)
        except Exception as e:
            print(f"  ✗ {c['name']}: {e}")
            frappe.log_error(title=f"setup_rh_dashboard chart {c['name']}",
                             message=frappe.get_traceback() + f"\n\nError: {e}")

    print("\n[2/3] Number Cards RH...")
    for c in NUMBER_CARDS:
        try:
            _upsert_number_card(c)
        except Exception as e:
            print(f"  ✗ {c['label']}: {e}")
            frappe.log_error(title=f"setup_rh_dashboard card {c['label']}",
                             message=frappe.get_traceback() + f"\n\nError: {e}")

    print("\n[3/3] Dashboard global RH...")
    try:
        _upsert_dashboard(DASHBOARD)
    except Exception as e:
        print(f"  ✗ Dashboard: {e}")
        frappe.log_error(title="setup_rh_dashboard global",
                         message=frappe.get_traceback() + f"\n\nError: {e}")

    frappe.db.commit()
    frappe.clear_cache()
    print(f"\n✅ Dashboard RH configuré "
          f"({len(DASHBOARD_CHARTS)} charts, {len(NUMBER_CARDS)} cards)")

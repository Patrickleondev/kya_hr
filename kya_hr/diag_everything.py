"""
Diagnostic complet: Number Cards, workspaces Achats/Stock, Dashboard Charts, rapports
"""
import frappe
import json


def execute():
    print("=" * 60)
    print("DIAGNOSTIC COMPLET KYA-HR")
    print("=" * 60)

    # 1. Number Cards
    print("\n--- NUMBER CARDS ---")
    ncs = frappe.db.sql("""
        SELECT name, document_type, function, filters_json, color
        FROM `tabNumber Card`
        ORDER BY name
    """, as_dict=True)
    for nc in ncs:
        print(f"  {nc.name}: doctype={nc.document_type}, fn={nc.function}")
        print(f"    filters: {nc.filters_json}")

    # 2. Dashboard Charts
    print("\n--- DASHBOARD CHARTS ---")
    charts = frappe.db.sql("""
        SELECT name, chart_name, chart_type, document_type, based_on, filters_json
        FROM `tabDashboard Chart`
        ORDER BY name
    """, as_dict=True)
    for c in charts:
        print(f"  {c.name}: type={c.chart_type}, doctype={c.document_type}, based_on={c.based_on}")
        if c.filters_json:
            print(f"    filters: {c.filters_json}")

    # 3. Workspace Achats content
    print("\n--- WORKSPACE ACHATS CONTENT ---")
    try:
        ws = frappe.get_doc("Workspace", "Buying")
        content_list = json.loads(ws.content) if ws.content else []
        for item in content_list:
            print(f"  type={item.get('type')}: {item.get('data', {})}")
    except Exception as e:
        print(f"  Erreur Buying: {e}")

    # 4. Workspace Stock content
    print("\n--- WORKSPACE STOCK CONTENT ---")
    try:
        ws = frappe.get_doc("Workspace", "Stock")
        content_list = json.loads(ws.content) if ws.content else []
        for item in content_list:
            print(f"  type={item.get('type')}: {item.get('data', {})}")
    except Exception as e:
        print(f"  Erreur Stock: {e}")

    # 5. Workspace Espace Stagiaires content
    print("\n--- WORKSPACE ESPACE STAGIAIRES CONTENT ---")
    try:
        ws = frappe.get_doc("Workspace", "Espace Stagiaires")
        content_list = json.loads(ws.content) if ws.content else []
        for item in content_list:
            print(f"  type={item.get('type')}: {item.get('data', {})}")
        print(f"  charts linked: {[c.chart_name for c in ws.charts]}")
        print(f"  links count: {len(ws.links)}")
    except Exception as e:
        print(f"  Erreur Espace Stagiaires: {e}")

    # 6. Rapports dans kya_hr
    print("\n--- RAPPORTS KYA HR ---")
    reports = frappe.db.sql("""
        SELECT name, report_name, module, report_type, ref_doctype, disabled
        FROM `tabReport`
        WHERE module = 'KYA HR'
    """, as_dict=True)
    for r in reports:
        print(f"  {r.name}: type={r.report_type}, ref={r.ref_doctype}, disabled={r.disabled}")

    # 7. HRMS Workspaces icons
    print("\n--- HRMS WORKSPACES ICONS ---")
    hrms_ws = frappe.db.sql("""
        SELECT name, label, icon, type
        FROM `tabWorkspace`
        WHERE module IN ('HR', 'Payroll', 'HRMS', 'Payroll HR')
           OR name IN ('Congés & Permissions', 'Personnes', 'Payroll', 'HR')
        ORDER BY name
    """, as_dict=True)
    for w in hrms_ws:
        print(f"  {w.name}: icon={w.icon}, type={w.type}")

    # 8. KYA Services workspace
    print("\n--- KYA SERVICES WORKSPACE ---")
    try:
        ws = frappe.get_doc("Workspace", "KYA Services")
        content_list = json.loads(ws.content) if ws.content else []
        for item in content_list:
            print(f"  type={item.get('type')}: {item.get('data', {})}")
        print(f"  charts: {[c.chart_name for c in ws.charts]}")
    except Exception as e:
        print(f"  Erreur KYA Services: {e}")

    # 9. Vérifier la NC "Répartition par Genre"
    print("\n--- NC REPARTITION PAR GENRE ---")
    try:
        nc = frappe.get_doc("Number Card", "Répartition par Genre")
        print(f"  doctype: {nc.document_type}")
        print(f"  function: {nc.function}")
        print(f"  filters_json: {nc.filters_json}")
        print(f"  color: {nc.color}")
        print(f"  aggregate_function_based_on: {nc.aggregate_function_based_on}")
    except Exception as e:
        print(f"  NC non trouvée: {e}")

    # 10. Check si le chart "Répartition par Genre" exists
    print("\n--- CHART REPARTITION PAR GENRE ---")
    try:
        chart = frappe.get_doc("Dashboard Chart", "Répartition par Genre")
        print(f"  chart_type: {chart.chart_type}")
        print(f"  document_type: {chart.document_type}")
        print(f"  based_on: {chart.based_on}")
        print(f"  value_based_on: {chart.value_based_on}")
        print(f"  filters_json: {chart.filters_json}")
    except Exception as e:
        print(f"  Chart non trouvé: {e}")

    print("\n" + "=" * 60)
    print("FIN DIAGNOSTIC")
    print("=" * 60)

import frappe
import json


def execute():
    # === NUMBER CARDS ===
    ncs = frappe.get_all(
        "Number Card",
        fields=["name", "document_type", "function", "filters_json", "color", "label", "currency"]
    )
    print("=== NUMBER CARDS ===")
    for nc in ncs:
        print(f"  {nc.name}: doc={nc.document_type}, fn={nc.function}, label={nc.label}, currency={nc.currency}")
        if nc.filters_json:
            print(f"    filters: {nc.filters_json}")

    # === ESPACE STAGIAIRES WORKSPACE ===
    try:
        ws = frappe.get_doc("Workspace", "Espace Stagiaires")
        content = json.loads(ws.content) if ws.content else []
        print(f"\n=== ESPACE STAGIAIRES CONTENT ({len(content)} items) ===")
        for item in content[:30]:
            t = item.get("type", "")
            d = item.get("data", {})
            print(f"  type={t}, id={item.get('id', '')[:8]}, data_label={d.get('label', '')}, data_link={d.get('link_to', d.get('card_name', d.get('chart_name', '')))}")
    except Exception as e:
        print(f"Error reading Espace Stagiaires: {e}")

    # === BUYING WORKSPACE ===
    try:
        ws_buying = frappe.get_doc("Workspace", "Buying")
        content_b = json.loads(ws_buying.content) if ws_buying.content else []
        print(f"\n=== BUYING CONTENT ({len(content_b)} items) ===")
        for item in content_b[:30]:
            t = item.get("type", "")
            d = item.get("data", {})
            print(f"  type={t}, data_label={d.get('label', '')}, link={d.get('link_to', d.get('card_name', d.get('chart_name', '')))}")
    except Exception as e:
        print(f"Error reading Buying: {e}")

    # === STOCK WORKSPACE ===
    try:
        ws_stock = frappe.get_doc("Workspace", "Stock")
        content_s = json.loads(ws_stock.content) if ws_stock.content else []
        print(f"\n=== STOCK CONTENT ({len(content_s)} items) ===")
        for item in content_s[:30]:
            t = item.get("type", "")
            d = item.get("data", {})
            print(f"  type={t}, data_label={d.get('label', '')}, link={d.get('link_to', d.get('card_name', d.get('chart_name', '')))}")
    except Exception as e:
        print(f"Error reading Stock: {e}")

    # === DASHBOARD CHARTS ===
    charts = frappe.get_all(
        "Dashboard Chart",
        fields=["name", "chart_type", "document_type", "based_on", "value_based_on", "filters_json"]
    )
    print("\n=== DASHBOARD CHARTS ===")
    for c in charts:
        print(f"  {c.name}: type={c.chart_type}, doc={c.document_type}, based_on={c.based_on}, value={c.value_based_on}")
        if c.filters_json and c.filters_json != "[]":
            print(f"    filters: {c.filters_json}")

    # === CHECK HRMS WORKSPACE ICONS ===
    hrms_ws = ["Conges & Permissions", "Conges et Permissions", "Personal", "Personnes",
               "Payroll", "Expenses", "Performance Management", "Recruitment"]
    print("\n=== HRMS WORKSPACE ICONS ===")
    for wname in hrms_ws:
        try:
            ws = frappe.get_doc("Workspace", wname)
            print(f"  {wname}: icon='{ws.icon}', type='{ws.type}', module='{ws.module}'")
        except Exception:
            pass

    # Broader search
    all_ws = frappe.get_all("Workspace", fields=["name", "icon", "type", "module", "is_hidden"],
                            filters={"is_hidden": 0})
    print(f"\n=== ALL VISIBLE WORKSPACES ({len(all_ws)}) ===")
    for w in all_ws:
        print(f"  {w.name}: icon='{w.icon}', type='{w.type}', module='{w.module}'")

    # === CHECK REPORT IN DB ===
    reports = frappe.get_all("Report", fields=["name", "report_name", "report_type", "module"],
                             filters={"module": "KYA HR"})
    print("\n=== KYA HR REPORTS IN DB ===")
    for r in reports:
        print(f"  {r.name}: report_name='{r.report_name}', type={r.report_type}, module={r.module}")

    # Check all reports with Presence in name
    reps = frappe.db.sql(
        "SELECT name, report_name, report_type FROM `tabReport` WHERE name LIKE '%Pr%sence%' OR name LIKE '%Presence%'",
        as_dict=True
    )
    print("\n=== PRESENCE REPORTS IN DB ===")
    for r in reps:
        print(f"  name='{r.name}', report_name='{r.report_name}', type={r.report_type}")

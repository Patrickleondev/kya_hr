"""
Restore native ERPNext Buying/Stock workspaces & fix ALL workspace icons
- Restores Buying workspace to native ERPNext v16 content
- Restores Stock workspace to native ERPNext v16 content
- Fixes all broken workspace icons (uses only valid timeless sprite names)
- Reverts bad icon changes from previous mega_fix_all.py
"""
import frappe
import json


def execute():
    log = []

    # ─── 1. RESTORE BUYING WORKSPACE ────────────────────────────────────────
    buying_content = json.dumps([
        {"id": "j3dJGo8Ok6", "type": "chart", "data": {"chart_name": "Purchase Order Trends", "col": 12}},
        {"id": "k75jSq2D6Z", "type": "number_card", "data": {"number_card_name": "Purchase Orders Count", "col": 4}},
        {"id": "UPXys0lQLj", "type": "number_card", "data": {"number_card_name": "Total Purchase Amount", "col": 4}},
        {"id": "yQGK3eb2hg", "type": "number_card", "data": {"number_card_name": "Average Order Values", "col": 4}},
        {"id": "oN7lXSwQji", "type": "spacer", "data": {"col": 12}},
        {"id": "Xe2GVLOq8J", "type": "header", "data": {"text": "<span class=\"h4\"><b>Reports &amp; Masters</b></span>", "col": 12}},
        {"id": "QwqyG6XuUt", "type": "card", "data": {"card_name": "Buying", "col": 4}},
        {"id": "bTPjOxC_N_", "type": "card", "data": {"card_name": "Items & Pricing", "col": 4}},
        {"id": "87ht0HIneb", "type": "card", "data": {"card_name": "Settings", "col": 4}},
        {"id": "EDOsBOmwgw", "type": "card", "data": {"card_name": "Supplier", "col": 4}},
        {"id": "oWNNIiNb2i", "type": "card", "data": {"card_name": "Supplier Scorecard", "col": 4}},
        {"id": "7F_13-ihHB", "type": "card", "data": {"card_name": "Key Reports", "col": 4}},
        {"id": "pfwiLvionl", "type": "card", "data": {"card_name": "Other Reports", "col": 4}},
        {"id": "8ySDy6s4qn", "type": "card", "data": {"card_name": "Regional", "col": 4}},
    ])

    try:
        exists = frappe.db.sql("SELECT name FROM `tabWorkspace` WHERE name='Buying'")
        if exists:
            frappe.db.sql(
                "UPDATE `tabWorkspace` SET content=%s, icon='buying', label='Buying', modified=NOW(), modified_by='Administrator' WHERE name='Buying'",
                (buying_content,)
            )
            log.append("✓ Buying workspace content restored (native ERPNext)")
        else:
            log.append("⚠ Workspace 'Buying' not found in DB")
    except Exception as e:
        log.append(f"✗ Buying workspace restore failed: {e}")

    # ─── 2. RESTORE STOCK WORKSPACE ─────────────────────────────────────────
    stock_content = json.dumps([
        {"id": "1cdTNYy-TO", "type": "chart", "data": {"chart_name": "Stock Value by Item Group", "col": 12}},
        {"id": "WKeeHLcyXI", "type": "number_card", "data": {"number_card_name": "Total Stock Value", "col": 4}},
        {"id": "6nVoOHuy5w", "type": "number_card", "data": {"number_card_name": "Total Warehouses", "col": 4}},
        {"id": "OUex5VED7d", "type": "number_card", "data": {"number_card_name": "Total Active Items", "col": 4}},
        {"id": "3SmmwBbOER", "type": "header", "data": {"text": "<span class=\"h4\"><b>Masters &amp; Reports</b></span>", "col": 12}},
        {"id": "OAGNH9njt7", "type": "card", "data": {"card_name": "Items Catalogue", "col": 4}},
        {"id": "jF9eKz0qr0", "type": "card", "data": {"card_name": "Stock Transactions", "col": 4}},
        {"id": "tyTnQo-MIS", "type": "card", "data": {"card_name": "Stock Reports", "col": 4}},
        {"id": "dJaJw6YNPU", "type": "card", "data": {"card_name": "Settings", "col": 4}},
        {"id": "rQf5vK4N_T", "type": "card", "data": {"card_name": "Serial No and Batch", "col": 4}},
        {"id": "7oM7hFL4v8", "type": "card", "data": {"card_name": "Tools", "col": 4}},
        {"id": "ve3L6ZifkB", "type": "card", "data": {"card_name": "Key Reports", "col": 4}},
        {"id": "8Kfvu3umw7", "type": "card", "data": {"card_name": "Other Reports", "col": 4}},
    ])

    try:
        exists = frappe.db.sql("SELECT name FROM `tabWorkspace` WHERE name='Stock'")
        if exists:
            frappe.db.sql(
                "UPDATE `tabWorkspace` SET content=%s, icon='stock', label='Stock', modified=NOW(), modified_by='Administrator' WHERE name='Stock'",
                (stock_content,)
            )
            log.append("✓ Stock workspace content restored (native ERPNext)")
        else:
            log.append("⚠ Workspace 'Stock' not found in DB")
    except Exception as e:
        log.append(f"✗ Stock workspace restore failed: {e}")

    # ─── 3. FIX ALL WORKSPACE ICONS ─────────────────────────────────────────
    # Only valid timeless sprite names are used (icon-NAME must exist in timeless/icons.svg)
    # Valid timeless: accounting, hr, buying, stock, quality, permission, education,
    #                 crm, healthcare, non-profit, project, support, integration, tool,
    #                 retail, loan, website, equity, expenses, income ...
    icon_fixes = {
        # HRMS workspaces — revert bad changes from mega_fix_all.py
        "Payroll":              "accounting",  # REVERT: calculator→accounting (valid in timeless)
        "Ressources Humaines":  "hr",          # REVERT: users→hr (valid in timeless)
        "Shift & Attendance":   "hr",          # FIX: clock→hr (milestone/clock both invalid; hr valid)
        "Personnes":            "hr",          # FIX: users→hr (users invalid; hr valid)
        # HRMS optional workspaces — fix if they exist
        "Recruitment":          "hr",          # users→hr
        "Learning":             "education",   # fix if icon is invalid
        # ERPNext workspaces — quality icon IS valid, but reset to be sure
        "Quality":              "quality",     # quality IS in timeless
        # KYA custom workspaces
        "Congés & Permissions": "permission",  # FIX: calendar→permission (permission valid in timeless)
        "Espace Stagiaires":    "education",   # education IS in timeless
        "KYA Services":         "tool",        # tool IS in timeless
    }

    for ws_name, icon in icon_fixes.items():
        try:
            exists = frappe.db.sql(
                "SELECT name, icon FROM `tabWorkspace` WHERE name=%s", (ws_name,)
            )
            if exists:
                current_icon = exists[0][1]
                frappe.db.sql(
                    "UPDATE `tabWorkspace` SET icon=%s, modified=NOW(), modified_by='Administrator' WHERE name=%s",
                    (icon, ws_name)
                )
                log.append(f"✓ Icon fixed: {ws_name}: {current_icon!r} → {icon!r}")
            else:
                log.append(f"  (skip) Workspace not found: {ws_name}")
        except Exception as e:
            log.append(f"✗ Icon fix failed for {ws_name}: {e}")

    # ─── 4. REPORT CURRENT STATE ─────────────────────────────────────────────
    try:
        rows = frappe.db.sql(
            "SELECT name, icon FROM `tabWorkspace` WHERE is_hidden=0 ORDER BY sequence_id",
            as_dict=True
        )
        log.append("\n=== WORKSPACE ICONS (all visible) ===")
        for r in rows:
            log.append(f"  {r.name!s:40s} icon={r.icon!r}")
    except Exception as e:
        log.append(f"✗ Could not read workspace list: {e}")

    frappe.db.commit()

    print("\n".join(log))

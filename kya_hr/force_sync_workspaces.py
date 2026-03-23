"""
force_sync_workspaces.py v7 — Post-migrate hook.

Recreates ALL Workspace records deleted by Frappe's orphan cleanup.
In v16, most modules have no workspace/ source dir (they use workspace_sidebar/),
so Frappe deletes the Workspace DB records during migrate.
This hook rebuilds them from the Workspace Sidebar items.
"""
import frappe
import json


# Modules Sidebar → icon mapping (used when creating Workspace records)
ICON_MAP = {
    "Stock": "stock", "Buying": "buying", "Selling": "sell",
    "CRM": "crm", "Support": "support", "Projects": "projects",
    "Manufacturing": "factory", "Assets": "assets", "Quality": "quality",
    "Home": "home", "Setup": "setting-gear", "Website": "website",
    "People": "hr", "Payroll": "accounting", "Recruitment": "users",
    "Leaves": "non-profit", "Shift & Attendance": "milestone",
    "Performance": "star", "Expenses": "expenses", "Tenure": "customer",
    "Tax & Benefits": "money-coins-1", "Personnes": "hr",
    "Accounts Setup": "accounting", "Banking": "bank",
    "Financial Reports": "chart-bar", "Invoicing": "accounting",
    "Payments": "money-coins-1", "Taxes": "money-coins-1",
    "Budget": "chart-bar", "Share Management": "share",
    "Subscription": "repeat", "Subcontracting": "organization",
    "Data": "database", "Email": "mail", "System": "setting-gear",
    "Users": "users", "Build": "tool", "Printing": "printer",
    "Automation": "setting-gear", "Integrations": "link",
    "ERPNext Settings": "setting-gear", "My Workspaces": "bookmark",
    "Ressources Humaines": "hr", "Comptabilité": "accounting",
}


def _build_workspace_from_sidebar(ws_name, sidebar):
    """Create a Workspace record with content derived from sidebar items."""
    icon = ICON_MAP.get(ws_name, sidebar.header_icon or "home")

    # Content blocks
    blocks = [
        {"id": "h1", "type": "header", "data": {
            "text": f"<div class='ellipsis' title='{ws_name}'>{ws_name}</div>",
            "level": 3, "col": 12
        }}
    ]

    # Extract top-level links for shortcuts
    link_items = [
        it for it in sidebar.items
        if it.type == "Link"
        and it.link_type in ("DocType", "Report", "Page")
        and not it.child
    ]

    shortcuts = []
    for it in link_items[:4]:
        shortcuts.append({
            "label": it.label, "type": it.link_type,
            "link_to": it.link_to, "color": "#ecf5fe",
            "doc_view": "List" if it.link_type == "DocType" else "",
        })
        blocks.append({
            "id": f"sc{len(shortcuts)}",
            "type": "shortcut",
            "data": {"shortcut_name": it.label, "col": 3}
        })

    blocks.append({"id": "sp1", "type": "spacer", "data": {"col": 12}})

    # Build link cards from sidebar sections
    links = []
    section = None
    section_links = []
    for it in sidebar.items:
        if it.type == "Section Break":
            if section and section_links:
                links.append({"type": "Card Break", "label": section,
                              "hidden": 0, "is_query_report": 0,
                              "link_count": 0, "link_type": "DocType", "onboard": 0})
                links.extend(section_links)
                section_links = []
            section = it.label
        elif it.type == "Link" and it.link_type in ("DocType", "Report", "Page") and it.link_to:
            section_links.append({
                "type": "Link", "label": it.label,
                "link_to": it.link_to, "link_type": it.link_type,
                "hidden": 0, "is_query_report": 1 if it.link_type == "Report" else 0,
                "link_count": 0, "onboard": 0
            })
    if section and section_links:
        links.append({"type": "Card Break", "label": section,
                      "hidden": 0, "is_query_report": 0,
                      "link_count": 0, "link_type": "DocType", "onboard": 0})
        links.extend(section_links)

    if not links and link_items:
        links.append({"type": "Card Break", "label": ws_name,
                      "hidden": 0, "is_query_report": 0,
                      "link_count": 0, "link_type": "DocType", "onboard": 0})
        for it in link_items:
            links.append({
                "type": "Link", "label": it.label,
                "link_to": it.link_to, "link_type": it.link_type,
                "hidden": 0, "is_query_report": 1 if it.link_type == "Report" else 0,
                "link_count": 0, "onboard": 0
            })

    # Determine module from sidebar
    module = sidebar.module or "Core"

    # Insert workspace
    ws = frappe.new_doc("Workspace")
    ws.name = ws_name
    ws.label = ws_name
    ws.module = module
    ws.icon = icon
    ws.is_hidden = 0
    ws.public = 1
    ws.content = json.dumps(blocks)
    ws.db_insert()

    # Insert shortcuts
    for idx, sc in enumerate(shortcuts, 1):
        frappe.get_doc({
            "doctype": "Workspace Shortcut",
            "parent": ws_name, "parenttype": "Workspace",
            "parentfield": "shortcuts", "idx": idx,
            "label": sc["label"], "type": sc["type"],
            "link_to": sc["link_to"], "color": sc.get("color", ""),
            "doc_view": sc.get("doc_view", ""),
        }).db_insert()

    # Insert links
    for idx, lk in enumerate(links, 1):
        frappe.get_doc({
            "doctype": "Workspace Link",
            "parent": ws_name, "parenttype": "Workspace",
            "parentfield": "links", "idx": idx,
            "type": lk["type"], "label": lk["label"],
            "link_to": lk.get("link_to"), "link_type": lk.get("link_type"),
            "hidden": lk.get("hidden", 0),
            "is_query_report": lk.get("is_query_report", 0),
            "onboard": lk.get("onboard", 0),
        }).db_insert()

    return len(shortcuts), len(links)


def execute():
    """Post-migrate hook."""
    print("=== FORCE SYNC WORKSPACES KYA v7 ===")

    # 1. KYA custom workspaces: ensure visible
    for ws_name in ["Espace Stagiaires", "Congés & Permissions", "KYA Services"]:
        if frappe.db.exists("Workspace", ws_name):
            frappe.db.set_value("Workspace", ws_name, "is_hidden", 0, update_modified=False)

    # 2. Delete obsolete custom workspaces
    for ws_name in ["Stock & Logistique", "Achats & Approvisionnement", "KYA Stagiaires"]:
        if frappe.db.exists("Workspace", ws_name):
            for child in ["Workspace Link", "Workspace Shortcut"]:
                frappe.db.delete(child, {"parent": ws_name})
            frappe.db.delete("Workspace", {"name": ws_name})
        if frappe.db.exists("Workspace Sidebar", ws_name):
            frappe.db.delete("Workspace Sidebar Item", {"parent": ws_name})
            frappe.db.delete("Workspace Sidebar", {"name": ws_name})

    # 3. Recreate ALL missing Workspace records from their Workspace Sidebar
    existing = set(w["name"] for w in frappe.get_all("Workspace", fields=["name"]))
    sidebars = frappe.get_all("Workspace Sidebar", fields=["name"])
    created = 0

    for sb in sidebars:
        if sb["name"] not in existing:
            try:
                sidebar_doc = frappe.get_doc("Workspace Sidebar", sb["name"])
                sc_count, lk_count = _build_workspace_from_sidebar(sb["name"], sidebar_doc)
                created += 1
                print(f"  [CREATE] {sb['name']} ({sc_count} shortcuts, {lk_count} links)")
            except Exception as e:
                print(f"  [ERROR] {sb['name']}: {e}")

    if created:
        print(f"  -> {created} workspaces recréés")

    frappe.db.commit()
    print("=== DONE ===")

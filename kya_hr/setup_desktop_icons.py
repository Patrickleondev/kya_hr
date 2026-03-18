"""
Setup Desktop Icons for KYA-Energy Group.
Hides broken Desktop Icons whose workspace routes can't resolve.
Run via: bench --site frontend execute kya_hr.setup_desktop_icons.execute
"""
import frappe


def execute():
    """Hide Desktop Icons that reference non-existent workspace sidebar items."""

    # Get all workspace sidebar item keys (lowercase names)
    existing_ws_keys = set()
    from frappe.desk.doctype.workspace.workspace import get_workspace_sidebar_items
    sidebar_pages = get_workspace_sidebar_items()
    if isinstance(sidebar_pages, dict) and "pages" in sidebar_pages:
        pages = sidebar_pages["pages"]
    elif isinstance(sidebar_pages, list):
        pages = sidebar_pages
    else:
        pages = []

    for page in pages:
        if isinstance(page, dict):
            name = page.get("name", page.get("title", ""))
            if name:
                existing_ws_keys.add(name.lower())
        elif isinstance(page, str):
            existing_ws_keys.add(page.lower())

    # Also add keys from boot workspace_sidebar_item
    try:
        from frappe.boot import get_bootinfo
        boot = get_bootinfo()
        if hasattr(boot, "workspace_sidebar_item"):
            wsi = boot.workspace_sidebar_item
            if isinstance(wsi, dict):
                for key, val in wsi.items():
                    items = val.get("items", []) if isinstance(val, dict) else []
                    # Only count workspaces that have Link-type items
                    has_links = any(
                        i.get("type") == "Link" for i in items
                        if isinstance(i, dict)
                    )
                    if has_links:
                        existing_ws_keys.add(key.lower())
    except Exception:
        pass

    # Get all Desktop Icons
    icons = frappe.db.sql(
        """SELECT name, label, icon_type, link_type, link_to, link, hidden
           FROM `tabDesktop Icon`
           ORDER BY label""",
        as_dict=True,
    )

    fixed = 0
    for icon in icons:
        should_hide = False
        reason = ""

        if icon.icon_type == "Folder":
            # Folder icons: check if they have child icons
            child_count = frappe.db.count(
                "Desktop Icon", {"parent_icon": icon.label}
            )
            if child_count == 0:
                # No children, will fall through to route code
                label_key = icon.label.lower()
                if label_key not in existing_ws_keys:
                    should_hide = True
                    reason = f"Folder with no children, '{label_key}' not in sidebar"

        elif icon.icon_type == "Link" and icon.link_type == "Workspace Sidebar":
            label_key = icon.label.lower()
            if label_key not in existing_ws_keys:
                should_hide = True
                reason = f"Workspace '{label_key}' not in sidebar"

        if should_hide and not icon.hidden:
            frappe.db.set_value("Desktop Icon", icon.name, "hidden", 1)
            fixed += 1
            print(f"  HIDDEN: {icon.label} ({reason})")

    # Hide stale KYA Desktop Icons that reference old/renamed workspaces
    stale_icons = ["KYA Stagiaires", "Achats KYA", "Stock KYA"]
    for label in stale_icons:
        existing = frappe.db.exists("Desktop Icon", {"label": label})
        if existing:
            frappe.db.set_value("Desktop Icon", existing, "hidden", 1)
            print(f"  HIDDEN (stale): {label}")

    # Ensure current KYA workspace icons are visible
    kya_icons = ["Espace Stagiaires", "KYA Services", "Congés & Permissions"]
    for label in kya_icons:
        existing = frappe.db.exists("Desktop Icon", {"label": label})
        if existing:
            frappe.db.set_value("Desktop Icon", existing, "hidden", 0)
            print(f"  VISIBLE: {label}")

    if fixed:
        frappe.db.commit()
        print(f"\n  Total fixes: {fixed}")
    else:
        print("  No Desktop Icon fixes needed")

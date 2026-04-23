"""
Post-migration workspace fixes for KYA-Energy.
1. Fix URL-type shortcuts losing their link_to.
2. Unhide standard Buying/Stock workspaces (hidden by earlier custom workspaces).
Run via after_migrate hook or:
  bench --site frontend execute kya_hr.fix_workspace_shortcuts.execute
"""
import frappe


def _unhide_standard_workspaces():
    """Ensure standard ERPNext workspaces Buying and Stock are visible.
    Our custom sub-workspaces use parent_page to nest under them.
    """
    changed = False
    for ws_name in ("Buying", "Stock"):
        if frappe.db.exists("Workspace", ws_name):
            is_hidden = frappe.db.get_value("Workspace", ws_name, "is_hidden")
            if is_hidden:
                frappe.db.set_value("Workspace", ws_name, "is_hidden", 0,
                                    update_modified=False)
                print(f"  UNHIDDEN workspace: {ws_name}")
                changed = True

    # Ensure our custom workspaces are nested under the standard ones
    sub_pages = {
        "Achats & Approvisionnement": "Buying",
        "Stock & Logistique": "Stock",
    }
    for ws_name, parent in sub_pages.items():
        if frappe.db.exists("Workspace", ws_name):
            current = frappe.db.get_value("Workspace", ws_name, "parent_page")
            if current != parent:
                frappe.db.set_value("Workspace", ws_name, "parent_page", parent,
                                    update_modified=False)
                print(f"  SET parent_page: {ws_name} -> {parent}")
                changed = True

    if changed:
        frappe.db.commit()


def execute():
    """Apply all post-migration workspace fixes."""
    _unhide_standard_workspaces()

    # Fix URL shortcuts with missing link_to
    broken = frappe.db.sql(
        """
        SELECT name, parent, label, url
        FROM `tabWorkspace Shortcut`
        WHERE type = 'URL' AND (link_to IS NULL OR link_to = '')
        """,
        as_dict=True,
    )
    if broken:
        for row in broken:
            frappe.db.set_value(
                "Workspace Shortcut", row["name"], "link_to", row["url"],
                update_modified=False,
            )
        frappe.db.commit()
        print(f"  Fixed {len(broken)} URL shortcut(s) with missing link_to")

"""
Fix URL-type Workspace Shortcuts that lose their link_to after migration.
Run via after_migrate hook or:
  bench --site frontend execute kya_hr.fix_workspace_shortcuts.execute
"""
import frappe


def execute():
    """Set link_to = url for URL shortcuts where link_to is missing."""
    broken = frappe.db.sql(
        """
        SELECT name, parent, label, url
        FROM `tabWorkspace Shortcut`
        WHERE type = 'URL' AND (link_to IS NULL OR link_to = '')
        """,
        as_dict=True,
    )
    if not broken:
        return

    for row in broken:
        frappe.db.set_value(
            "Workspace Shortcut", row["name"], "link_to", row["url"],
            update_modified=False,
        )

    frappe.db.commit()
    print(f"  Fixed {len(broken)} URL shortcut(s) with missing link_to")

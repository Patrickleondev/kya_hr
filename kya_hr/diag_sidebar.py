"""Diagnostiquer Workspace Sidebar - structure correcte."""
import frappe


def execute():
    # Voir les colonnes de Workspace Sidebar Item
    print("=== COLONNES tabWorkspace Sidebar Item ===")
    cols = frappe.db.sql("DESCRIBE `tabWorkspace Sidebar Item`")
    for c in cols:
        print(f"  {c[0]} ({c[1]})")

    print("\n=== COLONNES tabWorkspace Sidebar ===")
    cols2 = frappe.db.sql("DESCRIBE `tabWorkspace Sidebar`")
    for c in cols2:
        print(f"  {c[0]} ({c[1]})")

    # Voir quelques records
    print("\n=== WORKSPACE SIDEBAR RECORDS (tous) ===")
    sidebars = frappe.db.sql(
        "SELECT name, workspace, user, is_public FROM `tabWorkspace Sidebar` LIMIT 30",
        as_dict=True
    )
    for s in sidebars:
        count = frappe.db.count("Workspace Sidebar Item", {"parent": s.name})
        print(f"  [{s.workspace}] user={s.user} public={s.is_public} items={count}")
    print(f"  Total: {len(sidebars)}")

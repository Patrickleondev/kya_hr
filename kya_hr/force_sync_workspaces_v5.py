"""
force_sync_workspaces.py v5 — Minimal, ne touche PAS aux workspaces natifs.

Ne gère que les workspaces KYA custom :
  - Espace Stagiaires
  - Congés & Permissions

Ne modifie PAS : Stock, Buying, Personnes, Payroll, Shift & Attendance, etc.
"""
import frappe


def execute():
    """Post-migrate hook. Ne restaure/modifie que les workspaces KYA."""
    print("=== FORCE SYNC WORKSPACES KYA v5 (minimal) ===")

    # S'assurer que les workspaces KYA custom sont visibles
    for ws_name in ["Espace Stagiaires", "Congés & Permissions", "KYA Services"]:
        if frappe.db.exists("Workspace", ws_name):
            frappe.db.set_value("Workspace", ws_name, "is_hidden", 0, update_modified=False)
            print(f"  [OK] {ws_name} visible")

    # Supprimer les anciens workspaces custom obsolètes s'ils réapparaissent
    for ws_name in ["Stock & Logistique", "Achats & Approvisionnement", "KYA Stagiaires"]:
        if frappe.db.exists("Workspace", ws_name):
            for child in ["Workspace Link", "Workspace Shortcut"]:
                frappe.db.delete(child, {"parent": ws_name})
            frappe.db.delete("Workspace", {"name": ws_name})
            print(f"  [DEL] {ws_name}")
        if frappe.db.exists("Workspace Sidebar", ws_name):
            frappe.db.delete("Workspace Sidebar Item", {"parent": ws_name})
            frappe.db.delete("Workspace Sidebar", {"name": ws_name})
            print(f"  [DEL] {ws_name} sidebar")

    frappe.db.commit()
    print("=== DONE ===")

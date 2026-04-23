"""Diagnostiquer et corriger les workspaces Buying/Stock en DB."""
import frappe


def execute():
    wss = ["Buying", "Stock", "Achats & Approvisionnement",
           "Stock & Logistique", "KYA Services", "Espace Stagiaires"]
    print("=== ETAT WORKSPACES ===")
    for ws in wss:
        r = frappe.db.get_value(
            "Workspace", ws,
            ["name", "is_hidden", "parent_page", "sequence_id"],
            as_dict=True
        )
        if r:
            print(f"  {r['name']} | hidden={r['is_hidden']} | parent={r['parent_page']!r} | seq={r['sequence_id']}")
        else:
            print(f"  {ws} -> NOT FOUND")

    # Force apply parent_page for our custom sub-workspaces
    sub_workspaces = {
        "Achats & Approvisionnement": "Buying",
        "Stock & Logistique": "Stock",
    }
    changed = False
    for ws_name, parent in sub_workspaces.items():
        if frappe.db.exists("Workspace", ws_name):
            current_parent = frappe.db.get_value("Workspace", ws_name, "parent_page")
            if current_parent != parent:
                frappe.db.set_value("Workspace", ws_name, "parent_page", parent,
                                    update_modified=False)
                print(f"  >> SET parent_page: {ws_name} -> {parent}")
                changed = True

    # Unhide Buying and Stock if needed
    for ws in ["Buying", "Stock"]:
        if frappe.db.exists("Workspace", ws):
            h = frappe.db.get_value("Workspace", ws, "is_hidden")
            if h:
                frappe.db.set_value("Workspace", ws, "is_hidden", 0, update_modified=False)
                print(f"  >> UNHIDDEN: {ws}")
                changed = True

    if changed:
        frappe.db.commit()
        print("  >> Commit done")
    else:
        print("  >> Nothing to change")

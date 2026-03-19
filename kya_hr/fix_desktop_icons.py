"""
fix_desktop_icons.py - v2
--------------------------
Corrige les Desktop Icons pour qu'ils correspondent aux Workspace Sidebar.

Architecture Frappe v16:
  Desktop Icon.label -> frappe.boot.workspace_sidebar_item[label.lower()]
  La cle vient du NOM des Workspace Sidebar records (pas des Workspace DocType).
"""

# Labels qui ont ete modifies et doivent etre REVERTS vers l original
LABEL_REVERT = {
    "Conges & Permissions": None,  # placeholder
}


def execute():
    import frappe
    from frappe.boot import get_sidebar_items

    ws_names = [w["name"] for w in frappe.get_all("Workspace", filters={"is_hidden": 0})]
    sidebar_items = get_sidebar_items(ws_names)
    print(f"[fix_desktop_icons v2] {len(sidebar_items)} Workspace Sidebar keys")
    print("Keys:", sorted(sidebar_items.keys()))

    icons = frappe.get_all("Desktop Icon",
        fields=["name", "label", "link_type", "hidden"],
    )
    print(f"[fix_desktop_icons v2] {len(icons)} Desktop Icons")

    # Revert incorrectly changed labels
    revert_map = {}

    import frappe as _f
    # Read the current labels to find ones that were changed
    for ic in icons:
        name = ic["name"]
        label = ic.get("label") or ""
        link_type = ic.get("link_type") or ""
        hidden = ic.get("hidden", 0)

        # Icons whose names differ from labels (were relabeled)
        if name != label and link_type == "Workspace Sidebar":
            # name is the original English value, label is the modified value
            print(f"  MISMATCH: name={name!r} != label={label!r}")

    # Now fix based on name vs label mismatch
    reverted = 0
    hidden_count = 0

    for ic in icons:
        name = ic["name"]
        label = ic.get("label") or ""
        link_type = ic.get("link_type") or ""
        current_hidden = ic.get("hidden", 0)

        if link_type == "External":
            continue

        # The Desktop Icon name IS the original label in Frappe
        # If name != label, label was changed - revert it
        if name != label:
            # Revert to name (original)
            frappe.db.set_value("Desktop Icon", name, "label", name)
            print(f"  [REVERT] {label!r} -> {name!r}")
            reverted += 1
            label = name

        # Check if sidebar exists for this label
        key = label.lower()
        sidebar = sidebar_items.get(key)
        items = sidebar.get("items") or [] if sidebar else []
        link_items = [i for i in items if i.get("type") == "Link"]

        if not sidebar or not link_items:
            if not current_hidden:
                frappe.db.set_value("Desktop Icon", name, "hidden", 1)
                reason = "no sidebar" if not sidebar else "0 link items"
                print(f"  [HIDE] {label!r}: {reason}")
                hidden_count += 1

    frappe.db.commit()
    frappe.clear_cache()

    print(f"\nReverted: {reverted}, Hidden: {hidden_count}")

    # Final state
    print("\n=== Final VISIBLE icons ===")
    final = frappe.get_all("Desktop Icon",
        fields=["name", "label", "link_type", "hidden"],
        filters={"hidden": 0}
    )
    for ic in sorted(final, key=lambda x: x["label"] or ""):
        if (ic.get("link_type") or "") != "External":
            key = (ic["label"] or "").lower()
            sidebar = sidebar_items.get(key)
            lc = len([i for i in (sidebar.get("items") or []) if i.get("type") == "Link"]) if sidebar else 0
            status = f"OK ({lc} links)" if sidebar and lc > 0 else "BROKEN"
            print(f"  {ic['label']!r}: {status}")

#!/usr/bin/env python3
"""Diagnostic script - run with:
docker cp diag_ws2.py kya-8083-backend-8083-1:/tmp/ 
docker exec kya-8083-backend-8083-1 bash -c "cd /home/frappe/frappe-bench && bench --site frontend execute frappe.db.sql --args '[\"SELECT name, is_hidden FROM tabWorkspace LIMIT 3\"]'"
"""
# This script is called via bench execute kya_hr.diag_ws.run
import frappe

def run():
    # Check modules registered
    mods = frappe.db.sql("SELECT name, app_name FROM `tabModule Def` WHERE app_name IN ('kya_hr','kya_services') ORDER BY name", as_dict=True)
    print(f"\n=== Modules kya_hr + kya_services ({len(mods)}) ===")
    for m in mods:
        print(f"  {m.app_name} -> {m.name}")

    # Check workspace module field for our targets
    ws = frappe.db.sql("SELECT name, module, `public`, is_hidden, parent_page FROM tabWorkspace WHERE name IN ('KYA Services','Espace Stagiaires') OR name LIKE '%quipe%'", as_dict=True)
    print(f"\n=== Target workspaces ===")
    for w in ws:
        print(f"  {w.name} | module={w.module} | pub={w.get('public')} | hidden={w.is_hidden} | parent={w.parent_page}")

    # Count root workspaces by module
    print("\n=== Root workspaces by module ===")
    minfo = frappe.db.sql("SELECT module, COUNT(*) as cnt FROM tabWorkspace WHERE (parent_page='' OR parent_page IS NULL) AND is_hidden=0 AND `public`=1 GROUP BY module ORDER BY module", as_dict=True)
    for m in minfo:
        print(f"  {m.module or '(none)'} -> {m.cnt}")

    # Check installed apps from global defaults
    print("\n=== Installed Apps (frappe.get_installed_apps) ===")
    installed = frappe.get_installed_apps()
    print(f"  {installed}")

    print("\n=== installed_apps from DB global ===")
    raw = frappe.db.get_global("installed_apps") or "[]"
    print(f"  {raw}")

    print("\n=== Desktop Icons (targets) ===")
    icons = frappe.get_all(
        "Desktop Icon",
        fields=["label", "icon_type", "app", "parent_icon", "hidden", "link_type", "link_to", "standard", "sidebar", "owner"],
        filters={"label": ["in", ["KYA HR", "KYA Services", "Espace Stagiaires", "Gestion Équipe", "Espace Employes"]]},
        order_by="label asc",
    )
    for icon in icons:
        print(
            f"  {icon.label} | type={icon.icon_type} | app={icon.app} | parent={icon.parent_icon} | "
            f"hidden={icon.hidden} | standard={icon.standard} | sidebar={icon.sidebar} | owner={icon.owner} | "
            f"link_type={icon.link_type} | link_to={icon.link_to}"
        )

    print("\n=== Desktop Layout (Administrator) ===")
    try:
        layout = frappe.get_doc("Desktop Layout", frappe.session.user).layout or "{}"
        print(layout)
    except Exception as exc:
        print(f"  no layout: {exc}")

    print("\n=== Desktop Icon count by direct query ===")
    direct_icons = frappe.get_all(
        "Desktop Icon",
        fields=["label", "icon_type", "hidden", "parent_icon", "standard"],
        filters={"standard": 1},
        order_by="idx asc",
    )
    print(f"  total={len(direct_icons)}")
    for icon in direct_icons[:20]:
        print(
            f"  {icon.label} | type={icon.icon_type} | hidden={icon.hidden} | "
            f"parent={icon.parent_icon} | standard={icon.standard}"
        )

    print("\n=== get_desktop_icons() labels ===")
    from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons
    desktop_icons = get_desktop_icons(user="Administrator")
    print(f"  total={len(desktop_icons)}")
    for icon in desktop_icons:
        print(f"  {icon.label} | type={icon.icon_type} | hidden={icon.hidden} | parent={icon.parent_icon}")

    # Old run() code below
    rows = frappe.db.sql(
        "SELECT name, is_hidden, `public`, parent_page, icon FROM tabWorkspace ORDER BY parent_page, name",
        as_dict=True
    )
    print(f"\nTotal: {len(rows)} workspaces")
    for r in rows:
        parent = r.parent_page or "(ROOT)"
        hidden = "HIDDEN" if r.is_hidden else "vis"
        pub = "pub" if r.get("public") else "priv"
        print(f"  [{pub}/{hidden}] {parent:20s} → {r.name} (icon={r.icon})")


def quick_check():
    cards = [
        "Stagiaires Actifs",
        "Permissions Stagiaires en Attente",
        "Bilans de Stage Soumis",
        "Réponses Reçues",
    ]
    print("=== Number Card filters ===")
    for card in cards:
        val = frappe.db.get_value("Number Card", card, "filters_json")
        print(f"  {card}: {val}")

    print("\n=== Number Card names like '%Stag%' ===")
    for row in frappe.get_all("Number Card", filters={"name": ["like", "%Stag%"]}, fields=["name", "document_type"], order_by="name asc"):
        print(f"  {row.name} ({row.document_type})")

    print("\n=== Doctype existence ===")
    for dt in ["Permission Sortie Stagiaire", "Bilan Fin de Stage"]:
        print(f"  {dt}: {bool(frappe.db.exists('DocType', dt))}")

    print("\n=== Desktop Layout contains Espace Stagiaires ===")
    rows = frappe.db.sql(
        "SELECT user, CASE WHEN layout LIKE %s THEN 1 ELSE 0 END as has_stag FROM `tabDesktop Layout` ORDER BY user",
        ("%Espace Stagiaires%",),
        as_dict=True,
    )
    for row in rows:
        print(f"  {row.user}: {row.has_stag}")

"""
fix_desktop_icons.py - v3
--------------------------
Crée les Desktop Icons manquantes pour les workspaces kya_hr en français.
Ces workspaces ont des noms avec accents et ne sont pas auto-détectés par
create_desktop_icons_from_workspace() (bug avec la validation des liens).
"""
import frappe


def execute():
    from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache

    # Workspaces kya_hr/hrms qui manquent de Desktop Icons avec link_type="Workspace Sidebar"
    targets = [
        {"label": "Congés & Permissions", "icon": "calendar", "app": "kya_hr"},
        {"label": "Personnes",            "icon": "users",    "app": "hrms"},
        {"label": "Espace Stagiaires",    "icon": "education","app": "kya_hr"},
    ]

    for item in targets:
        label = item["label"]
        exists = frappe.db.get_value("Desktop Icon", {"label": label}, "name")
        if exists:
            current_lt = frappe.db.get_value("Desktop Icon", exists, "link_type")
            if current_lt != "Workspace Sidebar":
                frappe.db.set_value("Desktop Icon", exists, {
                    "link_type": "Workspace Sidebar",
                    "link_to": label,
                })
                print(f"  [FIX] '{label}' link_type: {current_lt} -> Workspace Sidebar")
            else:
                print(f"  [OK]  '{label}' deja configure (link_type=Workspace Sidebar)")
            continue

        # Créer la Desktop Icon manquante
        di = frappe.new_doc("Desktop Icon")
        di.label = label
        di.link_type = "Workspace Sidebar"
        di.link_to = label
        di.icon_type = "Link"
        di.icon = item["icon"]
        di.app = item["app"]
        di.standard = 1
        di.hidden = 0
        di.flags.ignore_permissions = True
        di.flags.ignore_links = True
        di.insert(ignore_if_duplicate=True)
        print(f"  [OK] Desktop Icon '{label}' creee (link_type=Workspace Sidebar)")

    frappe.db.commit()
    clear_desktop_icons_cache()

    # Résumé
    print("\n=== Resume Desktop Icons ===")
    for item in targets:
        label = item["label"]
        di = frappe.db.get_value(
            "Desktop Icon", {"label": label},
            ["name", "link_type", "link_to", "hidden"],
            as_dict=True
        )
        if di:
            print(f"  {label}: link_type={di.link_type}, hidden={di.hidden}")
        else:
            print(f"  {label}: NOT FOUND")

    print("\nDone. Effacez le cache et reconnectez-vous.")


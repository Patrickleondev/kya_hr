"""
fix_hrms_sidebar.py
-------------------
Crée les Workspace Sidebars manquantes pour les workspaces kya_hr renommés en français.

Problème : En Frappe v16, les icônes de la grille d'accueil utilisent
           frappe.boot.workspace_sidebar_item[label.toLowerCase()]
           pour calculer la route. Si aucun Workspace Sidebar n'a ce nom,
           la route est null → erreur "Icon is not correctly configured".

Workspaces kya_hr affectés :
  - "Congés & Permissions"  → sidebar source : "Leaves" (hrms)
  - "Personnes"             → sidebar source : "People"  (hrms)
  - "Espace Stagiaires"     → sidebar source : "KYA Stagiaires" (kya_hr)
"""
import frappe


def _copy_sidebar(source_name, target_name, target_app="kya_hr", label=None):
    """Copie une Workspace Sidebar existante sous un nouveau nom."""
    if frappe.db.exists("Workspace Sidebar", target_name):
        count = frappe.db.count("Workspace Sidebar Item", {"parent": target_name})
        print(f"  [SKIP] Sidebar '{target_name}' déjà présente ({count} items)")
        return False

    if not frappe.db.exists("Workspace Sidebar", source_name):
        print(f"  [WARN] Source sidebar '{source_name}' introuvable")
        return False

    src = frappe.get_doc("Workspace Sidebar", source_name)

    new_sidebar = frappe.new_doc("Workspace Sidebar")
    new_sidebar.name = target_name
    new_sidebar.title = target_name  # requis pour l'autoname
    new_sidebar.app = target_app
    new_sidebar.module = src.module
    new_sidebar.header_icon = src.header_icon
    new_sidebar.flags.name_set = True  # forcer le name

    for item in src.items:
        new_sidebar.append("items", {
            "type": item.type,
            "label": item.label,
            "link_type": item.link_type,
            "link_to": item.link_to,
            "icon": item.icon,
            "child": item.child,
            "collapsible": item.collapsible,
            "indent": item.indent,
            "keep_closed": item.keep_closed,
            "display_depends_on": item.display_depends_on,
            "url": item.url,
            "show_arrow": item.show_arrow,
            "filters": item.filters,
            "route_options": item.route_options,
            "navigate_to_tab": item.navigate_to_tab,
        })

    # Insérer le doc sans déclencher les hooks pour éviter les conflits
    new_sidebar.flags.ignore_permissions = True
    new_sidebar.flags.ignore_mandatory = True
    new_sidebar.flags.ignore_links = True
    new_sidebar.insert(ignore_if_duplicate=True)
    frappe.db.commit()

    count = len(new_sidebar.items)
    print(f"  [OK] Sidebar '{target_name}' créée ({count} items depuis '{source_name}')")
    return True


def _ensure_sidebar_has_link(sidebar_name):
    """Vérifie qu'une sidebar a au moins un item de type 'Link'."""
    links = frappe.db.count("Workspace Sidebar Item", {
        "parent": sidebar_name,
        "type": "Link"
    })
    if links == 0:
        print(f"  [WARN] Sidebar '{sidebar_name}' n'a aucun item 'Link' - la route sera null !")
    else:
        print(f"  [INFO] Sidebar '{sidebar_name}': {links} link(s) présent(s)")
    return links > 0


def execute():
    print("=== FIX HRMS WORKSPACE SIDEBARS ===\n")

    # ----------------------------------------------------------------
    # 1. Congés & Permissions  (workspace kya_hr)
    #    source HRMS : "Leaves" ou "Tax & Benefits" ou custom
    # ----------------------------------------------------------------
    print("1. Congés & Permissions :")
    # Essayer plusieurs sources dans l'ordre de préférence
    for source in ["Leaves", "Tax & Benefits", "Tenure"]:
        if frappe.db.exists("Workspace Sidebar", source):
            _copy_sidebar(source, "Congés & Permissions", target_app="kya_hr")
            break
    else:
        # Créer une sidebar minimale si aucune source trouvée
        if not frappe.db.exists("Workspace Sidebar", "Congés & Permissions"):
            _create_minimal_sidebar(
                name="Congés & Permissions",
                app="kya_hr",
                links=[
                    ("Permission Sortie Employe", "Permission de Sortie Employé"),
                    ("Planning Conge", "Planning de Congé"),
                    ("Leave Application", "Demande de Congé"),
                    ("Attendance", "Présences"),
                ]
            )

    _ensure_sidebar_has_link("Congés & Permissions")

    # ----------------------------------------------------------------
    # 2. Personnes  (workspace hrms renommé depuis "People")
    # ----------------------------------------------------------------
    print("\n2. Personnes :")
    _copy_sidebar("People", "Personnes", target_app="hrms")
    _ensure_sidebar_has_link("Personnes")

    # ----------------------------------------------------------------
    # 3. Espace Stagiaires (workspace kya_hr sous KYA Stagiaires)
    #    → Peut déjà avoir une sidebar "KYA Stagiaires" ou "Espace Stagiaires"
    # ----------------------------------------------------------------
    print("\n3. Espace Stagiaires :")
    if not frappe.db.exists("Workspace Sidebar", "Espace Stagiaires"):
        if frappe.db.exists("Workspace Sidebar", "KYA Stagiaires"):
            _copy_sidebar("KYA Stagiaires", "Espace Stagiaires", target_app="kya_hr")
        else:
            _create_minimal_sidebar(
                name="Espace Stagiaires",
                app="kya_hr",
                links=[
                    ("Permission Sortie Stagiaire", "Permissions"),
                    ("Bilan Fin de Stage", "Bilans de Stage"),
                    ("Attendance", "Présences"),
                ]
            )
        _ensure_sidebar_has_link("Espace Stagiaires")
    else:
        count = frappe.db.count("Workspace Sidebar Item", {"parent": "Espace Stagiaires"})
        print(f"  [SKIP] Sidebar 'Espace Stagiaires' déjà présente ({count} items)")

    # ----------------------------------------------------------------
    # 4. Vérifier que les workspaces eux-mêmes ont is_hidden=0
    # ----------------------------------------------------------------
    print("\n4. Vérification visibilité :")
    for ws_name in ["Congés & Permissions", "Personnes", "Espace Stagiaires"]:
        hidden = frappe.db.get_value("Workspace", ws_name, "is_hidden")
        if hidden:
            frappe.db.set_value("Workspace", ws_name, "is_hidden", 0)
            frappe.db.commit()
            print(f"  [FIX] {ws_name} — rendu visible")
        else:
            print(f"  [OK]  {ws_name} — déjà visible")

    # ----------------------------------------------------------------
    # 5. Résumé
    # ----------------------------------------------------------------
    print("\n=== RÉSUMÉ SIDEBARS ===")
    for ws_name in ["Congés & Permissions", "Personnes", "Espace Stagiaires", "KYA Stagiaires", "KYA Services"]:
        ws = frappe.db.get_value("Workspace Sidebar", ws_name, "name")
        count = frappe.db.count("Workspace Sidebar Item", {"parent": ws_name}) if ws else 0
        status = f"{count} items" if ws else "ABSENTE ❌"
        print(f"  {ws_name}: {status}")

    frappe.db.commit()
    print("\nDone. Relancez clear-cache et redémarrez les services.")


def _create_minimal_sidebar(name, app, links):
    """Crée une Workspace Sidebar minimale avec les liens donnés."""
    if frappe.db.exists("Workspace Sidebar", name):
        return
    ws = frappe.new_doc("Workspace Sidebar")
    ws.name = name
    ws.title = name
    ws.app = app
    ws.flags.name_set = True
    for doctype, label in links:
        ws.append("items", {
            "type": "Link",
            "label": label,
            "link_type": "DocType",
            "link_to": doctype,
            "icon": "",
        })
    ws.flags.ignore_permissions = True
    ws.flags.ignore_mandatory = True
    ws.flags.ignore_links = True
    ws.insert(ignore_if_duplicate=True)
    frappe.db.commit()
    print(f"  [OK] Sidebar minimale '{name}' créée ({len(links)} links)")

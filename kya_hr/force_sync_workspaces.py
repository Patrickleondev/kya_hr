"""
force_sync_workspaces.py v10 -- Post-migrate hook (KYA).

Regles :
  1. Ne JAMAIS creer de workspaces programmatiquement (les JSON files gerent ca)
  2. Supprimer les workspaces et sidebars orphelins crees par les anciennes versions
  3. S'assurer que les workspaces KYA JSON sont visibles
  4. Corriger le module de KYA Services si necessaire
  5. Creer le Workspace Sidebar pour KYA Services s'il manque
  6. Creer le Workspace Sidebar pour Espace Stagiaires s'il manque
  7. Corriger le champ app de Gestion Equipe
"""
import frappe
import json


# Workspaces orphelins a supprimer (crees par d'anciennes versions du script)
ORPHAN_WORKSPACES = ["KYA Stagiaires", "Conges & Permissions"]

# Workspace Sidebars orphelins a supprimer
ORPHAN_SIDEBARS = ["KYA Stagiaires", "Personnes"]

# Workspaces geres par les fichiers JSON (on s'assure juste qu'ils sont visibles)
KYA_WORKSPACES = [
    "Espace Employes",
    "Espace Employés",
    "Espace Stagiaires",
    "KYA Services",
    "Gestion Équipe",
    "Gestion Equipe",
    "Espace Achats",
    "Espace Stock",
    "Espace RH",
    "Espace Comptabilité",
    "Espace Direction",
    "Logistique",
    "Inventaire & Sorties Matériel",
]

# Sidebar a auto-creer si manquant : (titre, icon Lucide, workspace_name, items)
KYA_AUTO_SIDEBARS = [
    {
        "title": "Espace Achats",
        "icon": "shopping-cart",
        "module": "KYA HR",
        "app": "kya_hr",
        "workspace": "Espace Achats",
        "items": [
            {"label": "Demandes d'Achat", "link_to": "Demande Achat KYA", "link_type": "DocType", "icon": "shopping-cart"},
            {"label": "Bons de Commande", "link_to": "Bon Commande KYA", "link_type": "DocType", "icon": "file-text"},
            {"label": "Appels d'Offre", "link_to": "Appel Offre KYA", "link_type": "DocType", "icon": "megaphone"},
        ],
    },
    {
        "title": "Espace Stock",
        "icon": "package",
        "module": "KYA HR",
        "app": "kya_hr",
        "workspace": "Espace Stock",
        "items": [
            {"label": "PV Sortie Matériel", "link_to": "PV Sortie Materiel", "link_type": "DocType", "icon": "upload"},
            {"label": "PV Entrée Matériel", "link_to": "PV Entree Materiel", "link_type": "DocType", "icon": "download"},
            {"label": "Articles", "link_to": "Item", "link_type": "DocType", "icon": "box"},
        ],
    },
    {
        "title": "Espace RH",
        "icon": "users",
        "module": "KYA HR",
        "app": "kya_hr",
        "workspace": "Espace RH",
        "items": [
            {"label": "Permissions Sortie Employé", "link_to": "Permission Sortie Employe", "link_type": "DocType", "icon": "log-out"},
            {"label": "Permissions Sortie Stagiaire", "link_to": "Permission Sortie Stagiaire", "link_type": "DocType", "icon": "log-out"},
            {"label": "Demandes de Congé", "link_to": "Leave Application", "link_type": "DocType", "icon": "calendar"},
            {"label": "Plannings Congé", "link_to": "Planning Conge", "link_type": "DocType", "icon": "calendar"},
        ],
    },
    {
        "title": "Espace Comptabilité",
        "icon": "wallet",
        "module": "KYA HR",
        "app": "kya_hr",
        "workspace": "Espace Comptabilité",
        "items": [
            {"label": "Brouillards de Caisse", "link_to": "Brouillard Caisse", "link_type": "DocType", "icon": "book"},
            {"label": "États Récap Chèques", "link_to": "Etat Recap Cheques", "link_type": "DocType", "icon": "file-text"},
        ],
    },
    {
        "title": "Direction Générale",
        "icon": "briefcase",
        "module": "KYA HR",
        "app": "kya_hr",
        "workspace": "Espace Direction",
        "items": [
            {"label": "Tableau de Bord Global", "url": "/app/dashboard-view", "link_type": "URL", "icon": "bar-chart"},
            {"label": "Demandes d'Achat", "link_to": "Demande Achat KYA", "link_type": "DocType", "icon": "shopping-cart"},
            {"label": "Permissions Employé", "link_to": "Permission Sortie Employe", "link_type": "DocType", "icon": "log-out"},
            {"label": "Contrats KYA", "link_to": "Contrat KYA", "link_type": "DocType", "icon": "file"},
        ],
    },
    {
        "title": "Logistique",
        "icon": "truck",
        "module": "KYA HR",
        "app": "kya_hr",
        "workspace": "Logistique",
        "items": [
            {"label": "Sorties Véhicule", "link_to": "Sortie Vehicule", "link_type": "DocType", "icon": "log-out"},
            {"label": "Véhicules", "link_to": "Vehicle", "link_type": "DocType", "icon": "truck"},
            {"label": "Documents Véhicule", "link_to": "Document Vehicule", "link_type": "DocType", "icon": "alert-triangle"},
        ],
    },
]


def _resolve_existing_workspace(candidates):
    for ws_name in candidates:
        if frappe.db.exists("Workspace", ws_name):
            return ws_name
    return None


def _resolve_existing_sidebar(candidates):
    for sidebar_title in candidates:
        sidebar_name = frappe.db.exists("Workspace Sidebar", {"title": sidebar_title})
        if sidebar_name:
            return sidebar_name, sidebar_title
    return None, None


def _ensure_sidebar_home_link(sidebar_title, workspace_name):
    """Make sure sidebar has a first workspace link so desktop icon can resolve a route."""
    sidebar_name = frappe.db.exists("Workspace Sidebar", {"title": sidebar_title})
    if not sidebar_name:
        return
    has_workspace_link = frappe.db.exists(
        "Workspace Sidebar Item",
        {
            "parent": sidebar_name,
            "link_type": "Workspace",
            "link_to": workspace_name,
        },
    )
    if has_workspace_link:
        return

    item = frappe.new_doc("Workspace Sidebar Item")
    item.parent = sidebar_name
    item.parenttype = "Workspace Sidebar"
    item.parentfield = "items"
    item.type = "Link"
    item.label = "Home"
    item.link_type = "Workspace"
    item.link_to = workspace_name
    item.icon = "home"
    item.insert(ignore_permissions=True)
    print(f"  [SIDEBAR LINK] {sidebar_title} -> Workspace:{workspace_name}")


def _link_desktop_icon_to_sidebar(label, sidebar_candidates):
    """Desktop icons must point to Workspace Sidebar for route resolution in Frappe desk."""
    icon_name = frappe.db.exists("Desktop Icon", {"label": label})
    sidebar_name, sidebar_title = _resolve_existing_sidebar(sidebar_candidates)
    if not sidebar_name:
        return

    # Recreate icon if it was deleted by previous broken fixes.
    if not icon_name:
        icon_doc = frappe.new_doc("Desktop Icon")
        icon_doc.label = label
        icon_doc.icon_type = "Link"
        icon_doc.icon = "folder-normal"
        icon_doc.standard = 1
        icon_doc.hidden = 0
        icon_doc.link_type = "Workspace Sidebar"
        icon_doc.link_to = sidebar_name
        icon_doc.insert(ignore_permissions=True)
        print(f"  [ICON CREATED] {label} -> Sidebar:{sidebar_title}")
        return

    frappe.db.set_value("Desktop Icon", icon_name, {
        "link_type": "Workspace Sidebar",
        "link": "",
        "link_to": sidebar_name,
        "hidden": 0,
    }, update_modified=False)
    print(f"  [ICON LINK] {label} -> Sidebar:{sidebar_title}")


def _sidebar_exists(title):
    """Check sidebar existence by both document name and title."""
    return bool(
        frappe.db.exists("Workspace Sidebar", title)
        or frappe.db.exists("Workspace Sidebar", {"title": title})
    )


def _upsert_workspace_shortcut(workspace_name, label, link_type, link_to=None, url=None, icon=None, color=None):
    existing = frappe.db.exists(
        "Workspace Shortcut",
        {
            "parent": workspace_name,
            "label": label,
        },
    )

    values = {
        "type": link_type,
        "label": label,
    }

    if link_type == "URL":
        values.update({"url": url or "", "link_to": ""})
    else:
        values.update({"link_to": link_to or "", "url": ""})

    if icon is not None:
        values["icon"] = icon
    if color is not None:
        values["color"] = color

    if existing:
        frappe.db.set_value("Workspace Shortcut", existing, values, update_modified=False)
        return existing

    shortcut = frappe.get_doc({
        "doctype": "Workspace Shortcut",
        "parent": workspace_name,
        "parenttype": "Workspace",
        "parentfield": "shortcuts",
        **values,
    })
    shortcut.insert(ignore_permissions=True)
    return shortcut.name


def _ensure_sidebar_item(sidebar_title, label, link_type, link_to=None, url=None, icon=None):
    sidebar_name = frappe.db.exists("Workspace Sidebar", {"title": sidebar_title})
    if not sidebar_name:
        return

    existing = frappe.db.exists(
        "Workspace Sidebar Item",
        {
            "parent": sidebar_name,
            "label": label,
        },
    )

    values = {
        "label": label,
        "type": "Link",
        "link_type": link_type,
    }
    if link_type == "URL":
        values.update({"url": url or "", "link_to": ""})
    else:
        values.update({"link_to": link_to or "", "url": ""})
    if icon is not None:
        values["icon"] = icon

    if existing:
        frappe.db.set_value("Workspace Sidebar Item", existing, values, update_modified=False)
        return

    item = frappe.get_doc({
        "doctype": "Workspace Sidebar Item",
        "parent": sidebar_name,
        "parenttype": "Workspace Sidebar",
        "parentfield": "items",
        **values,
    })
    item.insert(ignore_permissions=True)


def _ensure_gestion_equipe_content():
    if not frappe.db.exists("Workspace", "Gestion Équipe"):
        return

    _upsert_workspace_shortcut(
        "Gestion Équipe",
        "Dashboard Equipe",
        "URL",
        url="/kya-dashboard-equipe",
        icon="bar-chart-2",
        color="#4CAF50",
    )

    content_blocks = [
        {"id": "shortcut-dashboard", "type": "shortcut", "data": {"shortcut_name": "Dashboard Equipe", "col": 12}},
    ]
    frappe.db.set_value("Workspace", "Gestion Équipe", "content", json.dumps(content_blocks), update_modified=False)

    frappe.db.delete("Workspace Sidebar Item", {"parent": "Gestion Équipe"})
    _ensure_sidebar_item("Gestion Équipe", "Dashboard Equipe", "URL", url="/kya-dashboard-equipe", icon="bar-chart-2")
    print("  [MINIMAL] Gestion Équipe content + sidebar (Dashboard only)")


def execute():
    """Post-migrate hook -- nettoyage et visibilite uniquement."""
    print("=== KYA WORKSPACE SYNC v10 ===")

    # 1. Supprimer les Workspace Sidebar orphelins
    for sb_name in ORPHAN_SIDEBARS:
        if frappe.db.exists("Workspace Sidebar", sb_name):
            frappe.delete_doc("Workspace Sidebar", sb_name, force=True, ignore_missing=True)
            print(f"  [SIDEBAR DELETED] {sb_name}")

    # Also delete "Conges & Permissions" sidebar (accent variants)
    for variant in ["Conges & Permissions", "Cong\u00e9s & Permissions"]:
        if frappe.db.exists("Workspace Sidebar", variant):
            frappe.delete_doc("Workspace Sidebar", variant, force=True, ignore_missing=True)
            print(f"  [SIDEBAR DELETED] {variant}")

    # 2. Supprimer les workspaces orphelins des anciennes versions
    for ws_name in ORPHAN_WORKSPACES:
        if frappe.db.exists("Workspace", ws_name):
            frappe.delete_doc("Workspace", ws_name, force=True, ignore_missing=True)
            print(f"  [WORKSPACE DELETED] {ws_name} (orphelin)")

    # Also delete accent variant
    if frappe.db.exists("Workspace", "Cong\u00e9s & Permissions"):
        frappe.delete_doc("Workspace", "Cong\u00e9s & Permissions", force=True, ignore_missing=True)
        print("  [WORKSPACE DELETED] Cong\u00e9s & Permissions (orphelin)")

    # 3. Corriger le module de KYA Services (doit etre KYA Services, pas KYA HR)
    if frappe.db.exists("Workspace", "KYA Services"):
        current_module = frappe.db.get_value("Workspace", "KYA Services", "module")
        if current_module != "KYA Services":
            frappe.db.set_value("Workspace", "KYA Services", {
                "module": "KYA Services",
                "app": "kya_services"
            }, update_modified=False)
            print(f"  [FIXED] KYA Services module: {current_module} -> KYA Services")

    # 4. S'assurer que les workspaces KYA sont visibles
    for ws_name in KYA_WORKSPACES:
        if frappe.db.exists("Workspace", ws_name):
            frappe.db.set_value("Workspace", ws_name, "is_hidden", 0, update_modified=False)
            if not frappe.db.get_value("Workspace", ws_name, "title"):
                frappe.db.set_value("Workspace", ws_name, "title", ws_name, update_modified=False)
            print(f"  [VISIBLE] {ws_name}")

    # 5. Creer le Workspace Sidebar pour KYA Services s'il n'existe pas
    #    Guard: only if kya_services app is fully installed (DocTypes + Workspace exist)
    if not _sidebar_exists("KYA Services"):
        kya_svc_ready = (
            frappe.db.exists("DocType", "KYA Form")
            and frappe.db.exists("Workspace", "KYA Services")
        )
        if not kya_svc_ready:
            print("  [SKIP] KYA Services sidebar (kya_services not fully installed)")
        else:
            sidebar = frappe.new_doc("Workspace Sidebar")
            sidebar.title = "KYA Services"
            sidebar.module = "KYA Services"
            sidebar.header_icon = "clipboard-list"
            sidebar.app = "kya_services"
            sidebar.standard = 0
            sidebar.append("items", {
                "label": "KYA Services",
                "type": "Link",
                "link_to": "KYA Services",
                "link_type": "Workspace",
                "icon": "clipboard-list"
            })
            sidebar.append("items", {
                "label": "KYA Form",
                "type": "Link",
                "link_to": "KYA Form",
                "link_type": "DocType",
                "icon": "file-text"
            })
            sidebar.append("items", {
                "label": "Reponses",
                "type": "Link",
                "link_to": "KYA Form Response",
                "link_type": "DocType",
                "icon": "list"
            })
            sidebar.append("items", {
                "label": "KYA Evaluation",
                "type": "Link",
                "link_to": "KYA Evaluation",
                "link_type": "DocType",
                "icon": "clipboard-check"
            })
            sidebar.insert(ignore_permissions=True)
            print("  [CREATED] KYA Services sidebar")

    # 6. Creer le Workspace Sidebar pour Espace Stagiaires s'il n'existe pas
    if not _sidebar_exists("Espace Stagiaires"):
        if frappe.db.exists("Workspace", "Espace Stagiaires"):
            sidebar = frappe.new_doc("Workspace Sidebar")
            sidebar.title = "Espace Stagiaires"
            sidebar.module = "KYA HR"
            sidebar.header_icon = "graduation-cap"
            sidebar.app = "kya_hr"
            sidebar.standard = 0
            sidebar.append("items", {
                "label": "Espace Stagiaires",
                "type": "Link",
                "link_to": "Espace Stagiaires",
                "link_type": "Workspace",
                "icon": "graduation-cap"
            })
            sidebar.append("items", {
                "label": "Permission Sortie",
                "type": "Link",
                "link_to": "Permission Sortie Stagiaire",
                "link_type": "DocType",
                "icon": "file-text"
            })
            sidebar.append("items", {
                "label": "Bilan Fin de Stage",
                "type": "Link",
                "link_to": "Bilan Fin de Stage",
                "link_type": "DocType",
                "icon": "clipboard"
            })
            sidebar.insert(ignore_permissions=True)
            print("  [CREATED] Espace Stagiaires sidebar")
        else:
            print("  [SKIP] Espace Stagiaires sidebar (workspace not found)")

    # 6b. Creer le Workspace Sidebar pour Espace Employes s'il n'existe pas
    espace_employes_name = None
    if frappe.db.exists("Workspace", "Espace Employes"):
        espace_employes_name = "Espace Employes"
    elif frappe.db.exists("Workspace", "Espace Employés"):
        espace_employes_name = "Espace Employés"

    if not _sidebar_exists("Espace Employes") and espace_employes_name:
        sidebar = frappe.new_doc("Workspace Sidebar")
        sidebar.title = "Espace Employes"
        sidebar.module = "KYA HR"
        sidebar.header_icon = "employee"
        sidebar.app = "kya_hr"
        sidebar.standard = 0
        sidebar.append("items", {
            "label": "Espace Employes",
            "type": "Link",
            "link_to": espace_employes_name,
            "link_type": "Workspace",
            "icon": "employee"
        })
        sidebar.append("items", {
            "label": "Permissions de Sortie",
            "type": "Link",
            "link_to": "Permission Sortie Employe",
            "link_type": "DocType",
            "icon": "file-text"
        })
        sidebar.append("items", {
            "label": "Planning Conge",
            "type": "Link",
            "link_to": "Planning Conge",
            "link_type": "DocType",
            "icon": "calendar"
        })
        sidebar.insert(ignore_permissions=True)
        print("  [CREATED] Espace Employes sidebar")

    # 7. Corriger le champ app de Gestion Equipe

    if frappe.db.exists("Workspace", "Gestion Équipe"):
        current_app = frappe.db.get_value("Workspace", "Gestion Équipe", "app")
        if not current_app:
            frappe.db.set_value("Workspace", "Gestion Équipe", "app", "kya_services", update_modified=False)
            print("  [FIXED] Gestion Équipe app -> kya_services")

    # 8. Ensure sidebars expose a workspace home link (required by desktop icon route resolver).
    gestion_ws = _resolve_existing_workspace(["Gestion Équipe", "Gestion Equipe"])
    if gestion_ws:
        _ensure_sidebar_home_link("Gestion Équipe", gestion_ws)
        _ensure_gestion_equipe_content()
        _ensure_sidebar_item("Gestion Équipe", "Plans Trimestriels", "DocType", link_to="Plan Trimestriel", icon="list")
        _ensure_sidebar_item("Gestion Équipe", "Taches d'Equipe", "DocType", link_to="Tache Equipe", icon="task")

    espace_ws = _resolve_existing_workspace(["Espace Employes", "Espace Employés"])
    if espace_ws:
        _ensure_sidebar_home_link("Espace Employes", espace_ws)

    # Ensure KYA Services sidebar contains functional entries even if sidebar existed but got emptied.
    kya_services_ws = _resolve_existing_workspace(["KYA Services"])
    if kya_services_ws:
        _ensure_sidebar_home_link("KYA Services", kya_services_ws)
        _ensure_sidebar_item("KYA Services", "Formulaires", "DocType", link_to="KYA Form", icon="file")
        _ensure_sidebar_item("KYA Services", "Évaluations", "DocType", link_to="KYA Evaluation", icon="clipboard")
        _ensure_sidebar_item("KYA Services", "Réponses Formulaires", "DocType", link_to="KYA Form Response", icon="list")

    # 9. Desktop icons must target Workspace Sidebar to avoid route=null popup.
    _link_desktop_icon_to_sidebar("KYA Services", ["KYA Services"])
    _link_desktop_icon_to_sidebar("Gestion Équipe", ["Gestion Équipe", "Gestion Equipe"])
    _link_desktop_icon_to_sidebar("Gestion Equipe", ["Gestion Équipe", "Gestion Equipe"])
    _link_desktop_icon_to_sidebar("Espace Employes", ["Espace Employes", "Espace Employés"])
    _link_desktop_icon_to_sidebar("Espace Employés", ["Espace Employes", "Espace Employés"])
    _link_desktop_icon_to_sidebar("Espace Stagiaires", ["Espace Stagiaires"])

    # 9b. Auto-create Workspace Sidebar for Achats/Stock/RH/Compta/Direction/Logistique
    for cfg in KYA_AUTO_SIDEBARS:
        title = cfg["title"]
        ws_name = cfg["workspace"]
        if not frappe.db.exists("Workspace", ws_name):
            print(f"  [SKIP SIDEBAR] {title} (workspace '{ws_name}' missing)")
            continue
        if not _sidebar_exists(title):
            sidebar = frappe.new_doc("Workspace Sidebar")
            sidebar.title = title
            sidebar.module = cfg["module"]
            sidebar.header_icon = cfg["icon"]
            sidebar.app = cfg["app"]
            sidebar.standard = 0
            sidebar.append("items", {
                "label": title,
                "type": "Link",
                "link_to": ws_name,
                "link_type": "Workspace",
                "icon": cfg["icon"],
            })
            for it in cfg["items"]:
                # Skip items pointing to non-existent doctypes
                if it.get("link_type") == "DocType" and not frappe.db.exists("DocType", it.get("link_to")):
                    continue
                sidebar.append("items", {
                    "label": it["label"],
                    "type": "Link",
                    "link_type": it["link_type"],
                    "link_to": it.get("link_to", ""),
                    "url": it.get("url", ""),
                    "icon": it.get("icon", "file"),
                })
            sidebar.insert(ignore_permissions=True)
            print(f"  [CREATED SIDEBAR] {title} (icon={cfg['icon']})")
        else:
            # Sidebar exists -> ensure header icon is the Lucide icon
            sidebar_name = frappe.db.exists("Workspace Sidebar", {"title": title})
            if sidebar_name:
                frappe.db.set_value("Workspace Sidebar", sidebar_name, "header_icon", cfg["icon"], update_modified=False)
        _link_desktop_icon_to_sidebar(title, [title])

    # 10. Fix setup_complete default value if needed
    try:
        val = frappe.db.get_value("DefaultValue", {"defkey": "setup_complete"}, "defvalue")
        if val != "1":
            frappe.db.sql("UPDATE tabDefaultValue SET defvalue='1' WHERE defkey='setup_complete'")
            print("  [FIXED] setup_complete = 1")
    except Exception:
        pass

    frappe.db.commit()
    print("=== DONE ===")
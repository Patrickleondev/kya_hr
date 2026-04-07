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


# Workspaces orphelins a supprimer (crees par d'anciennes versions du script)
ORPHAN_WORKSPACES = ["KYA Stagiaires", "Conges & Permissions"]

# Workspace Sidebars orphelins a supprimer
ORPHAN_SIDEBARS = ["KYA Stagiaires", "Personnes"]

# Workspaces geres par les fichiers JSON (on s'assure juste qu'ils sont visibles)
KYA_WORKSPACES = ["Espace Employes", "Espace Stagiaires", "KYA Services", "Gestion Équipe"]


def _normalize_workspace_title(workspace_name):
    """Ensure custom workspaces always have a non-null title for Desk route generation."""
    if not frappe.db.exists("Workspace", workspace_name):
        return

    title = frappe.db.get_value("Workspace", workspace_name, "title")
    if title:
        return

    fallback_title = (
        frappe.db.get_value("Workspace", workspace_name, "label")
        or workspace_name
    )
    frappe.db.set_value(
        "Workspace", workspace_name, "title", fallback_title, update_modified=False
    )
    print(f"  [FIXED] {workspace_name} title -> {fallback_title}")


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
            _normalize_workspace_title(ws_name)
            print(f"  [VISIBLE] {ws_name}")

    # 5. Creer le Workspace Sidebar pour KYA Services s'il n'existe pas
    #    Guard: only if kya_services app is fully installed (DocTypes + Workspace exist)
    if not frappe.db.exists("Workspace Sidebar", "KYA Services"):
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
    if not frappe.db.exists("Workspace Sidebar", "Espace Stagiaires"):
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

    # 7. Corriger le champ app de Gestion Equipe
    if frappe.db.exists("Workspace", "Gestion Équipe"):
        current_app = frappe.db.get_value("Workspace", "Gestion Équipe", "app")
        if not current_app:
            frappe.db.set_value("Workspace", "Gestion Équipe", "app", "kya_services", update_modified=False)
            print("  [FIXED] Gestion Équipe app -> kya_services")

    # 8. Fix setup_complete default value if needed
    try:
        val = frappe.db.get_value("DefaultValue", {"defkey": "setup_complete"}, "defvalue")
        if val != "1":
            frappe.db.sql("UPDATE tabDefaultValue SET defvalue='1' WHERE defkey='setup_complete'")
            print("  [FIXED] setup_complete = 1")
    except Exception:
        pass

    frappe.db.commit()
    print("=== DONE ===")
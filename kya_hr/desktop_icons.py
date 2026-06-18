import json

import frappe
from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache

WORKSPACE_ICONS = [
    {"label": "Direction Générale", "link_to": "Direction Generale", "sidebar": "Direction Generale", "icon": "🏛️", "app": "kya_hr", "idx": 10},
    {"label": "Gestion Équipe", "link_to": "Gestion Equipe", "sidebar": "Gestion Equipe", "icon": "🤝", "app": "kya_services", "idx": 20},
    {"label": "Espace RH", "link_to": "Espace RH", "icon": "👥", "app": "kya_hr", "idx": 11},
    {"label": "Espace Achats", "link_to": "Espace Achats", "icon": "🛒", "app": "kya_hr", "idx": 12},
    {"label": "Espace Stock", "link_to": "Espace Stock", "icon": "📦", "app": "kya_hr", "idx": 13},
    {"label": "Espace Comptabilité", "link_to": "Espace Comptabilité", "icon": "💰", "app": "kya_hr", "idx": 14},
    {"label": "Logistique", "link_to": "Logistique", "icon": "🚚", "app": "kya_hr", "idx": 15},
    {"label": "Espace Employés", "link_to": "Espace Employes", "icon": "👤", "app": "kya_hr", "idx": 16},
    {"label": "Espace Stagiaires", "link_to": "Espace Stagiaires", "icon": "🎓", "app": "kya_hr", "idx": 17},
    # "Inventaire & Sorties Matériel" retiré : redondant avec Espace Stock + le
    # libellé avec '&' cassait la route (404). Le workspace est masqué (cf.
    # fix_workspace_anomalies). Inventaire/PV sortie restent dans Espace Stock.
    {"label": "KYA Services", "link_to": "KYA Services", "icon": "📋", "app": "kya_services", "idx": 19},
]

RESTRICTED_LAYOUT_ROLES = {
    "Direction Générale": ["Directeur Général", "DG", "DGA", "DAAF", "System Manager", "Administrator"],
    "Gestion Équipe": [
        "Chef Equipe", "Chef d'Équipe", "Chef Service", "Responsable Equipe",
        "Supérieur Immédiat", "Directeur Général", "DG", "DGA", "System Manager",
    ],
    "Espace RH": ["HR Manager", "HR User", "Responsable RH", "Directeur Général", "System Manager"],
    "Espace Achats": [
        "Purchase Manager",
        "Purchase User",
        "Responsable Achats",
        "Responsable Comptable",
        "Directeur Général",
        "DG",
        "DGA",
        "Auditeur Interne",
        "System Manager",
    ],
    "Espace Stock": [
        "Stock Manager",
        "Stock User",
        "Chargé des Stocks",
        "Responsable Comptable",
        "Auditeur Interne",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    "Espace Comptabilité": [
        "Accounts Manager",
        "Accounts User",
        "Responsable Comptable",
        "Auditeur Interne",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    "Logistique": [
        "Fleet Manager",
        "Responsable Logistique",
        "Driver",
        "Responsable Comptable",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    "Inventaire & Sorties Matériel": [
        "Stock Manager",
        "Stock User",
        "Chargé des Stocks",
        "Responsable Achats",
        "Auditeur Interne",
        "Responsable Comptable",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    # Espace Employés contient Mon Espace + raccourcis formulaires de base.
    # Accessible à TOUS les comptes liés à un employé actif : rôle Employee
    # est le rôle par défaut HRMS. Les rôles métier élargissent simplement
    # la portée (gestion RH, stock, achats, direction).
    "Espace Employés": [
        "Employee",          # ← tout employé KYA (CDI/CDD/Stage/Prestataire)
        "Stagiaire",
        "Chef Service",
        "Supérieur Immédiat",
        "Chef Equipe",
        "Responsable RH",
        "HR User",
        "HR Manager",
        "Directeur Général",
        "DG",
        "DGA",
        "Responsable Comptable",
        "Auditeur Interne",
        "Stock User",
        "Purchase User",
        "Responsable Achats",
        "Chargé des Stocks",
        "KYA Destinataire Notif",
        "System Manager",
    ],
    "Espace Stagiaires": [
        # Stagiaire lui-meme doit voir son icone (son espace) sur le desk
        # legacy /desk. Sur /app c'est gere via le workspace.roles.
        "Stagiaire",
        "Maître de Stage",
        "Responsable des Stagiaires",
        "Responsable RH",
        "HR User",
        "HR Manager",
        "Directeur Général",
        "DG",
        "System Manager",
    ],
    "KYA Services": ["KYA Survey Admin", "System Manager"],
}

LAYOUT_FIELDS = [
    "label",
    "bg_color",
    "link",
    "link_type",
    "app",
    "icon_type",
    "parent_icon",
    "icon",
    "link_to",
    "idx",
    "standard",
    "logo_url",
    "hidden",
    "name",
    "restrict_removal",
    "icon_image",
]


def _get_icon_doc(label: str):
    name = frappe.db.get_value(
        "Desktop Icon",
        {"label": label, "link_type": "Workspace Sidebar"},
        "name",
    )
    if name:
        return frappe.get_doc("Desktop Icon", name)
    return frappe.new_doc("Desktop Icon")


def _serialize_icon(icon: dict) -> dict:
    item = {field: icon.get(field) for field in LAYOUT_FIELDS}
    item["child_icons"] = []
    return item


def _sync_workspace_icon(config: dict) -> bool:
    if not frappe.db.exists("Workspace", config["link_to"]):
        return False

    workspace_title = frappe.db.get_value("Workspace", config["link_to"], "title")
    workspace_label = frappe.db.get_value("Workspace", config["link_to"], "label")

    sidebar_name = frappe.db.get_value(
        "Workspace Sidebar",
        {"title": config.get("sidebar") or config["label"]},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": config["label"]},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": config["link_to"]},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": workspace_title},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": workspace_label},
        "name",
    ) or config["link_to"]

    icon = _get_icon_doc(config["label"])
    previous = {
        "label": icon.get("label"),
        "link_type": icon.get("link_type"),
        "icon_type": icon.get("icon_type"),
        "link_to": icon.get("link_to"),
        "icon": icon.get("icon"),
        "app": icon.get("app"),
        "idx": icon.get("idx"),
        "hidden": icon.get("hidden"),
        "parent_icon": icon.get("parent_icon"),
        "standard": icon.get("standard"),
    }

    icon.label = config["label"]
    icon.link_type = "Workspace Sidebar"
    icon.icon_type = "Link"
    icon.link_to = sidebar_name
    icon.icon = config["icon"]
    icon.app = config.get("app") or "kya_hr"
    icon.idx = config["idx"]
    icon.hidden = 0
    icon.parent_icon = None
    icon.standard = 1

    current = {
        "label": icon.get("label"),
        "link_type": icon.get("link_type"),
        "icon_type": icon.get("icon_type"),
        "link_to": icon.get("link_to"),
        "icon": icon.get("icon"),
        "app": icon.get("app"),
        "idx": icon.get("idx"),
        "hidden": icon.get("hidden"),
        "parent_icon": icon.get("parent_icon"),
        "standard": icon.get("standard"),
    }

    if icon.is_new() or previous != current:
        icon.flags.ignore_links = True
        icon.save(ignore_permissions=True)
        changed = True
    else:
        changed = False

    duplicate_values = {
        "link_type": "Workspace Sidebar",
        "icon_type": "Link",
        "link_to": sidebar_name,
        "icon": config["icon"],
        "app": config.get("app") or "kya_hr",
        "idx": config["idx"],
        "hidden": 0,
        "parent_icon": None,
        "standard": 1,
    }
    for duplicate in frappe.get_all("Desktop Icon", filters={"label": config["label"]}, pluck="name"):
        current_values = frappe.db.get_value("Desktop Icon", duplicate, list(duplicate_values), as_dict=True)
        updates = {key: value for key, value in duplicate_values.items() if current_values.get(key) != value}
        if updates:
            frappe.db.set_value("Desktop Icon", duplicate, updates, update_modified=False)
            changed = True

    return changed


def _build_default_layout() -> list[dict]:
    icons = frappe.get_all(
        "Desktop Icon",
        fields=LAYOUT_FIELDS,
        filters={"standard": 1, "hidden": 0},
        order_by="idx asc, creation asc",
    )
    icon_map = {icon["label"]: _serialize_icon(icon) for icon in icons}
    layout = []

    for icon in icons:
        item = icon_map[icon["label"]]
        parent = icon.get("parent_icon")
        if parent and parent in icon_map:
            item["in_folder"] = True
            icon_map[parent]["child_icons"].append(item)
        else:
            layout.append(item)

    return layout


def _sync_layout_doc(layout_doc) -> bool:
    layout = json.loads(layout_doc.layout or "[]")
    changed = False

    for config in WORKSPACE_ICONS:
        icon = frappe.db.get_value(
            "Desktop Icon",
            {"label": config["label"], "link_type": "Workspace Sidebar"},
            LAYOUT_FIELDS,
            as_dict=True,
        )
        if not icon:
            continue

        serialized = _serialize_icon(icon)
        existing_items = [item for item in layout if item.get("label") == config["label"]]
        if existing_items:
            keep = existing_items[0]
            for field in LAYOUT_FIELDS:
                if keep.get(field) != serialized.get(field):
                    keep[field] = serialized.get(field)
                    changed = True
            keep["child_icons"] = keep.get("child_icons") or []
            for duplicate in existing_items[1:]:
                layout.remove(duplicate)
                changed = True
        else:
            layout.append(serialized)
            changed = True

    layout.sort(key=lambda item: (item.get("idx") or 0, item.get("label") or ""))

    if changed:
        layout_doc.layout = json.dumps(layout, ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
        return True

    return False


def _sync_all_desktop_layouts() -> bool:
    changed = False

    for row in frappe.get_all("Desktop Layout", fields=["name"]):
        layout_doc = frappe.get_doc("Desktop Layout", row.name)
        changed = _sync_layout_doc(layout_doc) or changed

    # Ensure Administrator has a layout in fresh sites, then sync it too.
    if not frappe.db.exists("Desktop Layout", "Administrator"):
        layout_doc = frappe.new_doc("Desktop Layout")
        layout_doc.user = "Administrator"
        layout_doc.owner = "Administrator"
        layout_doc.layout = json.dumps(_build_default_layout(), ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
        changed = True

    admin_doc = frappe.get_doc("Desktop Layout", "Administrator")
    changed = _sync_layout_doc(admin_doc) or changed

    return changed


def _user_has_any_role(user: str, allowed_roles: list[str]) -> bool:
    if user == "Administrator":
        return True
    roles = set(frappe.get_roles(user) or [])
    return bool(roles.intersection(allowed_roles))


def _prune_restricted_layout_doc(layout_doc) -> bool:
    layout = json.loads(layout_doc.layout or "[]")
    user = layout_doc.get("user") or layout_doc.get("owner")
    changed = False

    def allowed(item):
        label = item.get("label")
        roles = RESTRICTED_LAYOUT_ROLES.get(label)
        return not roles or _user_has_any_role(user, roles)

    pruned = []
    for item in layout:
        child_icons = item.get("child_icons") or []
        filtered_children = [child for child in child_icons if allowed(child)]
        if len(filtered_children) != len(child_icons):
            item["child_icons"] = filtered_children
            changed = True
        if allowed(item):
            pruned.append(item)
        else:
            changed = True

    if changed:
        layout_doc.layout = json.dumps(pruned, ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)

    return changed


def _managed_label_by_target() -> dict:
    """Cible (sidebar/workspace) -> libellé géré (accentué)."""
    m = {}
    for cfg in WORKSPACE_ICONS:
        m[cfg.get("sidebar") or cfg["link_to"]] = cfg["label"]
        m[cfg["link_to"]] = cfg["label"]
    return m


def _dedupe_layout_doc(layout_doc) -> bool:
    """Supprime les icônes en double DANS une Desktop Layout.

    Bug terrain : la même icône (ex. « Direction Generale ») se cumulait des
    dizaines de fois car la déduplication se faisait par LABEL et les entrées
    héritées portaient un libellé non accentué (« Direction Generale ») là où
    l'icône gérée est « Direction Générale ». On déduplique donc par
    (link_type, link_to) — l'identité stable du workspace — et on normalise au
    passage le libellé vers la version accentuée gérée.
    """
    layout = json.loads(layout_doc.layout or "[]")
    label_map = _managed_label_by_target()
    seen = set()
    out = []
    changed = False
    for item in layout:
        lt = item.get("link_type") or ""
        target = item.get("link_to") or item.get("label") or ""
        if lt == "Workspace Sidebar" and target in label_map and item.get("label") != label_map[target]:
            item["label"] = label_map[target]
            changed = True
        key = (lt, target)
        if key in seen:
            changed = True  # doublon -> on jette
            continue
        seen.add(key)
        out.append(item)
    if changed:
        layout_doc.layout = json.dumps(out, ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
    return changed


def _dedupe_all_layouts() -> bool:
    changed = False
    for row in frappe.get_all("Desktop Layout", fields=["name"]):
        try:
            changed = _dedupe_layout_doc(frappe.get_doc("Desktop Layout", row.name)) or changed
        except Exception:
            try:
                frappe.log_error(frappe.get_traceback(), "desktop_icons: dedupe layout")
            except Exception:
                pass
    return changed


def _prune_restricted_desktop_layouts() -> bool:
    changed = False
    for row in frappe.get_all("Desktop Layout", fields=["name"]):
        layout_doc = frappe.get_doc("Desktop Layout", row.name)
        changed = _prune_restricted_layout_doc(layout_doc) or changed
    return changed


def _sync_administrator_layout() -> bool:
    if not frappe.db.exists("Desktop Layout", "Administrator"):
        layout_doc = frappe.new_doc("Desktop Layout")
        layout_doc.user = "Administrator"
        layout_doc.owner = "Administrator"
        layout_doc.layout = json.dumps(_build_default_layout(), ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
        return True

    admin_doc = frappe.get_doc("Desktop Layout", "Administrator")
    return _sync_layout_doc(admin_doc)


@frappe.whitelist()
def execute():
    """Sync KYA Desktop Icons. Defensive: never raise to avoid breaking install/migrate."""
    # Skip if Desktop Icon table doesn't exist (fresh install before frappe.desk migration)
    if not frappe.db.has_table("Desktop Icon") or not frappe.db.has_table("Desktop Layout"):
        print("[kya_hr.desktop_icons] Desktop Icon/Layout tables missing, skipping.")
        return {"skipped": True}

    changed = False
    errors = []

    for config in WORKSPACE_ICONS:
        try:
            changed = _sync_workspace_icon(config) or changed
        except Exception as e:
            errors.append(f"{config['label']}: {e}")

    try:
        # Re-sync TOUTES les Desktop Layout (pas seulement Administrator) : ajoute
        # les icônes standard manquantes à chaque utilisateur, PUIS élague par rôle.
        # Sinon une icône autrefois élaguée (ex. Direction pour un compte "DG")
        # n'était jamais re-ajoutée après correction des rôles.
        changed = _sync_all_desktop_layouts() or changed
        changed = _dedupe_all_layouts() or changed        # collapse les doublons hérités
        changed = _prune_restricted_desktop_layouts() or changed
    except Exception as e:
        errors.append(f"layouts: {e}")

    try:
        for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
            clear_desktop_icons_cache(user)
        frappe.clear_cache()
    except Exception as e:
        errors.append(f"clear_cache: {e}")

    if errors:
        print(f"[kya_hr.desktop_icons] Warnings: {errors}")

    return {
        "changed": changed,
        "labels": [config["label"] for config in WORKSPACE_ICONS],
        "errors": errors,
    }

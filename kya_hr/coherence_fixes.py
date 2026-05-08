import json

import frappe


ICON_REPLACEMENTS = {
    "basket": "shopping-cart",
    "currency-exchange": "wallet",
    "person-vcard": "user-round",
    "employee": "user-round",
    "dashboard": "chart-column",
    "graph-up": "chart-column",
    "bar-chart": "chart-column",
    "bar-chart-2": "chart-column",
    "exit": "log-out",
    "small-file": "file-text",
    "task": "list-checks",
    "folder-normal": "folder",
}

SIDEBAR_FIXES = {
    "Espace Direction": {"workspace": "Espace Direction", "icon": "🏛️", "module": "KYA HR", "app": "kya_hr"},
    "Espace Achats": {"workspace": "Espace Achats", "icon": "🛒", "module": "KYA HR", "app": "kya_hr"},
    "Espace Stock": {"workspace": "Espace Stock", "icon": "📦", "module": "KYA HR", "app": "kya_hr"},
    "Espace RH": {"workspace": "Espace RH", "icon": "👥", "module": "KYA HR", "app": "kya_hr"},
    "Espace Comptabilité": {"workspace": "Espace Comptabilité", "icon": "💰", "module": "KYA HR", "app": "kya_hr"},
    "Espace Employes": {"workspace": "Espace Employes", "icon": "👤", "module": "KYA HR", "app": "kya_hr"},
    "Espace Employés": {"workspace": "Espace Employes", "icon": "👤", "module": "KYA HR", "app": "kya_hr"},
    "Espace Stagiaires": {"workspace": "Espace Stagiaires", "icon": "🎓", "module": "KYA HR", "app": "kya_hr"},
    "Inventaire & Sorties Matériel": {"workspace": "Inventaire Sorties Materiel", "icon": "🧾", "module": "KYA HR", "app": "kya_hr"},
    "Logistique": {"workspace": "Logistique", "icon": "🚚", "module": "KYA HR", "app": "kya_hr"},
    "KYA Services": {"workspace": "KYA Services", "icon": "📋", "module": "KYA Services", "app": "kya_services"},
    "Gestion Équipe": {"workspace": "Gestion Équipe", "icon": "👥", "module": "KYA Taches", "app": "kya_services"},
}

DESKTOP_ICON_FIXES = {
    "Direction Générale": {"sidebar": "Espace Direction", "icon": "🏛️", "app": "kya_hr"},
    "Espace Achats": {"sidebar": "Espace Achats", "icon": "🛒", "app": "kya_hr"},
    "Espace Stock": {"sidebar": "Espace Stock", "icon": "📦", "app": "kya_hr"},
    "Espace RH": {"sidebar": "Espace RH", "icon": "👥", "app": "kya_hr"},
    "Espace Comptabilité": {"sidebar": "Espace Comptabilité", "icon": "💰", "app": "kya_hr"},
    "Logistique": {"sidebar": "Logistique", "icon": "🚚", "app": "kya_hr"},
    "Espace Employés": {"sidebar": "Espace Employes", "icon": "👤", "app": "kya_hr"},
    "Espace Stagiaires": {"sidebar": "Espace Stagiaires", "icon": "🎓", "app": "kya_hr"},
    "Inventaire & Sorties Matériel": {"sidebar": "Inventaire & Sorties Matériel", "icon": "🧾", "app": "kya_hr"},
    "KYA Services": {"sidebar": "KYA Services", "icon": "📋", "app": "kya_services"},
}

OBSOLETE_DESKTOP_LABELS = {"Espace Direction", "Inventaire Sorties Materiel"}


def _safe_icon(icon):
    return ICON_REPLACEMENTS.get(icon, icon)


def _set_values(doctype, name, values):
    current = frappe.db.get_value(doctype, name, list(values.keys()), as_dict=True)
    if not current:
        return False
    updates = {key: value for key, value in values.items() if current.get(key) != value}
    if updates:
        frappe.db.set_value(doctype, name, updates, update_modified=False)
        return True
    return False


def _ensure_sidebar(title, cfg):
    workspace = cfg["workspace"]
    icon = cfg["icon"]
    if not frappe.db.exists("Workspace", workspace):
        return False

    sidebar_name = frappe.db.exists("Workspace Sidebar", {"title": title})
    changed = False
    sidebar_values = {
        "title": title,
        "header_icon": icon,
        "module": cfg.get("module") or "KYA HR",
        "app": cfg.get("app") or "kya_hr",
    }
    if frappe.db.has_column("Workspace Sidebar", "type"):
        sidebar_values["type"] = "Link"
    if frappe.db.has_column("Workspace Sidebar", "link_to"):
        sidebar_values["link_to"] = workspace

    if sidebar_name:
        changed = _set_values("Workspace Sidebar", sidebar_name, sidebar_values) or changed
    else:
        sidebar = frappe.new_doc("Workspace Sidebar")
        for key, value in sidebar_values.items():
            setattr(sidebar, key, value)
        sidebar.standard = 0
        sidebar.append("items", {"label": title, "type": "Link", "link_type": "Workspace", "link_to": workspace, "icon": icon})
        sidebar.insert(ignore_permissions=True)
        sidebar_name = sidebar.name
        changed = True

    home_exists = frappe.db.exists(
        "Workspace Sidebar Item",
        {"parent": sidebar_name, "link_type": "Workspace", "link_to": workspace},
    )
    if not home_exists:
        item = frappe.new_doc("Workspace Sidebar Item")
        item.parent = sidebar_name
        item.parenttype = "Workspace Sidebar"
        item.parentfield = "items"
        item.type = "Link"
        item.label = title
        item.link_type = "Workspace"
        item.link_to = workspace
        item.icon = icon
        item.insert(ignore_permissions=True)
        changed = True

    return changed


def _ensure_desktop_icon(label, sidebar_title, icon):
    sidebar_name = frappe.db.exists("Workspace Sidebar", {"title": sidebar_title})
    if not sidebar_name:
        return False

    values = {
        "label": label,
        "link_type": "Workspace Sidebar",
        "icon_type": "Link",
        "link_to": sidebar_name,
        "link": "",
        "icon": icon,
        "app": DESKTOP_ICON_FIXES.get(label, {}).get("app") or "kya_hr",
        "hidden": 0,
        "standard": 1,
    }

    icon_names = frappe.get_all("Desktop Icon", filters={"label": label}, pluck="name")
    if icon_names:
        changed = False
        for icon_name in icon_names:
            changed = _set_values("Desktop Icon", icon_name, values) or changed
        return changed

    doc = frappe.new_doc("Desktop Icon")
    for key, value in values.items():
        setattr(doc, key, value)
    doc.insert(ignore_permissions=True)
    return True


def _normalize_icons(doctype, field="icon"):
    if not frappe.db.has_column(doctype, field):
        return 0
    changed = 0
    for row in frappe.get_all(doctype, fields=["name", field]):
        icon = row.get(field)
        safe = _safe_icon(icon)
        if icon and safe != icon:
            frappe.db.set_value(doctype, row.name, field, safe, update_modified=False)
            changed += 1
    return changed


def _hide_obsolete_desktop_icons():
    changed = 0
    for label in OBSOLETE_DESKTOP_LABELS:
        for name in frappe.get_all("Desktop Icon", filters={"label": label}, pluck="name"):
            frappe.db.set_value("Desktop Icon", name, "hidden", 1, update_modified=False)
            changed += 1
    return changed


def _clean_desktop_layouts():
    changed = 0
    keep_labels = set(DESKTOP_ICON_FIXES)

    for row in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
        try:
            layout = json.loads(row.layout or "[]")
        except Exception:
            continue

        filtered = []
        seen = set()
        for item in layout:
            label = item.get("label")
            if label in OBSOLETE_DESKTOP_LABELS:
                continue
            if label in keep_labels:
                if label in seen:
                    continue
                seen.add(label)
                cfg = DESKTOP_ICON_FIXES[label]
                sidebar_name = frappe.db.exists("Workspace Sidebar", {"title": cfg["sidebar"]})
                item.update({"link_type": "Workspace Sidebar", "link_to": sidebar_name, "icon": cfg["icon"], "hidden": 0})
            filtered.append(item)

        if filtered != layout:
            frappe.db.set_value("Desktop Layout", row.name, "layout", json.dumps(filtered, ensure_ascii=False), update_modified=False)
            changed += 1

    return changed


def _fix_km_number_card():
    name = frappe.db.exists("Number Card", {"label": "Km parcourus (total)"})
    if not name:
        return False
    doc = frappe.get_doc("Number Card", name)
    changed = False
    values = {
        "document_type": "Sortie Vehicule",
        "function": "Sum",
        "aggregate_function_based_on": "km_parcourus",
        "label": "Km parcourus (total)",
    }
    for field, value in values.items():
        if doc.meta.has_field(field) and doc.get(field) != value:
            setattr(doc, field, value)
            changed = True
    if doc.meta.has_field("is_currency") and doc.get("is_currency"):
        doc.is_currency = 0
        changed = True
    if doc.meta.has_field("currency") and doc.get("currency"):
        doc.currency = ""
        changed = True
    if changed:
        doc.save(ignore_permissions=True)
    return changed


def _existing_fields(doctype, candidates):
    return [field for field in candidates if frappe.db.has_column(doctype, field)]


@frappe.whitelist()
def audit():
    sidebar_titles = sorted(set(SIDEBAR_FIXES) | {cfg["sidebar"] for cfg in DESKTOP_ICON_FIXES.values()})
    bad_bilan_refs = {}
    for doctype in ["Workspace Link", "Workspace Shortcut", "Workspace Sidebar Item"]:
        if not frappe.db.has_table(doctype):
            continue
        bad_bilan_refs[doctype] = [
            row
            for row in frappe.get_all(doctype, fields=["name", "parent", "label", "link_to"])
            if row.get("link_to") == "Bilan Fin De Stage"
        ]
    sidebar_items = {}
    for sidebar in sidebar_titles:
        sidebar_name = frappe.db.exists("Workspace Sidebar", sidebar) or frappe.db.exists("Workspace Sidebar", {"title": sidebar})
        if not sidebar_name:
            continue
        sidebar_items[sidebar] = frappe.get_all(
            "Workspace Sidebar Item",
            filters={"parent": sidebar_name},
            fields=["idx", "label", "link_type", "link_to", "url"],
            order_by="idx asc",
        )
    return {
        "desktop_icons": frappe.get_all(
            "Desktop Icon",
            filters={"label": ["in", list(DESKTOP_ICON_FIXES) + list(OBSOLETE_DESKTOP_LABELS)]},
            fields=["name", "label", "link_type", "link_to", "icon", "hidden"],
            order_by="idx asc, label asc",
        ),
        "sidebars": frappe.get_all(
            "Workspace Sidebar",
            filters={"title": ["in", sidebar_titles]},
            fields=_existing_fields("Workspace Sidebar", ["name", "title", "type", "link_to", "header_icon", "module", "app"]),
            order_by="title asc",
        ),
        "sidebar_items": sidebar_items,
        "bad_bilan_refs": bad_bilan_refs,
        "km_card": frappe.db.get_value(
            "Number Card",
            {"label": "Km parcourus (total)"},
            ["name", "document_type", "function", "aggregate_function_based_on"],
            as_dict=True,
        ),
        "bilan_count": frappe.db.count("Bilan Fin de Stage") if frappe.db.exists("DocType", "Bilan Fin de Stage") else None,
    }


@frappe.whitelist()
def execute():
    if not frappe.db.has_table("Workspace Sidebar") or not frappe.db.has_table("Desktop Icon"):
        return {"skipped": True}

    changed = False
    for title, cfg in SIDEBAR_FIXES.items():
        changed = _ensure_sidebar(title, cfg) or changed

    for label, cfg in DESKTOP_ICON_FIXES.items():
        changed = _ensure_desktop_icon(label, cfg["sidebar"], cfg["icon"]) or changed

    normalized = 0
    for doctype in ["Desktop Icon", "Workspace", "Workspace Shortcut", "Workspace Sidebar", "Workspace Sidebar Item"]:
        normalized += _normalize_icons(doctype)
    if frappe.db.has_column("Workspace Sidebar", "header_icon"):
        normalized += _normalize_icons("Workspace Sidebar", "header_icon")

    hidden = _hide_obsolete_desktop_icons()
    layouts = _clean_desktop_layouts()
    km_fixed = _fix_km_number_card()

    frappe.db.commit()
    frappe.clear_cache()

    return {
        "changed": changed or bool(normalized or hidden or layouts or km_fixed),
        "normalized_icons": normalized,
        "hidden_obsolete_icons": hidden,
        "desktop_layouts_cleaned": layouts,
        "km_card_fixed": km_fixed,
    }

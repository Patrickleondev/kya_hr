import json

import frappe
from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache

WORKSPACE_ICONS = [
    {
        "label": "Espace Employes",
        "link_to": "Espace Employes",
        "icon": "employee",
        "idx": 13,
    },
    {
        "label": "Espace Stagiaires",
        "link_to": "Espace Stagiaires",
        "icon": "graduation-cap",
        "idx": 14,
    },
    {
        "label": "KYA Services",
        "link_to": "KYA Services",
        "icon": "clipboard-list",
        "idx": 15,
    },
    {
        "label": "Gestion Équipe",
        "link_to": "Gestion Équipe",
        "icon": "users",
        "idx": 16,
    },
]

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

    icon = _get_icon_doc(config["label"])
    previous = {
        "label": icon.get("label"),
        "link_type": icon.get("link_type"),
        "icon_type": icon.get("icon_type"),
        "link_to": icon.get("link_to"),
        "icon": icon.get("icon"),
        "idx": icon.get("idx"),
        "hidden": icon.get("hidden"),
        "parent_icon": icon.get("parent_icon"),
        "standard": icon.get("standard"),
    }

    icon.label = config["label"]
    icon.link_type = "Workspace Sidebar"
    icon.icon_type = "Link"
    icon.link_to = config["link_to"]
    icon.icon = config["icon"]
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
        "idx": icon.get("idx"),
        "hidden": icon.get("hidden"),
        "parent_icon": icon.get("parent_icon"),
        "standard": icon.get("standard"),
    }

    if icon.is_new() or previous != current:
        icon.flags.ignore_links = True
        icon.save(ignore_permissions=True)
        return True

    return False


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
    existing_labels = {item.get("label") for item in layout}
    changed = False

    for config in WORKSPACE_ICONS:
        if config["label"] in existing_labels:
            continue

        icon = frappe.db.get_value(
            "Desktop Icon",
            {"label": config["label"], "link_type": "Workspace Sidebar"},
            LAYOUT_FIELDS,
            as_dict=True,
        )
        if not icon:
            continue

        layout.append(_serialize_icon(icon))
        existing_labels.add(config["label"])
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


@frappe.whitelist()
def execute():
    changed = False

    for config in WORKSPACE_ICONS:
        changed = _sync_workspace_icon(config) or changed

    changed = _sync_all_desktop_layouts() or changed

    for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
        clear_desktop_icons_cache(user)
    frappe.clear_cache()

    return {
        "changed": changed,
        "labels": [config["label"] for config in WORKSPACE_ICONS],
    }

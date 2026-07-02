# -*- coding: utf-8 -*-
"""Renomme en FRANÇAIS (KYA) les libellés des écrans natifs ERPNext utilisés
pour les articles — SANS toucher au cœur (via Property Setter, réversible).

Décision métier : on garde l'écran natif ERPNext (robuste) pour créer/gérer la
liste des articles, mais avec NOS noms de colonnes. Les mouvements de stock et
l'inventaire restent gérés par le système maison (PV Entrée/Sortie/Retour +
grand-livre Mouvement Stock KYA).

Idempotent. À relancer après chaque migrate.
"""
from __future__ import annotations

import frappe

# (doctype, fieldname) -> libellé français
ITEM_LABELS = {
    ("Item", "item_code"): "Code article",
    ("Item", "item_name"): "Nom de l'article",
    ("Item", "item_group"): "Groupe d'article",
    ("Item", "stock_uom"): "Unité (UdM)",
    ("Item", "description"): "Désignation",
    ("Item", "custom_type_article"): "Type d'article",
    ("Item", "opening_stock"): "Stock d'ouverture",
    ("Item", "valuation_rate"): "Valeur unitaire",
}


def _ensure_type_field():
    """Le champ « Type d'article » (custom_type_article) doit exister sur Item."""
    if not frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": "custom_type_article"}):
        try:
            frappe.get_doc({
                "doctype": "Custom Field", "dt": "Item",
                "fieldname": "custom_type_article", "label": "Type d'article",
                "fieldtype": "Data", "insert_after": "item_group",
            }).insert(ignore_permissions=True)
        except Exception:
            pass


def _set_label(doctype: str, fieldname: str, label: str) -> str:
    existing = frappe.db.get_value(
        "Property Setter",
        {"doc_type": doctype, "field_name": fieldname, "property": "label"},
        "name",
    )
    if existing:
        if frappe.db.get_value("Property Setter", existing, "value") != label:
            frappe.db.set_value("Property Setter", existing, "value", label)
            return "updated"
        return "unchanged"
    frappe.make_property_setter(
        {"doctype": doctype, "fieldname": fieldname,
         "property": "label", "value": label, "property_type": "Data"},
        is_system_generated=False,
    )
    return "created"


# Rôles KYA qui gèrent les articles nativement (créer / modifier).
ITEM_CREATE_ROLES = ["Responsable Stock", "Chargé des Stocks"]


def _grant_item_perms() -> list[str]:
    """Donne read+write+create sur Item aux rôles stock, SANS écraser les perms
    standard : frappe.permissions.add_permission copie d'abord les DocPerm
    standard en Custom DocPerm, puis ajoute le rôle. Non destructif."""
    from frappe.permissions import add_permission, update_permission_property
    granted = []
    for role in ITEM_CREATE_ROLES:
        if not frappe.db.exists("Role", role):
            continue
        if not frappe.db.exists("Custom DocPerm", {"parent": "Item", "role": role, "permlevel": 0}):
            add_permission("Item", role, 0)
        for ptype in ("read", "write", "create"):
            update_permission_property("Item", role, 0, ptype, 1)
        granted.append(role)
    return granted


def execute() -> dict:
    _ensure_type_field()
    out = {"created": 0, "updated": 0, "unchanged": 0}
    for (dt, fn), label in ITEM_LABELS.items():
        if not frappe.get_meta(dt).has_field(fn):
            continue
        action = _set_label(dt, fn, label)
        out[action] = out.get(action, 0) + 1
    out["item_perms"] = _grant_item_perms()
    frappe.clear_cache(doctype="Item")
    frappe.db.commit()
    print(f"[relabel_native_stock] {out}")
    return out

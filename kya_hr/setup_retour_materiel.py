"""
Setup Retour Matériel KYA + Fournisseurs KYA
──────────────────────────────────────────────────────────────────────
1. Seed les Supplier Groups KYA s'ils n'existent pas
2. Seed les Suppliers réels KYA depuis la base de données fournisseurs
3. Ajoute les raccourcis PV Réception et Retour Matériel aux workspaces Stock
"""
import json
import os

import frappe

BASE = os.path.dirname(os.path.abspath(__file__))

SUPPLIER_GROUPS = [
    "Modules PV",
    "Batteries & Energie",
    "Onduleurs",
    "Cables & Electricite",
    "Pneumatiques",
    "Materiel de Plomberie",
    "Barres Metalliques",
    "Divers KYA",
]

SUPPLIERS = [
    {"supplier_name": "Jinko Solar",             "supplier_group": "Modules PV",         "country": "China",   "mobile_no": "+27(0)747045606",      "email_id": "megan.johnson@jinkosolar.com"},
    {"supplier_name": "HITECH",                  "supplier_group": "Batteries & Energie"},
    {"supplier_name": "Voltronic Power",         "supplier_group": "Batteries & Energie", "country": "Taiwan", "mobile_no": "+886-2-27918296",       "email_id": "alicetseng@voltronic.com.tw"},
    {"supplier_name": "BAE",                     "supplier_group": "Batteries & Energie", "country": "Germany","mobile_no": "+49-30-53001-673"},
    {"supplier_name": "Energie Douce",           "supplier_group": "Batteries & Energie", "country": "France", "mobile_no": "+33(0)130259530"},
    {"supplier_name": "ECO SMART INDUSTRY",      "supplier_group": "Onduleurs",           "country": "Togo",   "mobile_no": "+228 90 06 30 17"},
    {"supplier_name": "AHATEFOU TEKO",           "supplier_group": "Onduleurs",           "country": "Togo",   "mobile_no": "+228 91 32 31 30"},
    {"supplier_name": "Entech SE SAS",           "supplier_group": "Cables & Electricite","country": "France", "mobile_no": "+02 98 94 44 48"},
    {"supplier_name": "Ets BOCCOVI",             "supplier_group": "Pneumatiques",        "country": "Togo",   "mobile_no": "+228 90 12 59 16"},
    {"supplier_name": "AMERICAIN",               "supplier_group": "Pneumatiques",        "country": "Togo",   "mobile_no": "+228 90 10 57 56"},
    {"supplier_name": "ZOUBEYROU",               "supplier_group": "Pneumatiques",        "country": "Togo",   "mobile_no": "+228 92 87 67 02"},
    {"supplier_name": "CCT",                     "supplier_group": "Materiel de Plomberie","country": "Togo",  "mobile_no": "+228 22 21 57 63"},
    {"supplier_name": "PUISSANTE MAIN DE DIEU",  "supplier_group": "Materiel de Plomberie","country": "Togo",  "mobile_no": "+228 90 10 97 75"},
    {"supplier_name": "MA.CO.DI",                "supplier_group": "Materiel de Plomberie","country": "Togo",  "mobile_no": "+228 22 25 24 70"},
    {"supplier_name": "LES FRERES COUSINS",      "supplier_group": "Barres Metalliques",  "country": "Togo",   "mobile_no": "+228 22 22 81 90"},
    {"supplier_name": "MONICO",                  "supplier_group": "Barres Metalliques",  "country": "Togo",   "mobile_no": "+228 22 21 81 24"},
    {"supplier_name": "MAFIS",                   "supplier_group": "Barres Metalliques",  "country": "Togo",   "mobile_no": "+228 90 91 75 19"},
    {"supplier_name": "DONSEN",                  "supplier_group": "Barres Metalliques",  "country": "Togo",   "mobile_no": "+228 90 73 68 88"},
]

# Workspaces et raccourcis à ajouter
STOCK_SHORTCUTS = [
    {
        "workspace": "Espace Stock",
        "label": "PV Réception Matériel",
        "url": "/pv-entree-materiel/new",
        "type": "URL",
        "color": "#009688",
        "format": "Icon",
    },
    {
        "workspace": "Espace Stock",
        "label": "Retour de Matériel",
        "url": "/retour-materiel/new",
        "type": "URL",
        "color": "#e65100",
        "format": "Icon",
    },
    {
        "workspace": "Inventaire Sorties Materiel",
        "label": "PV Réception Matériel",
        "url": "/pv-entree-materiel/new",
        "type": "URL",
        "color": "#009688",
        "format": "Icon",
    },
    {
        "workspace": "Inventaire Sorties Materiel",
        "label": "Retour de Matériel",
        "url": "/retour-materiel/new",
        "type": "URL",
        "color": "#e65100",
        "format": "Icon",
    },
]


def _seed_supplier_groups():
    created = 0
    for grp in SUPPLIER_GROUPS:
        if frappe.db.exists("Supplier Group", grp):
            continue
        doc = frappe.new_doc("Supplier Group")
        doc.supplier_group_name = grp
        doc.parent_supplier_group = "All Supplier Groups"
        doc.insert(ignore_permissions=True)
        created += 1
    print(f"  [Supplier Groups] {created} groupe(s) créé(s)")


def _seed_suppliers():
    created = updated = 0
    for s in SUPPLIERS:
        exists = frappe.db.get_value("Supplier", {"supplier_name": s["supplier_name"]}, "name")
        if exists:
            # Update group if not set
            current_group = frappe.db.get_value("Supplier", exists, "supplier_group")
            if not current_group or current_group in ("", "All Supplier Groups"):
                frappe.db.set_value("Supplier", exists, "supplier_group", s["supplier_group"],
                                    update_modified=False)
                updated += 1
            continue
        doc = frappe.new_doc("Supplier")
        doc.supplier_name = s["supplier_name"]
        doc.supplier_group = s["supplier_group"]
        doc.country = s.get("country")
        doc.mobile_no = s.get("mobile_no")
        doc.email_id = s.get("email_id", "")
        doc.insert(ignore_permissions=True)
        created += 1
    print(f"  [Suppliers] {created} créé(s), {updated} groupe mis à jour")


def _add_workspace_shortcuts():
    """Insère les raccourcis directement via SQL pour éviter les validations
    de Frappe v16 sur les shortcuts existants potentiellement invalides."""
    import json as _json
    added = 0
    for sc in STOCK_SHORTCUTS:
        ws_name = sc["workspace"]
        if not frappe.db.exists("Workspace", ws_name):
            continue
        existing = frappe.db.get_value(
            "Workspace Shortcut",
            {"label": sc["label"], "parent": ws_name},
            "name",
        )
        if existing:
            continue
        try:
            name = frappe.generate_hash(length=10)
            frappe.db.sql("""
                INSERT INTO `tabWorkspace Shortcut`
                  (name, parent, parenttype, parentfield, idx, label, type, url, color, `format`, modified, creation, owner, docstatus)
                VALUES
                  (%(name)s, %(parent)s, 'Workspace', 'shortcuts',
                   COALESCE((SELECT MAX(idx)+1 FROM `tabWorkspace Shortcut` ws2 WHERE ws2.parent=%(parent)s), 1),
                   %(label)s, 'URL', %(url)s, %(color)s, %(format)s,
                   NOW(), NOW(), 'Administrator', 0)
            """, {
                "name": name,
                "parent": ws_name,
                "label": sc["label"],
                "url": sc["url"],
                "color": sc.get("color", "#333"),
                "format": sc.get("format", "Icon"),
            })
            added += 1
        except Exception as e:
            print(f"  [Workspace Shortcuts] Skipped {ws_name}/{sc['label']}: {e}")
    print(f"  [Workspace Shortcuts] {added} raccourci(s) ajouté(s)")


def run():
    print("=== Setup Retour Matériel KYA + Fournisseurs ===")
    if frappe.db.has_table("Supplier Group"):
        _seed_supplier_groups()
    if frappe.db.has_table("Supplier"):
        _seed_suppliers()
    if frappe.db.has_table("Workspace"):
        _add_workspace_shortcuts()
    frappe.db.commit()
    frappe.clear_cache()
    print("=== Done ===")

"""Seed du stock KYA depuis l'inventaire papier du 2026-06-05.

Source : 'ETAT DE STOCK-AES-05-06-2026.pdf' (Akossiwa AMEOGNO).

Ce script realise en 3 etapes :

1. Cree les 5 Item Groups KYA (Modules PV, Onduleurs, Batteries,
   Elements de protection, Luminaires).

2. Cree les 36 Items du stock (idempotent : item_code stable, code
   commercial -> fiche stock).

3. Cree UN Opening Stock Entry 'KYA-Inventaire-Initial-2026-06-05'
   qui injecte les quantites dans Magasin KYA - KYA. Verifie par
   nom avant d'inserer pour rester idempotent.

Hypotheses :
- Company : 'KYA-Energy Group' (abbr 'KYA')
- Warehouse : 'Magasin KYA - KYA'
- UOM : 'Nos' (unite native Frappe pour les pieces detachees)

Si la company ou le warehouse n'existe pas, le script log et passe
silencieusement (idempotent / pas d'erreur fatale).

Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe
from frappe.utils import getdate


COMPANY_DEFAULT = "KYA-Energy Group"
WAREHOUSE_DEFAULT = "Magasin KYA - KYA"
DEFAULT_UOM = "Nos"
OPENING_DATE = "2026-06-05"
OPENING_STOCK_ENTRY_NAME = "KYA-Inventaire-Initial-2026-06-05"


# Liste des Item Groups KYA - tous parent='All Item Groups'
KYA_ITEM_GROUPS: list[str] = [
    "Modules PV - KYA",
    "Onduleurs - KYA",
    "Batteries - KYA",
    "Elements de protection - KYA",
    "Luminaires - KYA",
]


# 36 items extraits du PDF. Le code item suit la convention
# CATEGORIE-MARQUE-CARAC. Quantites en pieces.
# Note : 'Disjoncteur Mono AC 10 A LeGrand' apparait 2x dans le PDF
# (1 + 13) -> fusionne en 14 ici (confirme avec le user).
KYA_ITEMS: list[dict] = [
    # ===== Modules PV =====
    {"code": "MOD-PV-455", "name": "Module PV 455Wc", "group": "Modules PV - KYA", "qty": 295},
    {"code": "MOD-PV-195", "name": "Module PV 195Wc", "group": "Modules PV - KYA", "qty": 241},
    {"code": "MOD-PV-165", "name": "Module PV 165Wc", "group": "Modules PV - KYA", "qty": 9},

    # ===== Onduleurs =====
    {"code": "OND-DEYE-5K", "name": "Onduleur DEYE 5 kW", "group": "Onduleurs - KYA", "qty": 3},
    {"code": "OND-DEYE-8K", "name": "Onduleur DEYE 8 kW", "group": "Onduleurs - KYA", "qty": 1},
    {"code": "OND-DEYE-10K", "name": "Onduleur DEYE 10 kW", "group": "Onduleurs - KYA", "qty": 1},

    # ===== Batteries =====
    {"code": "BAT-DEYE-5K", "name": "Batterie DEYE 5 kW", "group": "Batteries - KYA", "qty": 5},
    {"code": "BAT-KYA-51V100AH", "name": "KYA-BAT 51V/100Ah", "group": "Batteries - KYA", "qty": 5},
    {"code": "BAT-48V100AH-Z1", "name": "Batterie 48V/100Ah (Z1)", "group": "Batteries - KYA", "qty": 2},

    # ===== Elements de protection =====
    {"code": "DIS-TETRA-AC-63-CNTH", "name": "Disjoncteur Tetra AC 63A CNTH", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-TETRA-AC-63-SCH", "name": "Disjoncteur Tetra AC 63A Schneider", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-TETRA-AC-32-SCH", "name": "Disjoncteur Tetra AC 32A Schneider", "group": "Elements de protection - KYA", "qty": 2},
    {"code": "DIS-TETRA-AC-32-LEG", "name": "Disjoncteur Tetra AC 32A LeGrand", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-TETRA-AC-20-SCH", "name": "Disjoncteur Tetra AC 20A Schneider", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-TETRA-AC-16-SCH", "name": "Disjoncteur Tetra AC 16A Schneider", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-MONO-AC-32-SCH", "name": "Disjoncteur Mono AC 32A Schneider", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-MONO-DC-32-SCH", "name": "Disjoncteur Mono DC 32A Schneider", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-MONO-AC-20-LEG", "name": "Disjoncteur Mono AC 20A LeGrand", "group": "Elements de protection - KYA", "qty": 6},
    {"code": "DIS-MONO-DIFF-AC-20-SCH", "name": "Disjoncteur Mono Diff AC 20A Schneider", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-MONO-AC-20-SCH", "name": "Disjoncteur Mono AC 20A Schneider", "group": "Elements de protection - KYA", "qty": 2},
    {"code": "DIS-MONO-AC-10-LEG", "name": "Disjoncteur Mono AC 10A LeGrand", "group": "Elements de protection - KYA", "qty": 14},
    {"code": "DIS-MONO-AC-10-SCH", "name": "Disjoncteur Mono AC 10A Schneider", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "DIS-MONO-AC-16-LEG", "name": "Disjoncteur Mono AC 16A LeGrand", "group": "Elements de protection - KYA", "qty": 3},
    {"code": "PARAF-TETRA-65KA", "name": "Parafoudre tetra 65 kA", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "PARAF-MONO-40KA", "name": "Parafoudre Mono 40 kA", "group": "Elements de protection - KYA", "qty": 2},
    {"code": "INV-TRI-MAN", "name": "Inverseur triphase Manuel", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "INV-MONO-MAN-AUTO", "name": "Inverseur monophase Manuel/Automatique", "group": "Elements de protection - KYA", "qty": 3},
    {"code": "PF-GPV-32", "name": "Porte Fusible gPV 32 A", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "PF-GPV-30", "name": "Porte Fusible gPV 30 A", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "IH-1", "name": "Interrupteur Horaire", "group": "Elements de protection - KYA", "qty": 1},
    {"code": "BT-150A-GRIS", "name": "Bornier de terre 150A/50mm2 (gris)", "group": "Elements de protection - KYA", "qty": 11},
    {"code": "BT-PETIT-GRIS", "name": "Bornier de terre petit (gris)", "group": "Elements de protection - KYA", "qty": 5},
    {"code": "BT-PETIT-VJ", "name": "Bornier de terre petit (vert/jaune)", "group": "Elements de protection - KYA", "qty": 2},
    {"code": "PIQ-TERRE-2M", "name": "Piquet de terre de 2m", "group": "Elements de protection - KYA", "qty": 100},

    # ===== Luminaires =====
    {"code": "LUM-AIO-T1", "name": "Luminaire All-in-One Type 1", "group": "Luminaires - KYA", "qty": 1},
    {"code": "LUM-AIO-T2", "name": "Luminaire All-in-One Type 2", "group": "Luminaires - KYA", "qty": 7},
    {"code": "LUM-AIO-T3", "name": "Luminaire All-in-One Type 3", "group": "Luminaires - KYA", "qty": 41},
]


def _resolve_company() -> str | None:
    """Cherche la company KYA. Retourne None si introuvable."""
    if frappe.db.exists("Company", COMPANY_DEFAULT):
        return COMPANY_DEFAULT
    # Fallback : premiere company avec abbr KYA
    rows = frappe.db.get_all("Company", filters={"abbr": "KYA"}, fields=["name"], limit=1)
    if rows:
        return rows[0].name
    # Fallback : premiere company tout court
    rows = frappe.db.get_all("Company", fields=["name"], limit=1)
    return rows[0].name if rows else None


def _resolve_warehouse(company: str) -> str | None:
    """Cherche le warehouse Magasin KYA. Retourne None si introuvable."""
    if frappe.db.exists("Warehouse", WAREHOUSE_DEFAULT):
        return WAREHOUSE_DEFAULT
    # Fallback : premier warehouse avec 'Magasin KYA' dans le nom
    rows = frappe.db.get_all(
        "Warehouse",
        filters={"warehouse_name": ["like", "Magasin KYA%"], "company": company},
        fields=["name"],
        limit=1,
    )
    return rows[0].name if rows else None


def _ensure_item_groups() -> dict:
    """Cree les Item Groups KYA sous 'All Item Groups'."""
    stats = {"created": 0, "existing": 0, "errors": 0}
    parent = "All Item Groups"
    if not frappe.db.exists("Item Group", parent):
        parent = None

    for group_name in KYA_ITEM_GROUPS:
        if frappe.db.exists("Item Group", group_name):
            stats["existing"] += 1
            continue
        try:
            doc = frappe.new_doc("Item Group")
            doc.item_group_name = group_name
            if parent:
                doc.parent_item_group = parent
            doc.is_group = 0
            doc.insert(ignore_permissions=True)
            stats["created"] += 1
        except Exception:
            stats["errors"] += 1
            try:
                frappe.log_error(frappe.get_traceback(), f"setup_kya_stocks: group {group_name}")
            except Exception:
                pass
    return stats


def _ensure_items(company: str) -> dict:
    """Cree les Items KYA. Idempotent par item_code."""
    stats = {"created": 0, "existing": 0, "errors": 0}
    for it in KYA_ITEMS:
        if frappe.db.exists("Item", it["code"]):
            stats["existing"] += 1
            continue
        try:
            doc = frappe.new_doc("Item")
            doc.item_code = it["code"]
            doc.item_name = it["name"]
            doc.item_group = it["group"]
            doc.stock_uom = DEFAULT_UOM
            doc.is_stock_item = 1
            doc.include_item_in_manufacturing = 0
            doc.is_purchase_item = 1
            doc.is_sales_item = 1
            doc.insert(ignore_permissions=True)
            stats["created"] += 1
        except Exception:
            stats["errors"] += 1
            try:
                frappe.log_error(frappe.get_traceback(), f"setup_kya_stocks: item {it['code']}")
            except Exception:
                pass
    return stats


def _ensure_opening_stock(company: str, warehouse: str) -> dict:
    """Cree UN Stock Entry 'Material Receipt' avec toutes les quantites.

    Idempotent : si un Stock Entry avec le name OPENING_STOCK_ENTRY_NAME
    existe deja, on ne fait rien.
    """
    stats = {"created": False, "skipped": False, "rows": 0}

    if frappe.db.exists("Stock Entry", OPENING_STOCK_ENTRY_NAME):
        stats["skipped"] = True
        return stats

    try:
        se = frappe.new_doc("Stock Entry")
        se.name = OPENING_STOCK_ENTRY_NAME  # name explicite (autoname=hash sinon)
        se.naming_series = ""
        se.stock_entry_type = "Material Receipt"
        se.purpose = "Material Receipt"
        se.company = company
        se.posting_date = getdate(OPENING_DATE)
        se.set_posting_time = 1

        for it in KYA_ITEMS:
            # Saute les items qui n'ont pas ete crees (erreurs amont)
            if not frappe.db.exists("Item", it["code"]):
                continue
            se.append("items", {
                "item_code": it["code"],
                "qty": it["qty"],
                "uom": DEFAULT_UOM,
                "stock_uom": DEFAULT_UOM,
                "conversion_factor": 1,
                "t_warehouse": warehouse,
                "basic_rate": 0,  # pas de valorisation au depart
                "allow_zero_valuation_rate": 1,
            })

        stats["rows"] = len(se.items)
        if not se.items:
            return stats

        se.insert(ignore_permissions=True)
        se.submit()
        stats["created"] = True
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), "setup_kya_stocks: opening stock entry")
        except Exception:
            pass

    return stats


def execute() -> dict:
    """Entrypoint after_migrate. Idempotent. Ne leve jamais."""
    summary: dict = {}
    try:
        company = _resolve_company()
        if not company:
            summary["error"] = "Aucune company trouvee - skip"
            print(f"[setup_kya_stocks] {summary}")
            return summary
        summary["company"] = company

        summary["item_groups"] = _ensure_item_groups()
        summary["items"] = _ensure_items(company)

        warehouse = _resolve_warehouse(company)
        if warehouse:
            summary["warehouse"] = warehouse
            summary["opening_stock"] = _ensure_opening_stock(company, warehouse)
        else:
            summary["warehouse"] = None
            summary["opening_stock_skipped"] = "Magasin KYA - KYA introuvable"

        frappe.db.commit()
        frappe.clear_cache(doctype="Item")
        frappe.clear_cache(doctype="Item Group")
    except Exception as exc:
        summary["fatal"] = str(exc)
        try:
            frappe.log_error(frappe.get_traceback(), "setup_kya_stocks: top-level")
        except Exception:
            pass

    print(f"[setup_kya_stocks] {summary}")
    return summary

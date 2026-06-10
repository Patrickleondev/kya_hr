"""Import/Export Articles KYA (template CSV compatible format prod).

Format CSV attendu (matches export Frappe natif Article.csv) :
- Code de l'Article          (item_code, PK)
- Groupe d'Article           (item_group, cree si absent)
- Unite de Mesure par Defaut (stock_uom, defaut 'Nos')
- Nom de l'article           (item_name)
- Qte Totale Prevue          (info, pas utilisee a l'import)
- Entrepot par Defaut        (default_warehouse via Item Default)

Workflow :
1. download_template() : telecharge un CSV vide avec entetes + 2 lignes
   d'exemple. Compatible Excel/Google Sheets.

2. import_items(content_b64) : parse le CSV uploade, cree/MAJ les Item.
   Idempotent : matche par item_code, met a jour le reste si conflit.
   Retourne stats {created, updated, skipped, errors}.

3. export_items() : exporte tous les Items actifs + qty actuelle par
   entrepot. Reutilise par /kya-stocks-dashboard bouton 'Exporter'.

Securite : whitelist + role Stock User/Manager.
"""
from __future__ import annotations

import base64
import csv
import io

import frappe
from frappe.utils import flt, cstr


IMPORT_ROLES = {
    "Stock User", "Stock Manager", "System Manager",
    "Chef Service Achats",
}

CSV_HEADERS = [
    "Code de l'Article",
    "Groupe d'Article",
    "Unite de Mesure par Defaut",
    "Nom de l'article",
    "Qte Totale Prevue",
    "Entrepot par Defaut",
]

CSV_EXAMPLE_ROWS = [
    ["MOD-PV-455", "Modules PV - KYA", "Nos", "Module PV 455Wc", "0", "Magasin KYA - KYA"],
    ["lum/Finis3", "luminaires/Finis", "Unit", "Luminaire all in one TYPE 3", "0", ""],
]


def _check_role(action: str = "stock"):
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not (user_roles & IMPORT_ROLES):
        frappe.throw(
            f"Acces refuse - role Stock requis pour {action}",
            frappe.PermissionError,
        )


@frappe.whitelist(allow_guest=False)
def download_template() -> dict:
    """Retourne le CSV template en base64 + nom de fichier."""
    _check_role("download_template")

    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)
    writer.writerow(CSV_HEADERS)
    for row in CSV_EXAMPLE_ROWS:
        writer.writerow(row)

    csv_text = out.getvalue()
    return {
        "filename": "template-articles-kya.csv",
        "content_base64": base64.b64encode(csv_text.encode("utf-8")).decode("ascii"),
        "size": len(csv_text),
    }


def _ensure_item_group(name: str) -> str:
    """Cree l'Item Group s'il n'existe pas. Retourne le name final."""
    name = (name or "").strip()
    if not name:
        return "All Item Groups"
    if frappe.db.exists("Item Group", name):
        return name
    try:
        doc = frappe.new_doc("Item Group")
        doc.item_group_name = name
        doc.parent_item_group = "All Item Groups" if frappe.db.exists("Item Group", "All Item Groups") else None
        doc.is_group = 0
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        return "All Item Groups"


@frappe.whitelist(allow_guest=False)
def import_items(content_base64: str) -> dict:
    """Parse un CSV (base64) et cree/MAJ les Items.

    Idempotent : un item_code existant est mis a jour (item_name, group,
    uom) si necessaire ; un nouveau code est cree.
    """
    _check_role("import_items")

    if not content_base64:
        frappe.throw("Aucun contenu fourni")

    try:
        raw = base64.b64decode(content_base64).decode("utf-8-sig")
    except Exception as exc:
        frappe.throw(f"Decodage base64/UTF-8 echoue : {exc}")

    reader = csv.DictReader(io.StringIO(raw))
    stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": []}

    for idx, row in enumerate(reader, start=2):  # ligne 2 = premiere data (1 = entete)
        code = cstr(row.get(CSV_HEADERS[0]) or row.get("Code de l'Article") or row.get("item_code") or "").strip()
        if not code:
            stats["skipped"] += 1
            continue

        name = cstr(row.get(CSV_HEADERS[3]) or row.get("item_name") or "").strip()
        group_in = cstr(row.get(CSV_HEADERS[1]) or row.get("item_group") or "").strip()
        uom = cstr(row.get(CSV_HEADERS[2]) or row.get("stock_uom") or "Nos").strip() or "Nos"
        default_wh = cstr(row.get(CSV_HEADERS[5]) or row.get("default_warehouse") or "").strip()

        group = _ensure_item_group(group_in) if group_in else "All Item Groups"

        try:
            if frappe.db.exists("Item", code):
                doc = frappe.get_doc("Item", code)
                changed = False
                if name and doc.item_name != name:
                    doc.item_name = name
                    changed = True
                if doc.item_group != group and group:
                    doc.item_group = group
                    changed = True
                if doc.stock_uom != uom and uom:
                    doc.stock_uom = uom
                    changed = True
                if changed:
                    doc.save(ignore_permissions=True)
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
            else:
                doc = frappe.new_doc("Item")
                doc.item_code = code
                doc.item_name = name or code
                doc.item_group = group
                doc.stock_uom = uom
                doc.is_stock_item = 1
                doc.is_purchase_item = 1
                doc.is_sales_item = 1
                if default_wh and frappe.db.exists("Warehouse", default_wh):
                    company = frappe.db.get_value("Warehouse", default_wh, "company")
                    doc.append("item_defaults", {
                        "company": company,
                        "default_warehouse": default_wh,
                    })
                doc.insert(ignore_permissions=True)
                stats["created"] += 1
        except Exception as exc:
            stats["errors"].append({"line": idx, "code": code, "error": str(exc)})
            try:
                frappe.log_error(frappe.get_traceback(), f"stocks_import: row {idx} {code}")
            except Exception:
                pass

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Item")
    except Exception:
        pass

    return stats


@frappe.whitelist(allow_guest=False)
def export_items(item_group: str = "", warehouse: str = "") -> dict:
    """Exporte les Items + qty/valeur par entrepot dans un CSV base64.

    Format de sortie : meme entetes que CSV_HEADERS, + 2 colonnes
    supplementaires (Qte Actuelle, Valeur XOF).
    """
    _check_role("export_items")

    where_clauses = ["i.disabled = 0"]
    params: dict = {}
    if item_group:
        where_clauses.append("i.item_group = %(item_group)s")
        params["item_group"] = item_group
    if warehouse:
        where_clauses.append("(b.warehouse = %(warehouse)s OR b.warehouse IS NULL)")
        params["warehouse"] = warehouse

    where = " AND ".join(where_clauses)
    rows = frappe.db.sql(f"""
        SELECT
            i.name AS code,
            i.item_group AS gr,
            i.stock_uom AS uom,
            i.item_name AS name,
            COALESCE(b.actual_qty, 0) AS qty,
            COALESCE(b.warehouse, '') AS wh,
            COALESCE(b.actual_qty * b.valuation_rate, 0) AS value
        FROM `tabItem` i
        LEFT JOIN `tabBin` b ON b.item_code = i.name
        WHERE {where}
        ORDER BY i.item_group, i.name
    """, params, as_dict=True)

    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)
    writer.writerow(CSV_HEADERS + ["Qte Actuelle", "Valeur XOF"])
    for r in rows:
        writer.writerow([
            r["code"], r["gr"] or "", r["uom"] or "Nos", r["name"] or "",
            str(flt(r["qty"], 2)), r["wh"] or "",
            str(flt(r["value"], 2)),
        ])

    csv_text = out.getvalue()
    return {
        "filename": f"articles-kya-{frappe.utils.today()}.csv",
        "content_base64": base64.b64encode(csv_text.encode("utf-8")).decode("ascii"),
        "size": len(csv_text),
        "rows_exported": len(rows),
    }

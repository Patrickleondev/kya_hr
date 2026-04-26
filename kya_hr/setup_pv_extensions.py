"""
Setup Inventaire & Sorties Matériel — Extensions PV + Dashboard DG/DGA
─────────────────────────────────────────────────────────────────────
1) Étend PV Sortie Materiel : client, projet, chantier_libre, valeur_totale
2) Étend PV Sortie Materiel Item : item_code, warehouse, uom, valeur_unitaire, valeur_totale
3) Custom Field stock_projet sur Project (libellé chantier KYA)
"""
import frappe

# ─────────────── CUSTOM FIELDS PV SORTIE MATERIEL ───────────────
PV_CUSTOM_FIELDS = [
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "section_client_projet",
        "label": "Client / Projet / Chantier",
        "fieldtype": "Section Break",
        "insert_after": "company",
        "collapsible": 0,
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "client",
        "label": "Client",
        "fieldtype": "Link",
        "options": "Customer",
        "in_list_view": 1,
        "in_standard_filter": 1,
        "insert_after": "section_client_projet",
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "client_name",
        "label": "Nom Client",
        "fieldtype": "Data",
        "fetch_from": "client.customer_name",
        "read_only": 1,
        "insert_after": "client",
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "col_projet",
        "fieldtype": "Column Break",
        "insert_after": "client_name",
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "projet",
        "label": "Projet",
        "fieldtype": "Link",
        "options": "Project",
        "in_list_view": 1,
        "in_standard_filter": 1,
        "insert_after": "col_projet",
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "chantier_libre",
        "label": "Chantier (libre)",
        "fieldtype": "Data",
        "description": "Si pas de Project ERPNext — saisie libre du nom du chantier",
        "insert_after": "projet",
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "section_valeur",
        "label": "Valorisation",
        "fieldtype": "Section Break",
        "collapsible": 1,
        "insert_after": "items",
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "valeur_totale_xof",
        "label": "Valeur Totale Sortie (XOF)",
        "fieldtype": "Currency",
        "options": "XOF",
        "read_only": 1,
        "in_list_view": 1,
        "insert_after": "section_valeur",
    },
    {
        "dt": "PV Sortie Materiel",
        "fieldname": "nb_lignes",
        "label": "Nombre de lignes",
        "fieldtype": "Int",
        "read_only": 1,
        "insert_after": "valeur_totale_xof",
    },
]

# ─────────────── CUSTOM FIELDS ITEM CHILD ───────────────
PV_ITEM_CUSTOM_FIELDS = [
    {
        "dt": "PV Sortie Materiel Item",
        "fieldname": "item_code",
        "label": "Code Article",
        "fieldtype": "Link",
        "options": "Item",
        "in_list_view": 1,
        "insert_after": "designation",
    },
    {
        "dt": "PV Sortie Materiel Item",
        "fieldname": "warehouse",
        "label": "Magasin",
        "fieldtype": "Link",
        "options": "Warehouse",
        "in_list_view": 1,
        "insert_after": "qte_reellement_sortie",
    },
    {
        "dt": "PV Sortie Materiel Item",
        "fieldname": "uom",
        "label": "Unité",
        "fieldtype": "Link",
        "options": "UOM",
        "fetch_from": "item_code.stock_uom",
        "insert_after": "warehouse",
    },
    {
        "dt": "PV Sortie Materiel Item",
        "fieldname": "valeur_unitaire",
        "label": "Valeur Unit. (XOF)",
        "fieldtype": "Currency",
        "options": "XOF",
        "fetch_from": "item_code.valuation_rate",
        "insert_after": "uom",
    },
    {
        "dt": "PV Sortie Materiel Item",
        "fieldname": "valeur_totale",
        "label": "Valeur Totale (XOF)",
        "fieldtype": "Currency",
        "options": "XOF",
        "read_only": 1,
        "in_list_view": 1,
        "insert_after": "valeur_unitaire",
    },
]


def _create_custom_field(cfg):
    name = f"{cfg['dt']}-{cfg['fieldname']}"
    if frappe.db.exists("Custom Field", name):
        cf = frappe.get_doc("Custom Field", name)
    else:
        cf = frappe.new_doc("Custom Field")
        cf.dt = cfg["dt"]
        cf.fieldname = cfg["fieldname"]
    for k, v in cfg.items():
        setattr(cf, k, v)
    cf.save(ignore_permissions=True)


def run():
    print("=== Extension PV Sortie Materiel — Client/Projet/Items ===")
    for cf in PV_CUSTOM_FIELDS:
        try:
            _create_custom_field(cf)
            print(f"  ✓ {cf['dt']}.{cf['fieldname']}")
        except Exception as e:
            print(f"  ✗ {cf['dt']}.{cf['fieldname']}: {e}")
    for cf in PV_ITEM_CUSTOM_FIELDS:
        try:
            _create_custom_field(cf)
            print(f"  ✓ {cf['dt']}.{cf['fieldname']}")
        except Exception as e:
            print(f"  ✗ {cf['dt']}.{cf['fieldname']}: {e}")
    frappe.db.commit()
    frappe.clear_cache()
    print(f"\n✅ {len(PV_CUSTOM_FIELDS) + len(PV_ITEM_CUSTOM_FIELDS)} custom fields PV configurés")

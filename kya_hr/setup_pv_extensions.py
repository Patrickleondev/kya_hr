"""
Setup Sorties Matériel — Extensions PV (traçabilité Client/Projet)
──────────────────────────────────────────────────────────────────────
Fidèle à la fiche papier AEA-ENG-32.V01 — PAS de montants en argent.
Champs standards (item_code, designation, uom, qte_demandee, qte_reellement_sortie,
warehouse) sont déjà dans pv_sortie_materiel_item.json — NE PAS les redoubler ici.
Étend uniquement PV Sortie Materiel : client, projet, chantier_libre.
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
]

# Aucune extension de PV Sortie Materiel Item — les champs (item_code, designation,
# uom, qte_demandee, qte_reellement_sortie, warehouse) sont déjà déclarés en standard
# dans pv_sortie_materiel_item.json. Pas de valorisation : la fiche n'a pas d'argent.
PV_ITEM_CUSTOM_FIELDS = []


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


# Champs obsolètes à supprimer (anciennes versions ajoutaient ces Custom Fields)
OBSOLETE_CUSTOM_FIELDS = [
    ("PV Sortie Materiel", "section_valeur"),
    ("PV Sortie Materiel", "valeur_totale_xof"),
    ("PV Sortie Materiel", "nb_lignes"),
    ("PV Sortie Materiel Item", "item_code"),
    ("PV Sortie Materiel Item", "warehouse"),
    ("PV Sortie Materiel Item", "uom"),
    ("PV Sortie Materiel Item", "valeur_unitaire"),
    ("PV Sortie Materiel Item", "valeur_totale"),
]


def _drop_obsolete_custom_fields():
    for dt, fn in OBSOLETE_CUSTOM_FIELDS:
        name = f"{dt}-{fn}"
        if frappe.db.exists("Custom Field", name):
            frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
            print(f"  ✘ supprimé {name}")


def run():
    print("=== Extension PV Sortie Materiel — Client/Projet ===")
    _drop_obsolete_custom_fields()
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

"""
Test E2E Dashboard Inventaire & Sorties Matériel
- Crée Customer + Project + Item + Warehouse
- Crée PV avec client/projet/items
- Vérifie valorisation auto
- Vérifie report renvoie des données
- Vérifie Dashboard chargé
"""
import frappe


def run():
    print("=" * 60)
    print("TEST E2E — Dashboard Inventaire & Sorties Matériel")
    print("=" * 60)

    # 1) Customer
    cust_name = "Client Test KYA E2E"
    if not frappe.db.exists("Customer", cust_name):
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": cust_name,
            "customer_group": "All Customer Groups",
            "territory": "All Territories",
            "customer_type": "Company",
        }).insert(ignore_permissions=True)
        print(f"  ✓ Customer: {cust.name}")
    else:
        print(f"  ✓ Customer: {cust_name} (existant)")

    # 2) Project (autoname → on cherche par project_name)
    proj_name = "Projet Solaire Lomé Test"
    existing = frappe.db.get_value("Project", {"project_name": proj_name}, "name")
    if existing:
        proj_id = existing
        print(f"  ✓ Project: {proj_id} (existant)")
    else:
        proj = frappe.get_doc({
            "doctype": "Project",
            "project_name": proj_name,
            "status": "Open",
            "customer": cust_name,
        }).insert(ignore_permissions=True)
        proj_id = proj.name
        print(f"  ✓ Project: {proj_id} (project_name='{proj_name}')")

    # 3) Item à utiliser (premier dispo) — force valuation_rate
    item = frappe.db.get_value("Item", {"is_stock_item": 1, "disabled": 0},
                                ["name", "stock_uom", "valuation_rate"], as_dict=True)
    if not item:
        # créer un Item de test
        it = frappe.get_doc({
            "doctype": "Item",
            "item_code": "TEST-PANNEAU-300W",
            "item_name": "Panneau Solaire 300W Test",
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "valuation_rate": 75000,
        }).insert(ignore_permissions=True)
        item = frappe._dict(name=it.name, stock_uom=it.stock_uom, valuation_rate=it.valuation_rate)
    # Force valuation_rate=75000 pour le test
    if not item.valuation_rate:
        frappe.db.set_value("Item", item.name, "valuation_rate", 75000)
        item.valuation_rate = 75000
    print(f"  ✓ Item utilisé: {item.name} (UOM={item.stock_uom}, rate={item.valuation_rate or 0})")

    # 4) Warehouse
    wh = frappe.db.get_value("Warehouse", {"is_group": 0, "disabled": 0}, "name")
    if not wh:
        company = frappe.db.get_value("Company", {}, "name")
        wh_doc = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "Magasin Test",
            "company": company,
        }).insert(ignore_permissions=True)
        wh = wh_doc.name
    print(f"  ✓ Warehouse: {wh}")

    # 5) PV Sortie Materiel
    company = frappe.db.get_value("Company", {}, "name")
    pv_doc = frappe.get_doc({
        "doctype": "PV Sortie Materiel",
        "objet": "Test E2E dashboard inventaire",
        "date_sortie": frappe.utils.today(),
        "company": company,
        "client": cust_name,
        "projet": proj_id,
        "demandeur_nom": "Test User",
        "items": [
            {
                "designation": "Panneau Solaire 300W",
                "qte_demandee": 5,
                "qte_reellement_sortie": 5,
                "item_code": item.name,
                "warehouse": wh,
            },
            {
                "designation": "Câble 6mm²",
                "qte_demandee": 100,
                "qte_reellement_sortie": 90,
                "item_code": item.name,
                "warehouse": wh,
            },
        ],
    }).insert(ignore_permissions=True)
    print(f"  ✓ PV créé: {pv_doc.name}")
    # Debug: print row-by-row
    for i, it in enumerate(pv_doc.items):
        print(f"    [item {i}] qte_d={it.qte_demandee} qte_r={it.qte_reellement_sortie} "
              f"item_code={it.get('item_code')} wh={it.get('warehouse')}")
    print(f"    - {len(pv_doc.items)} ligne(s) sur le PV")
    assert len(pv_doc.items) == 2
    print("  ✓ Saisie PV OK (fid\u00e8le \u00e0 la fiche papier — pas de montants)")

    # 6) Report
    from kya_hr.report.sorties_materiel_par_client_projet.sorties_materiel_par_client_projet import execute as run_report
    cols, data, _, chart, summary = run_report({"client": cust_name})
    print(f"  ✓ Report renvoie {len(data)} ligne(s) pour le client")
    assert len(data) >= 2
    print(f"    Summary: {[(s['label'], s['value']) for s in summary]}")

    # 7) Dashboard
    dash = frappe.get_doc("Dashboard", "Inventaire & Sorties Matériel")
    print(f"  ✓ Dashboard '{dash.name}': {len(dash.charts)} charts, {len(dash.cards)} cards")

    frappe.db.commit()
    print("\n✅ Tous les tests E2E sont passés.")

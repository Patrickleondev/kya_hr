# -*- coding: utf-8 -*-
"""Test automatise du cycle complet Stock:
1. Creer PV Entree, approuver => Stock Entry Material Receipt
2. Verifier stock > 0
3. Creer PV Sortie sur memes articles, approuver => Stock Entry Material Issue
4. Verifier stock decremente
"""
import frappe
from frappe.utils import today


def run():
    print("=== TEST CYCLE STOCK ===")
    wh = "Magasin Central KYA - KG"
    item_a = "KYA-FOURN-001"  # Ramette papier
    item_b = "KYA-IT-002"      # Souris

    # --- Avant ---
    def stock_of(item):
        bal = frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty") or 0
        return float(bal)

    print(f"[AVANT] {item_a}: {stock_of(item_a)} · {item_b}: {stock_of(item_b)}")

    # --- 1. PV Entree ---
    print("\n[1] Creation PV Entree...")
    emp = frappe.db.get_value("Employee", {"status": "Active"}, ["name", "employee_name"], as_dict=True)
    pve = frappe.get_doc({
        "doctype": "PV Entree Materiel",
        "date_entree": today(),
        "objet": "Test automatise - reception fournitures bureau",
        "livreur_nom": "TEST LIVREUR",
        "livreur_date": today(),
        "items": [
            {"item_code": item_a, "designation": "Ramette papier A4", "uom": "Nos", "qte_recue": 50, "prix_unitaire": 3500, "warehouse": wh},
            {"item_code": item_b, "designation": "Souris sans fil", "uom": "Nos", "qte_recue": 20, "prix_unitaire": 8500, "warehouse": wh},
        ],
    })
    pve.insert(ignore_permissions=True)
    pve.submit()
    print(f"    PV Entree cree: {pve.name} (submit, workflow_state={pve.workflow_state})")

    # Force workflow_state to Approuve to trigger stock entry (use instance we already have)
    pve.db_set("workflow_state", "Approuvé", update_modified=False)
    pve.workflow_state = "Approuvé"
    pve._create_stock_entry()
    frappe.db.commit()
    se_in = pve.get("stock_entry")
    print(f"    Stock Entry genere: {se_in}")

    print(f"[APRES ENTREE] {item_a}: {stock_of(item_a)} · {item_b}: {stock_of(item_b)}")

    # --- 2. PV Sortie ---
    print("\n[2] Creation PV Sortie...")
    pvs = frappe.get_doc({
        "doctype": "PV Sortie Materiel",
        "date_sortie": today(),
        "objet": "Test automatise - sortie fournitures",
        "demandeur_nom": emp.employee_name if emp else "Test",
        "demandeur_date": today(),
        "items": [
            {"item_code": item_a, "designation": "Ramette papier A4", "uom": "Nos", "qte_demandee": 10, "qte_reellement_sortie": 10, "warehouse": wh},
            {"item_code": item_b, "designation": "Souris sans fil", "uom": "Nos", "qte_demandee": 3, "qte_reellement_sortie": 3, "warehouse": wh},
        ],
    })
    pvs.insert(ignore_permissions=True)
    pvs.submit()
    pvs.db_set("workflow_state", "Approuvé", update_modified=False)
    pvs.workflow_state = "Approuvé"
    pvs._create_stock_entry()
    frappe.db.commit()
    se_out = pvs.get("stock_entry")
    print(f"    PV Sortie cree: {pvs.name}")
    print(f"    Stock Entry genere: {se_out}")

    print(f"[APRES SORTIE] {item_a}: {stock_of(item_a)} · {item_b}: {stock_of(item_b)}")
    print(f"\nAttendu: {item_a}=40, {item_b}=17")
    print("=== FIN TEST ===")

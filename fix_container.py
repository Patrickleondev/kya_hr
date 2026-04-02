#!/usr/bin/env python3
"""Exécuté directement dans le container bench pour corriger les workspaces."""
import sys, os
sys.path.insert(0, '/home/frappe/frappe-bench/apps/frappe')
sys.path.insert(0, '/home/frappe/frappe-bench/apps/erpnext')
sys.path.insert(0, '/home/frappe/frappe-bench/apps/kya_hr')
sys.path.insert(0, '/home/frappe/frappe-bench/apps/kya_services')

import frappe, json
frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()

# 1 - Gestion Equipe : remove "Tableau de Bord" duplicate
try:
    ws = frappe.get_doc("Workspace", "Gestion Equipe")
    print("GE shortcuts before:", [s.label for s in ws.shortcuts])
    ws.shortcuts = [s for s in ws.shortcuts if s.label not in ("Tableau de Bord",)]
    ws.save(ignore_permissions=True)
    frappe.db.commit()
    print("GE shortcuts after:", [s.label for s in ws.shortcuts])
    print("[OK] Gestion Equipe fixed")
except Exception as e:
    print("[ERR] Gestion Equipe:", e)

# 2 - Number Card filters (remove 5th False element)
fixes = [
    ("Stagiaires Actifs", json.dumps([
        ["Employee", "employment_type", "=", "Stage"],
        ["Employee", "status", "=", "Active"]
    ])),
    ("Permissions Stagiaires en Attente", json.dumps([
        ["Permission Sortie Stagiaire", "workflow_state", "not in", ["Approuve", "Rejete"]]
    ])),
    ("Bilans de Stage Soumis", json.dumps([
        ["Bilan Fin de Stage", "docstatus", "!=", 0]
    ])),
]
for nc_name, filt in fixes:
    if frappe.db.exists("Number Card", nc_name):
        frappe.db.set_value("Number Card", nc_name, "filters_json", filt)
        print(f"[OK] NC '{nc_name}' filtre corrige")
    else:
        print(f"[MISS] NC '{nc_name}' non trouvee")

frappe.db.commit()

# 3 - Espace Stagiaires shortcuts
try:
    ws2 = frappe.get_doc("Workspace", "Espace Stagiaires")
    labels = [s.label for s in ws2.shortcuts]
    print("Stagiaires shortcuts:", labels)
    if "Dashboard Stagiaires" not in str(labels):
        ws2.append("shortcuts", {
            "label": "Dashboard Stagiaires",
            "type": "URL",
            "url": "/kya-dashboard-stagiaires",
            "color": "Green",
            "icon": "bar-chart-line"
        })
        ws2.save(ignore_permissions=True)
        frappe.db.commit()
        print("[OK] Dashboard shortcut ajoute")
except Exception as e:
    print("[ERR] Espace Stagiaires:", e)

frappe.db.commit()
frappe.destroy()
print("=== ALL DONE ===")

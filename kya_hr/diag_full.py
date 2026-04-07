"""Chercher les tables workspace et diagnostiquer les links."""
import frappe
import json


def execute():
    # Tables liees aux workspaces
    print("=== TABLES WORKSPACE EN DB ===")
    tables = frappe.db.sql("SHOW TABLES LIKE '%orkspace%'")
    for t in tables:
        print(f"  {t[0]}")

    # Links en DB
    print("\n=== LINKS EN DB ===")
    for ws in ["Espace Stagiaires", "KYA Services",
               "Achats & Approvisionnement", "Stock & Logistique"]:
        links = frappe.db.get_all(
            "Workspace Link",
            filters={"parent": ws},
            fields=["type", "label", "link_to", "link_type"],
            order_by="idx"
        )
        print(f"\n  {ws} ({len(links)} links):")
        for lk in links:
            print(f"    [{lk.type}] {lk.label} -> {lk.link_to} ({lk.link_type})")

    # Number Cards KYA Services
    print("\n=== NUMBER CARDS EN DB ===")
    for c in ["Total Formulaires", "Formulaires Actifs",
              "Total Evaluations", "Reponses Recues"]:
        exists = frappe.db.exists("Number Card", c)
        print(f"  {'OK' if exists else 'MANQUANT'}: {c}")

    print("\n=== DASHBOARD CHARTS EN DB ===")
    for c in ["Formulaires par Statut", "Evaluations par Type"]:
        exists = frappe.db.exists("Dashboard Chart", c)
        print(f"  {'OK' if exists else 'MANQUANT'}: {c}")

    # Modules kya_services API
    print("\n=== KYA SERVICES - fichiers API ===")
    import os
    bench = frappe.utils.get_bench_path()
    api_path = os.path.join(bench, "apps", "kya_services", "kya_services", "api.py")
    print(f"  api.py exists: {os.path.exists(api_path)}")
    if os.path.exists(api_path):
        with open(api_path) as f:
            raw = f.read()
        import re
        methods = re.findall(r"def (\w+)\(", raw)
        whitelisted = re.findall(r"@frappe\.whitelist.*\ndef (\w+)\(", raw)
        print(f"  all methods: {methods}")
        print(f"  whitelisted: {whitelisted}")


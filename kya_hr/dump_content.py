"""Dumper le content brut des workspaces KYA pour analyser la structure."""
import frappe
import json


def execute():
    for ws_name in ["Espace Stagiaires", "KYA Services"]:
        doc = frappe.get_doc("Workspace", ws_name)
        print(f"\n=== {ws_name} CONTENT RAW ===")
        print(doc.content or "(empty)")
        print(f"\n=== {ws_name} LINKS RAW ===")
        for lk in doc.links:
            print(f"  type={lk.type} label={lk.label} link_to={lk.link_to} link_type={lk.link_type}")

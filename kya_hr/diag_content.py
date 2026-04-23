"""
Diagnostic complet: voir content vs links pour chaque workspace KYA
"""
import frappe
import json


def execute():
    workspaces = [
        "Espace Stagiaires",
        "KYA Services",
        "Achats & Approvisionnement",
        "Stock & Logistique",
    ]
    for ws_name in workspaces:
        doc = frappe.get_doc("Workspace", ws_name)
        content_raw = doc.content or ""
        links_count = len(doc.links)
        print(f"\n=== {ws_name} ===")
        print(f"  links count in DB: {links_count}")
        print(f"  content length: {len(content_raw)}")
        print(f"  modified: {doc.modified}")
        if content_raw:
            try:
                content = json.loads(content_raw)
                # Count items with label in content
                items = []
                def collect(nodes):
                    if isinstance(nodes, list):
                        for n in nodes:
                            collect(n)
                    elif isinstance(nodes, dict):
                        if nodes.get("type") in ("card", "link", "shortcut"):
                            label = nodes.get("data", {}).get("label", "")
                            if label:
                                items.append(label)
                        for v in nodes.values():
                            if isinstance(v, (list, dict)):
                                collect(v)
                collect(content)
                print(f"  content items found: {items[:10]}")
            except Exception as e:
                print(f"  content parse error: {e}")
        else:
            print("  content: EMPTY (only links will show)")

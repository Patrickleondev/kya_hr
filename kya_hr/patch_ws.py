import frappe
import json

def patch_workspaces():
    print("\n--- PATCHING STANDARD WORKSPACES ---")
    
    # === 1. Buying Workspace ===
    if frappe.db.exists("Workspace", "Buying"):
        print("Patching Buying...")
        ws = frappe.get_doc("Workspace", "Buying")
        
        # Add Shortcuts
        new_shortcuts = [
            {"label": "PV Sortie Materiel", "type": "DocType", "link_to": "PV Sortie Materiel", "color": "Orange"},
            {"label": "Demande Achat KYA", "type": "DocType", "link_to": "Demande Achat KYA", "color": "Blue"}
        ]
        
        for s in new_shortcuts:
            if not any(x.label == s["label"] for x in ws.shortcuts):
                ws.append("shortcuts", s)
        
        # Add Links (under a new card or existing one)
        new_links = [
            {"label": "PV Sortie Materiel", "type": "Link", "link_type": "DocType", "link_to": "PV Sortie Materiel", "onboard": 0},
            {"label": "Demande Achat KYA", "type": "Link", "link_type": "DocType", "link_to": "Demande Achat KYA", "onboard": 0}
        ]
        
        for l in new_links:
            if not any(x.label == l["label"] for x in ws.links):
                ws.append("links", l)
        
        ws.save(ignore_permissions=True)
        print("  → Buying patched.")

    # === 2. Leaves Workspace ===
    if frappe.db.exists("Workspace", "Leaves"):
        print("Patching Leaves...")
        ws = frappe.get_doc("Workspace", "Leaves")
        
        # Add Shortcut for Planning
        if not any(x.label == "Planning des Cong\u00e9s" for x in ws.shortcuts):
            ws.append("shortcuts", {
                "label": "Planning des Cong\u00e9s", 
                "type": "DocType", 
                "link_to": "Leave Application", # Using Leave Application as proxy if no specific planning doctype
                "color": "Green"
            })
        
        ws.save(ignore_permissions=True)
        print("  → Leaves patched.")

    frappe.db.commit()
    frappe.clear_cache()
    print("\n--- ALL PATCHES DONE ---")

if __name__ == "__main__":
    patch_workspaces()

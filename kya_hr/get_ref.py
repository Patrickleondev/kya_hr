import frappe
import json

def get_ref():
    frappe.init("frontend-test")
    frappe.connect()
    
    if frappe.db.exists("Workspace", "People"):
        w = frappe.get_doc("Workspace", "People")
        print("--- PEOPLE WORKSPACE DEFINITION ---")
        print(f"Parent Page: {w.parent_page}")
        print(f"Module: {w.module}")
        print(f"Content length: {len(w.content or '')}")
        print("\nContent excerpt:")
        print((w.content or "")[:500])
        
        print("\nShortcuts:")
        print([s.label for s in w.shortcuts])
        print("Links:")
        print([s.label for s in w.links])

if __name__ == "__main__":
    get_ref()

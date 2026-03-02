import frappe

def final_repair():
    print("--- 1. Cleaning up corrupted translations ---")
    # Delete corrupted entries
    for term in ['éhat', 'étifs', 'ànalyse', 'étif']:
        frappe.db.delete("Translation", {"translated_text": ["like", f"%{term}%"]})
        print(f"Deleted translations containing: {term}")
    
    # Force correct translations for core terms showing in screenshots
    frappe.get_doc({
        "doctype": "Translation",
        "language": "fr",
        "source_text": "Achat",
        "translated_text": "Achat"
    }).insert(ignore_permissions=True)
    
    frappe.get_doc({
        "doctype": "Translation",
        "language": "fr",
        "source_text": "Actifs",
        "translated_text": "Actifs"
    }).insert(ignore_permissions=True)

    print("--- 2. Renaming Workflows to French ---")
    map_wf = {
        "KYA Procurement Flow": "Flux d'Achat KYA",
        "Workflow Permission Stagiaire": "Flux de Permission Stagiaire",
        "Workflow Ticket de Sortie": "Flux de Ticket de Sortie",
        "Flux de Planning Congés": "Flux de Planning des Congés"
    }
    for old, new in map_wf.items():
        if frappe.db.exists("Workflow", old):
            frappe.rename_doc("Workflow", old, new, force=True)
            print(f"Renamed Workflow: {old} -> {new}")

    print("--- 3. Verifying Web Form and adding link to Workspace ---")
    wf_name = "KYA Purchase Request Web Form"
    if frappe.db.exists("Web Form", wf_name):
        doc = frappe.get_doc("Web Form", wf_name)
        doc.is_standard = 0 # Ensure we can edit
        doc.published = 1
        doc.save(ignore_permissions=True)
        route = doc.route
        print(f"Web Form Route: /{route}")
        
        # Add to Workspace KYA RH & Op
        ws = frappe.get_doc("Workspace", "KYA RH & Op")
        # Check if already exists
        exists = any(l.link_to == wf_name and l.link_type == "Web Form" for l in ws.links)
        if not exists:
            ws.append("links", {
                "label": "Formulaire Demande d'Achat",
                "link_to": wf_name,
                "link_type": "Web Form"
            })
            ws.save(ignore_permissions=True)
            print("Added Web Form link to Workspace.")

    frappe.db.commit()
    print("✅ Final French touch complete.")

if __name__ == "__main__":
    final_repair()

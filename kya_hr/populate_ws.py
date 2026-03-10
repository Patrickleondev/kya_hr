import frappe
import json

def execute():
    # Update KYA Services Workspace
    if frappe.db.exists("Workspace", "KYA Services"):
        ws = frappe.get_doc("Workspace", "KYA Services")
        ws.set('shortcuts', [])
        ws.set('links', [])
        ws.append("shortcuts", {"label": "Formulaires KYA", "type": "DocType", "link_to": "KYA Form", "color": "Green"})
        ws.append("links", {"type": "Card Break", "label": "Gestion des Formulaires"})
        ws.append("links", {"type": "Link", "label": "Les Formulaires", "link_type": "DocType", "link_to": "KYA Form"})
        ws.append("links", {"type": "Link", "label": "Les Questions", "link_type": "DocType", "link_to": "KYA Form Question"})
        ws.append("links", {"type": "Link", "label": "Les Reponses", "link_type": "DocType", "link_to": "KYA Form Response"})
        
        content = [
            {"id": "Header1", "type": "header", "data": {"text": "<span class=\"h4\"><b>Raccourcis</b></span>", "col": 12}},
            {"id": "Shortcut1", "type": "shortcut", "data": {"shortcut_name": "Formulaires KYA", "col": 4}},
            {"id": "Spacer1", "type": "spacer", "data": {"col": 12}},
            {"id": "Header2", "type": "header", "data": {"text": "<span class=\"h4\"><b>Formulaires & Reponses</b></span>", "col": 12}},
            {"id": "Card1", "type": "card", "data": {"card_name": "Gestion des Formulaires", "col": 4}}
        ]
        ws.content = json.dumps(content)
        ws.save(ignore_permissions=True)
        print("Updated Workspace: KYA Services")

    # Update KYA Stagiaires Workspace
    if frappe.db.exists("Workspace", "KYA Stagiaires"):
        ws = frappe.get_doc("Workspace", "KYA Stagiaires")
        ws.set('shortcuts', [])
        ws.set('links', [])
        ws.append("shortcuts", {"label": "Permission Sortie Stagiaire", "type": "DocType", "link_to": "Permission Sortie Stagiaire", "color": "Blue"})
        ws.append("links", {"type": "Card Break", "label": "Gestion des Stagiaires"})
        ws.append("links", {"type": "Link", "label": "Permissions de Sortie", "link_type": "DocType", "link_to": "Permission Sortie Stagiaire"})
        ws.append("links", {"type": "Link", "label": "Bilan Fin de Stage", "link_type": "DocType", "link_to": "Bilan Fin de Stage"})
        
        content = [
            {"id": "H1", "type": "header", "data": {"text": "<span class=\"h4\"><b>Raccourcis</b></span>", "col": 12}},
            {"id": "S1", "type": "shortcut", "data": {"shortcut_name": "Permission Sortie Stagiaire", "col": 4}},
            {"id": "Sp", "type": "spacer", "data": {"col": 12}},
            {"id": "H2", "type": "header", "data": {"text": "<span class=\"h4\"><b>Dossiers</b></span>", "col": 12}},
            {"id": "C1", "type": "card", "data": {"card_name": "Gestion des Stagiaires", "col": 4}}
        ]
        ws.content = json.dumps(content)
        ws.save(ignore_permissions=True)
        print("Updated Workspace: KYA Stagiaires")
        
    frappe.db.commit()


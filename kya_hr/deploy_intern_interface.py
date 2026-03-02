import frappe
import json
import traceback

def run():
    print('=== DEPLOIEMENT INTERFACE STAGIAIRES (ERROR TRAPPED) ===')
    try:
        if frappe.db.exists('Workspace', 'KYA Stagiaires'):
            frappe.delete_doc('Workspace', 'KYA Stagiaires', force=True)
            
        print('Creating workspace...')
        content_items = [
            {'type': 'header', 'data': {'text': 'Stagiaires', 'col': 12, 'level': 4}}
        ]
        
        links = [
            {'type': 'Card Break', 'label': 'Stagiaires', 'hidden': 0},
            {'type': 'Link', 'label': 'Stagiaire', 'link_to': 'Employee', 'link_type': 'DocType', 'hidden': 0, 'onboard': 1},
        ]
        
        ws_doc = frappe.get_doc({
            'doctype': 'Workspace',
            'name': 'KYA Stagiaires',
            'label': 'KYA Stagiaires',
            'icon': 'graduation-cap',
            'module': 'KYA HR',
            'category': 'Modules',
            'is_standard': 0,
            'public': 1,
            'content': json.dumps(content_items),
            'links': links
        })
        ws_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print('Workspace created successfully!')
    except Exception as e:
        print('WORKSPACE ERROR:', str(e))
        traceback.print_exc()\

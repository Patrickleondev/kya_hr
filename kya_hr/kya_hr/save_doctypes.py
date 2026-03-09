import frappe

def run():
    frappe.init(site='frontend')
    frappe.connect()
    
    doctypes_to_save = ['PV Sortie Materiel', 'Permission Sortie Stagiaire', 'Bilan Fin de Stage', 'KYA Form']
    for dt in doctypes_to_save:
        try:
            if frappe.db.exists('DocType', dt):
                doc = frappe.get_doc('DocType', dt)
                doc.save(ignore_permissions=True)
                print(f"Saved JSON for DocType: {dt}")
        except Exception as e:
            print(f"Failed to save {dt}: {e}")
            
    try:
        if frappe.db.exists('Workspace', 'KYA Services'):
            doc = frappe.get_doc('Workspace', 'KYA Services')
            doc.save(ignore_permissions=True)
            print("Saved Workspace: KYA Services")
        if frappe.db.exists('Workspace', 'KYA Stagiaires'):
            doc = frappe.get_doc('Workspace', 'KYA Stagiaires')
            doc.save(ignore_permissions=True)
            print("Saved Workspace: KYA Stagiaires")
    except Exception as e:
        print(f"Failed to save workspaces: {e}")
            
    frappe.destroy()

if __name__ == '__main__':
    run()

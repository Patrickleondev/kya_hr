import frappe, json

def execute():
    # 1 - Supprimer shortcut doublon dans Gestion Equipe
    try:
        frappe.db.sql("DELETE FROM `tabWorkspace Shortcut` WHERE parent = 'Gestion Equipe' AND label = 'Tableau de Bord'")
        frappe.db.commit()
        print("[OK] Doublon Tableau de Bord supprime")
    except Exception as e:
        print("[ERR GE]", e)

    # 2 - Corriger filtres Number Cards (enlever 5eme element False)
    nc_fixes = [
        ("Stagiaires Actifs", json.dumps([["Employee","employment_type","=","Stage"],["Employee","status","=","Active"]])),
        ("Permissions Stagiaires en Attente", json.dumps([["Permission Sortie Stagiaire","workflow_state","not in",["Approuve","Rejete"]]])),
        ("Bilans de Stage Soumis", json.dumps([["Bilan Fin de Stage","docstatus","!=",0]])),
    ]
    for nc_name, filt in nc_fixes:
        try:
            if frappe.db.exists("Number Card", nc_name):
                frappe.db.set_value("Number Card", nc_name, "filters_json", filt)
                print(f"[OK] NC {nc_name}")
            else:
                print(f"[MISS] NC {nc_name}")
        except Exception as e:
            print(f"[ERR NC {nc_name}]", e)

    frappe.db.commit()

    # 3 - Espace Stagiaires: ajouter shortcut dashboard si absent
    try:
        rows = frappe.db.sql("SELECT label FROM `tabWorkspace Shortcut` WHERE parent = 'Espace Stagiaires'", as_dict=1)
        labels = [r.label for r in rows]
        print("[Stag] shortcuts:", labels)
        if not any("Dashboard" in l for l in labels):
            frappe.db.sql("""
                INSERT INTO `tabWorkspace Shortcut`
                (name, parent, parenttype, parentfield, label, type, url, color, icon)
                VALUES (UUID(), 'Espace Stagiaires', 'Workspace', 'shortcuts',
                '📊 Dashboard Stagiaires', 'URL', '/kya-dashboard-stagiaires', 'Green', 'bar-chart-line')
            """)
            frappe.db.commit()
            print("[OK] Shortcut Dashboard ajoute")
    except Exception as e:
        print("[ERR Stag]", e)

    frappe.db.commit()
    print("=== DONE ===")

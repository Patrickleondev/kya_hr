"""
patch_kya_stagiaires_ws.py — Patch post-création workspace KYA Stagiaires
Ajoute les links (sidebar nav) et shortcuts manquants.
"""
import frappe
import json


def execute():
    ws_name = "KYA Stagiaires"

    if not frappe.db.exists("Workspace", ws_name):
        print(f"[ERR] Workspace '{ws_name}' n'existe pas. Créez-le d'abord.")
        return

    print(f"=== PATCH WORKSPACE '{ws_name}' ===\n")

    # 1. S'assurer que `type` = "Module" est défini
    frappe.db.sql(
        "UPDATE `tabWorkspace` SET type='Module', module='KYA HR', icon='users', "
        "is_hidden=0 WHERE name=%s",
        ws_name
    )

    # 2. Links (sidebar navigation)
    frappe.db.delete("Workspace Link", {"parent": ws_name})
    links_data = [
        ("Card Break", "🎓 Gestion Stagiaires", None, None, 1),
        ("Link", "Espace Stagiaires", "Espace Stagiaires", "Workspace", 2),
        ("Link", "Autorisations", "Permission Sortie Stagiaire", "DocType", 3),
        ("Link", "Bilan", "Bilan Fin de Stage", "DocType", 4),
        ("Link", "Stagiaires", "Employee", "DocType", 5),
        ("Link", "Présences", "Attendance", "DocType", 6),
        ("Card Break", "📊 Rapports Présences", None, None, 7),
        ("Link", "Rapport Présences", "Rapport Présence Stagiaires", "Report", 8),
        ("Link", "Tableau de Bord", "Tableau de Bord Stagiaires", "Report", 9),
    ]
    for ltype, label, link_to, link_type, idx in links_data:
        frappe.db.sql(
            "INSERT INTO `tabWorkspace Link` "
            "(name, parent, parenttype, parentfield, idx, type, label, link_to, link_type, hidden) "
            "VALUES (%s, %s, 'Workspace', 'links', %s, %s, %s, %s, %s, 0)",
            (frappe.generate_hash(length=10), ws_name, idx, ltype, label,
             link_to or "", link_type or "")
        )
    print(f"  [OK] {len(links_data)} links insérés")

    # 3. Shortcuts
    frappe.db.delete("Workspace Shortcut", {"parent": ws_name})
    shortcuts_data = [
        ("Nouvelle Permission",    "DocType", "Permission Sortie Stagiaire", "", "#4CAF50", 1),
        ("Nouveau Bilan",          "DocType", "Bilan Fin de Stage",           "", "#2196F3", 2),
        ("Voir Présences Stg",     "DocType", "Attendance",                   "", "#009688", 3),
        ("Form. Permission",       "URL",     "",  "/permission-sortie-stagiaire", "#FF9800", 4),
    ]
    for label, stype, link_to, url, color, idx in shortcuts_data:
        frappe.db.sql(
            "INSERT INTO `tabWorkspace Shortcut` "
            "(name, parent, parenttype, parentfield, idx, label, type, link_to, url, color) "
            "VALUES (%s, %s, 'Workspace', 'shortcuts', %s, %s, %s, %s, %s, %s)",
            (frappe.generate_hash(length=10), ws_name, idx, label, stype, link_to, url, color)
        )
    print(f"  [OK] {len(shortcuts_data)} shortcuts insérés")

    # 4. Vérifier/mettre à jour le Workspace Sidebar Item pour KYA Stagiaires
    # S'assurer que le workspace "Espace Stagiaires" est le premier item
    kya_sidebar = frappe.db.get_value("Workspace Sidebar",
        {"title": "KYA Stagiaires"}, "name")
    if kya_sidebar:
        items = frappe.db.sql(
            "SELECT label, link_type, link_to, idx FROM `tabWorkspace Sidebar Item` "
            "WHERE parent=%s ORDER BY idx",
            kya_sidebar, as_dict=True
        )
        print(f"\n  Workspace Sidebar 'KYA Stagiaires' items ({len(items)}):")
        for it in items:
            print(f"    [{it.idx}] {it.label} ({it.link_type}) → {it.link_to}")
    else:
        print("  [WARN] Workspace Sidebar 'KYA Stagiaires' non trouvé")

    # 5. Commit
    frappe.db.commit()
    frappe.clear_cache()

    # Rapport
    n = frappe.db.count("Workspace Link", {"parent": ws_name})
    ns = frappe.db.count("Workspace Shortcut", {"parent": ws_name})
    content = frappe.db.get_value("Workspace", ws_name, "content") or "[]"
    nc_cnt = sum(1 for c in json.loads(content) if c.get("type") == "number_card")
    print(f"\n=== RÉSULTAT FINAL ===")
    print(f"  {ws_name}: links={n}, shortcuts={ns}, number_cards={nc_cnt}")
    print("\n[DONE]")

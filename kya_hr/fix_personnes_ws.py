"""
fix_personnes_ws.py — Fix workspace "Personnes" (HRMS People) 0 links
Copie les liens depuis le Workspace Sidebar "People" vers tabWorkspace Link
et met à jour le content JSON pour avoir une page d'accueil HR fonctionnelle.
"""
import frappe
import json


def execute():
    print("=== FIX WORKSPACE PERSONNES (HRMS) ===\n")

    # 1. Identifier le workspace HRMS cible
    hrms_ws_candidates = ["Personnes", "People", "HR", "Ressources Humaines"]
    target_ws = None
    for cand in hrms_ws_candidates:
        if frappe.db.exists("Workspace", cand):
            n = frappe.db.count("Workspace Link", {"parent": cand})
            print(f"  [{cand}] links={n}")
            if n == 0 and target_ws is None:
                target_ws = cand

    if not target_ws:
        print("  Aucun workspace HRMS vide trouvé.")
    else:
        print(f"\n  → Cible: '{target_ws}' (0 links)")

    # 2. Récupérer les items du Workspace Sidebar "People" (la vraie source)
    people_sidebar = frappe.db.get_value("Workspace Sidebar",
        {"title": "People"}, "name")
    leaves_sidebar = frappe.db.get_value("Workspace Sidebar",
        {"title": "Leaves"}, "name")

    print(f"\n  People sidebar: {people_sidebar}")
    print(f"  Leaves sidebar: {leaves_sidebar}")

    if people_sidebar:
        items = frappe.db.sql(
            "SELECT label, link_type, link_to, url, icon, indent, type "
            "FROM `tabWorkspace Sidebar Item` WHERE parent=%s ORDER BY idx",
            people_sidebar, as_dict=True
        )
        print(f"  People sidebar items ({len(items)}):")
        for it in items:
            print(f"    [{it.label}] {it.link_type} → {it.link_to}")

    # 3. Remplir tabWorkspace Link pour "Personnes" depuis les People sidebar items
    if target_ws and people_sidebar:
        items = frappe.db.sql(
            "SELECT label, link_type, link_to, url, icon, indent, type "
            "FROM `tabWorkspace Sidebar Item` WHERE parent=%s ORDER BY idx",
            people_sidebar, as_dict=True
        )

        frappe.db.delete("Workspace Link", {"parent": target_ws})
        idx = 1
        for it in items:
            if it.type == "separator" or not it.label:
                # Transformer les séparateurs en Card Break
                frappe.db.sql(
                    "INSERT INTO `tabWorkspace Link` "
                    "(name, parent, parenttype, parentfield, idx, type, label) "
                    "VALUES (%s, %s, 'Workspace', 'links', %s, 'Card Break', %s)",
                    (frappe.generate_hash(length=10), target_ws, idx, it.label or "—")
                )
            else:
                frappe.db.sql(
                    "INSERT INTO `tabWorkspace Link` "
                    "(name, parent, parenttype, parentfield, idx, type, label, link_to, link_type, hidden) "
                    "VALUES (%s, %s, 'Workspace', 'links', %s, 'Link', %s, %s, %s, 0)",
                    (frappe.generate_hash(length=10), target_ws,
                     idx, it.label, it.link_to or "", it.link_type or "DocType")
                )
            idx += 1

        print(f"\n  [OK] {idx-1} items copiés dans '{target_ws}' tabWorkspace Link")

    # 4. Remplir le content JSON pour une home page HR propre
    if target_ws:
        # Shortcuts HR essentiels
        hr_shortcuts = [
            {"label": "Employés",     "type": "DocType", "link_to": "Employee",          "color": "#1565C0"},
            {"label": "Départements", "type": "DocType", "link_to": "Department",         "color": "#283593"},
            {"label": "Congés",       "type": "DocType", "link_to": "Leave Application",  "color": "#00838F"},
            {"label": "Assiduité",    "type": "DocType", "link_to": "Attendance",          "color": "#2E7D32"},
        ]
        frappe.db.delete("Workspace Shortcut", {"parent": target_ws})
        for i, sc in enumerate(hr_shortcuts):
            frappe.db.sql(
                "INSERT INTO `tabWorkspace Shortcut` "
                "(name, parent, parenttype, parentfield, idx, label, type, link_to, color) "
                "VALUES (%s, %s, 'Workspace', 'shortcuts', %s, %s, %s, %s, %s)",
                (frappe.generate_hash(length=10), target_ws, i+1,
                 sc["label"], sc["type"], sc["link_to"], sc["color"])
            )

        frappe.db.set_value("Workspace", target_ws, "content", json.dumps([
            {"id": "h1", "type": "header",
             "data": {"text": "<div>👥 Ressources Humaines — Personnes</div>",
                      "level": 3, "col": 12}},
            {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Employés",     "col": 3}},
            {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Départements", "col": 3}},
            {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "Congés",       "col": 3}},
            {"id": "s4", "type": "shortcut", "data": {"shortcut_name": "Assiduité",    "col": 3}},
        ], ensure_ascii=False), update_modified=True)
        print(f"  [OK] Content JSON mis à jour pour '{target_ws}'")

    # 5. Vérifier "Congés" workspace (peut être "Leaves and Holiday" ou "Congés")
    print("\n=== VÉRIFICATION WORKSPACES CONGÉS ===")
    for ws_cand in ["Congés", "Leaves and Holiday", "Leave"]:
        if frappe.db.exists("Workspace", ws_cand):
            n = frappe.db.count("Workspace Link", {"parent": ws_cand})
            print(f"  [{ws_cand}] links={n}")

    # 6. Lister tous les workspaces HR/HRMS avec leur nb de links
    print("\n=== TOUS LES WORKSPACES HRMS ===")
    ws_list = frappe.db.sql(
        "SELECT name, module FROM `tabWorkspace` "
        "WHERE module IN ('HR','Leave','Payroll','HRMS') "
        "OR name IN ('Personnes','Ressources Humaines','Congés','Leaves','Payroll',"
        "             'Recruitment','Expenses','Performance','Shift & Attendance',"
        "             'Tax & Benefits','Tenure','People','Leaves and Holiday')",
        as_dict=True
    )
    for ws in ws_list:
        n_links = frappe.db.count("Workspace Link", {"parent": ws.name})
        n_sc = frappe.db.count("Workspace Shortcut", {"parent": ws.name})
        print(f"  [{ws.name}] module={ws.module} links={n_links} shortcuts={n_sc}")

    frappe.db.commit()
    frappe.clear_cache()
    print("\n[DONE] Commit + cache bust effectués")

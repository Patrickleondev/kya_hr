"""
create_kya_stagiaires_ws.py — Créer le workspace KYA Stagiaires dans tabWorkspace
Le workspace Sidebar existait déjà (5 items) mais la home page n'avait pas de record tabWorkspace.
Ce script crée le record et y ajoute les Number Cards de présences.
"""
import frappe
import json


def execute():
    print("=== CRÉATION WORKSPACE KYA STAGIAIRES ===\n")

    ws_name = "KYA Stagiaires"

    # 1. Vérifier si le workspace existe déjà
    if frappe.db.exists("Workspace", ws_name):
        print(f"  Le workspace '{ws_name}' existe déjà.")
        n = frappe.db.count("Workspace Link", {"parent": ws_name})
        ns = frappe.db.count("Workspace Shortcut", {"parent": ws_name})
        content = frappe.db.get_value("Workspace", ws_name, "content") or "[]"
        nc_cnt = sum(1 for c in json.loads(content) if c.get("type") == "number_card")
        print(f"  links={n}, shortcuts={ns}, number_cards={nc_cnt}")

        # Si pas de number cards, mettre à jour
        if nc_cnt == 0:
            print("  → Mise à jour du content avec Number Cards...")
            _update_ws_content(ws_name)
        return

    # 2. Créer le workspace
    print(f"  Création du workspace '{ws_name}'...")

    # Récupérer le module KYA HR
    module_name = "KYA HR"

    ws_doc = frappe.new_doc("Workspace")
    ws_doc.name = ws_name
    ws_doc.title = ws_name
    ws_doc.module = module_name
    ws_doc.icon = "users"
    ws_doc.is_hidden = 0
    ws_doc.hide_custom = 0
    ws_doc.type = "Module"

    # Links (sidebar navigation du workspace)
    links = [
        {"type": "Card Break", "label": "🎓 Gestion Stagiaires"},
        {"type": "Link", "label": "Espace Stagiaires",
         "link_to": "Espace Stagiaires", "link_type": "Workspace", "onboard": 1},
        {"type": "Link", "label": "Autorisations",
         "link_to": "Permission Sortie Stagiaire", "link_type": "DocType"},
        {"type": "Link", "label": "Bilan",
         "link_to": "Bilan Fin de Stage", "link_type": "DocType"},
        {"type": "Link", "label": "Stagiaires",
         "link_to": "Employee", "link_type": "DocType"},
        {"type": "Link", "label": "Présences",
         "link_to": "Attendance", "link_type": "DocType"},
        {"type": "Card Break", "label": "📊 Rapports"},
        {"type": "Link", "label": "Rapport Présences",
         "link_to": "Rapport Présence Stagiaires", "link_type": "Report",
         "dependencies": "Attendance", "report_ref_doctype": "Attendance"},
        {"type": "Link", "label": "Tableau de Bord",
         "link_to": "Tableau de Bord Stagiaires", "link_type": "Report",
         "dependencies": "Employee", "report_ref_doctype": "Employee"},
    ]
    for i, lk in enumerate(links):
        ws_doc.append("links", {
            "idx": i + 1,
            "type": lk.get("type", "Link"),
            "label": lk.get("label", ""),
            "link_to": lk.get("link_to") or None,
            "link_type": lk.get("link_type") or None,
            "hidden": 0,
            "onboard": lk.get("onboard", 0),
            "dependencies": lk.get("dependencies") or None,
            "report_ref_doctype": lk.get("report_ref_doctype") or None,
        })

    # Shortcuts
    shortcuts = [
        {"label": "Nouvelle Permission", "type": "DocType",
         "link_to": "Permission Sortie Stagiaire", "color": "#4CAF50"},
        {"label": "Nouveau Bilan", "type": "DocType",
         "link_to": "Bilan Fin de Stage", "color": "#2196F3"},
        {"label": "Voir Présences Stg", "type": "DocType",
         "link_to": "Attendance", "color": "#009688"},
        {"label": "Form. Permission", "type": "URL",
         "url": "/permission-sortie-stagiaire", "color": "#FF9800"},
    ]
    for i, sc in enumerate(shortcuts):
        ws_doc.append("shortcuts", {
            "idx": i + 1,
            "label": sc["label"],
            "type": sc.get("type", "DocType"),
            "link_to": sc.get("link_to", ""),
            "url": sc.get("url", ""),
            "color": sc.get("color", ""),
        })

    try:
        ws_doc.insert(ignore_permissions=True)
        print(f"  [OK] Workspace '{ws_name}' créé avec {len(links)} links, {len(shortcuts)} shortcuts")
    except Exception as e:
        print(f"  [ERR] Insertion échouée: {e}")
        # Essayer avec db.insert direct
        frappe.db.sql(
            "INSERT INTO `tabWorkspace` (name, title, module, icon, is_hidden, creation, modified, "
            "modified_by, owner, docstatus) VALUES (%s, %s, %s, %s, 0, NOW(), NOW(), 'Administrator', "
            "'Administrator', 0)",
            (ws_name, ws_name, module_name, "users")
        )
        print(f"  [OK] Workspace '{ws_name}' créé via SQL direct")

    # 3. Ajouter le content avec Number Cards
    _update_ws_content(ws_name)

    frappe.db.commit()
    frappe.clear_cache()

    # Rapport
    print("\n=== RAPPORT FINAL ===")
    if frappe.db.exists("Workspace", ws_name):
        n = frappe.db.count("Workspace Link", {"parent": ws_name})
        ns = frappe.db.count("Workspace Shortcut", {"parent": ws_name})
        content = frappe.db.get_value("Workspace", ws_name, "content") or "[]"
        nc_cnt = sum(1 for c in json.loads(content) if c.get("type") == "number_card")
        print(f"  {ws_name}: links={n}, shortcuts={ns}, number_cards={nc_cnt}")

    print("\n[DONE] Commit effectué.")


def _update_ws_content(ws_name):
    """Injecte les Number Cards présences dans le content JSON du workspace."""
    import frappe as f

    today = f.utils.today()
    week_start = f.utils.add_days(today, -7)
    month_start = f.utils.get_first_day(today)

    # Créer les Number Cards si elles n'existent pas
    nc_defs = [
        ("Stagiaires Actifs KYA", "Stagiaires Actifs", "Employee",
         "#4CAF50", [["Employee", "custom_statut_stage", "=", "Actif"]]),
        ("Presences Aujourd'hui", "Présences Aujourd'hui", "Attendance",
         "#2196F3", [["Attendance", "attendance_date", "=", today],
                     ["Attendance", "status", "=", "Present"]]),
        ("Absences Cette Semaine", "Absences (7j)", "Attendance",
         "#F44336", [["Attendance", "attendance_date", "between", [week_start, today]],
                     ["Attendance", "status", "=", "Absent"]]),
        ("Presences Ce Mois", "Présences Ce Mois", "Attendance",
         "#009688", [["Attendance", "attendance_date", ">=", str(month_start)],
                     ["Attendance", "status", "=", "Present"]]),
    ]

    for nc_name, nc_label, nc_dt, nc_color, nc_filters in nc_defs:
        if not f.db.exists("Number Card", nc_name):
            nc = f.new_doc("Number Card")
            nc.name = nc_name
            nc.label = nc_label
            nc.document_type = nc_dt
            nc.function = "Count"
            nc.aggregate_function_based_on = "name"
            nc.color = nc_color
            nc.filters_json = json.dumps(nc_filters)
            nc.is_public = 1
            nc.insert(ignore_permissions=True)
            print(f"  [NC] Créé: {nc_name}")
        else:
            print(f"  [NC] Existe: {nc_name}")

    content = json.dumps([
        {"id": "h1", "type": "header",
         "data": {"text": "<div class='ellipsis'>🎓 KYA Stagiaires — Tableau de Bord</div>",
                  "level": 3, "col": 12}},
        {"id": "s1", "type": "shortcut",
         "data": {"shortcut_name": "Nouvelle Permission", "col": 3}},
        {"id": "s2", "type": "shortcut",
         "data": {"shortcut_name": "Nouveau Bilan", "col": 3}},
        {"id": "s3", "type": "shortcut",
         "data": {"shortcut_name": "Voir Présences Stg", "col": 3}},
        {"id": "s4", "type": "shortcut",
         "data": {"shortcut_name": "Form. Permission", "col": 3}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        {"id": "h2", "type": "header",
         "data": {"text": "📊 Présences & Activité", "level": 4, "col": 12}},
        {"id": "nc1", "type": "number_card",
         "data": {"number_card_name": "Stagiaires Actifs KYA", "col": 3}},
        {"id": "nc2", "type": "number_card",
         "data": {"number_card_name": "Presences Aujourd'hui", "col": 3}},
        {"id": "nc3", "type": "number_card",
         "data": {"number_card_name": "Absences Cette Semaine", "col": 3}},
        {"id": "nc4", "type": "number_card",
         "data": {"number_card_name": "Presences Ce Mois", "col": 3}},
    ], ensure_ascii=False)

    f.db.set_value("Workspace", ws_name, "content", content, update_modified=True)
    print(f"  [OK] Content JSON mis à jour pour '{ws_name}'")

"""
KYA — Fix all workspace issues in one pass (SQL-only, pas de ws.save).
bench --site frontend execute kya_hr.fix_all_workspaces.execute
"""
import frappe
import json


def execute():
    print("=== KYA FIX ALL WORKSPACES ===")
    fix_card_break_links()
    fix_kya_services_portail()
    fix_kya_services_content()
    fix_espace_employes()
    fix_gestion_equipe()
    fix_espace_stagiaires()
    fix_website_settings_appname()
    fix_corrupted_statut_values()
    fix_webform_client_scripts()
    fix_kya_forms_dashboard()
    fix_kya_services_number_cards()
    fix_stagiaires_number_cards()
    fix_kya_services_total_reponses()
    frappe.db.commit()
    frappe.clear_cache()
    print("=== ALL FIXES APPLIED + CACHE CLEARED ===")


def fix_card_break_links():
    """Clean Card Break entries with link_to='None' (string) that cause 'DocType s introuvable'."""
    frappe.db.sql("""
        UPDATE `tabWorkspace Link`
        SET link_to = '', link_type = ''
        WHERE type = 'Card Break' AND (link_to = 'None' OR link_to IS NULL)
    """)
    # Also clean shortcuts with url='None' (string)
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET url = ''
        WHERE url = 'None'
    """)
    print("  [Card Break] Cleaned link_to='None' entries ✓")


def fix_kya_services_portail():
    """Fix 'Portail Enquête' shortcut — NULL link_to causes 'DocType introuvable'."""
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET url = '/kya-survey', link_to = ''
        WHERE parent = 'KYA Services' AND label = 'Portail Enquête'
    """)
    print("  [KYA Services] Fixed 'Portail Enquête' → url=/kya-survey ✓")


def fix_kya_services_content():
    """Rebuild KYA Services workspace content JSON to avoid broken blocks."""
    content = [
        {"id": "hdr_forms", "type": "header", "data": {"text": "📝 Formulaires & Enquêtes", "col": 12}},
        {"id": "sc_forms", "type": "shortcut", "data": {"shortcut_name": "Formulaires", "col": 4}},
        {"id": "sc_resp", "type": "shortcut", "data": {"shortcut_name": "Réponses", "col": 4}},
        {"id": "sc_portail", "type": "shortcut", "data": {"shortcut_name": "Portail Enquête", "col": 4}},
        {"id": "hdr_evals", "type": "header", "data": {"text": "📋 Évaluations", "col": 12}},
        {"id": "sc_evals", "type": "shortcut", "data": {"shortcut_name": "Évaluations", "col": 4}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        {"id": "hdr_ind", "type": "header", "data": {"text": "📊 Indicateurs", "col": 12}},
        {"id": "nc1", "type": "number_card", "data": {"number_card_name": "Formulaires Actifs", "col": 6}},
        {"id": "nc2", "type": "number_card", "data": {"number_card_name": "Total Réponses", "col": 6}},
    ]
    frappe.db.sql(
        "UPDATE tabWorkspace SET content = %s WHERE name = 'KYA Services'",
        (json.dumps(content),)
    )
    print("  [KYA Services] Content JSON rebuilt ✓")


def fix_espace_employes():
    """Fix NULL link_to for URL shortcuts + add missing ones + rebuild content."""
    # Fix URL shortcuts with NULL link_to
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET url = '/permission-sortie-employe/new', link_to = ''
        WHERE parent = 'Espace Employes' AND label = 'Demander une Permission'
          AND (link_to IS NULL OR link_to = '')
    """)
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET url = '/app/employee', link_to = ''
        WHERE parent = 'Espace Employes' AND label = 'Tableau de Bord Employés'
          AND (link_to IS NULL OR link_to = '')
    """)
    # Fix Planning Congé → Leave Application si DocType inexistant
    if not frappe.db.exists("DocType", "Planning Conge"):
        frappe.db.sql("""
            UPDATE `tabWorkspace Shortcut`
            SET link_to = 'Leave Application'
            WHERE parent = 'Espace Employes' AND label = 'Planning Congé'
              AND link_to = 'Planning Conge'
        """)
        print("  [Espace Employes] Fixed 'Planning Congé' → Leave Application")

    # Ajouter les shortcuts manquants via INSERT direct
    existing = set(r[0] for r in frappe.db.sql(
        "SELECT label FROM `tabWorkspace Shortcut` WHERE parent='Espace Employes'"
    ))

    to_add = []
    if "Demande d'Achat" not in existing:
        to_add.append(("Demande d'Achat", "URL", "/demande-achat/new", "#1a5276", "file"))
    if "PV Sortie Matériel" not in existing:
        to_add.append(("PV Sortie Matériel", "URL", "/pv-sortie-materiel/new", "#e67e22", "file"))

    for label, stype, url, color, icon in to_add:
        name = frappe.generate_hash(length=10)
        frappe.db.sql("""
            INSERT INTO `tabWorkspace Shortcut`
              (name, parent, parenttype, parentfield, label, type, url, color, icon, idx)
            VALUES (%s, 'Espace Employes', 'Workspace', 'shortcuts', %s, %s, %s, %s, %s,
              COALESCE((SELECT MAX(idx) FROM `tabWorkspace Shortcut` t2 WHERE t2.parent='Espace Employes'),0)+1)
        """, (name, label, stype, url, color, icon))
        print(f"  [Espace Employes] Added '{label}' ✓")

    # Rebuild content JSON
    shortcuts = frappe.db.sql(
        "SELECT label FROM `tabWorkspace Shortcut` WHERE parent='Espace Employes' ORDER BY idx",
        as_dict=True
    )
    content = [{"id": "hero", "type": "header", "data": {
        "text": "<div class='ellipsis' title='Espace Employés'>👤 Espace Employés KYA</div>",
        "level": 3, "col": 12
    }}]
    for i, s in enumerate(shortcuts):
        content.append({"id": f"s{i+1}", "type": "shortcut",
                        "data": {"shortcut_name": s.label, "col": 3}})
    content.append({"id": "spacer1", "type": "spacer", "data": {"col": 12}})
    frappe.db.set_value("Workspace", "Espace Employes", "content", json.dumps(content))
    print(f"  [Espace Employes] Rebuilt content ({len(shortcuts)} shortcuts) ✓")


def fix_gestion_equipe():
    """Remove unsupported 'card'/'link' blocks from Gestion Équipe content."""
    new_content = [
        {"id": "shortcut-1", "type": "shortcut",
         "data": {"shortcut_name": "Plans Trimestriels", "col": 4}},
        {"id": "shortcut-2", "type": "shortcut",
         "data": {"shortcut_name": "Tâches d'Équipe", "col": 4}},
        {"id": "shortcut-3", "type": "shortcut",
         "data": {"shortcut_name": "Tableau de Bord", "col": 4}},
        {"id": "spacer-1", "type": "spacer", "data": {"col": 12}},
        {"id": "header-1", "type": "header",
         "data": {"text": "📋 Gestion des Tâches", "col": 12, "level": 4}},
        {"id": "spacer-2", "type": "spacer", "data": {"col": 12}},
    ]
    frappe.db.set_value("Workspace", "Gestion Équipe", "content", json.dumps(new_content))
    print("  [Gestion Équipe] Removed card/link blocks, rebuilt content ✓")


def fix_espace_stagiaires():
    """Ensure Espace Stagiaires is visible, public, with correct icon and content."""
    frappe.db.sql("""
        UPDATE tabWorkspace
        SET public = 1, is_hidden = 0, icon = 'graduation-cap'
        WHERE name = 'Espace Stagiaires'
    """)
    # Rebuild content with 3 Number Cards + shortcuts
    content = [
        {"type": "header", "data": {"text": "📊 Tableau de Bord", "col": 12}},
        {"type": "number_card", "data": {"number_card_name": "Stagiaires Actifs", "col": 4}},
        {"type": "number_card", "data": {"number_card_name": "Permissions Stagiaires en Attente", "col": 4}},
        {"type": "number_card", "data": {"number_card_name": "Bilans de Stage Soumis", "col": 4}},
        {"type": "header", "data": {"text": "🔗 Accès Rapide", "col": 12}},
        {"type": "shortcut", "data": {"shortcut_name": "Stagiaires", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Permissions", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Bilan", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Demander une Permission", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Bilan de Stage ↗", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Tableau de Bord", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Mon Espace", "col": 4}},
    ]
    frappe.db.set_value("Workspace", "Espace Stagiaires", "content", json.dumps(content))
    print("  [Espace Stagiaires] Visible + public + icon + content rebuilt ✓")


def fix_website_settings_appname():
    """Force Website Settings.app_name = KYA-Energy Group (was 'Frappe')."""
    frappe.db.sql("""
        UPDATE tabSingles
        SET value = 'KYA-Energy Group'
        WHERE doctype = 'Website Settings' AND field = 'app_name'
    """)
    count = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    if not count:
        # Row might not exist — insert it
        frappe.db.sql("""
            INSERT INTO tabSingles (doctype, field, value)
            VALUES ('Website Settings', 'app_name', 'KYA-Energy Group')
            ON DUPLICATE KEY UPDATE value = 'KYA-Energy Group'
        """)
    print("  [Website Settings] app_name → KYA-Energy Group ✓")


def fix_corrupted_statut_values():
    """Correct statut values that may be corrupted/outdated in DB."""
    # KYA Form: valid options are Brouillon, Actif, Fermé
    frappe.db.sql("""
        UPDATE `tabKYA Form`
        SET statut = 'Actif'
        WHERE statut NOT IN ('Brouillon', 'Actif', 'Ferm\u00e9')
          AND (statut LIKE '%tiv%' OR statut LIKE '%ctif%' OR statut LIKE '%Activ%')
    """)
    # KYA Evaluation: valid options are Brouillon, Soumis, Validé
    frappe.db.sql("""
        UPDATE `tabKYA Evaluation`
        SET statut = 'Brouillon'
        WHERE statut NOT IN ('Brouillon', 'Soumis', 'Valid\u00e9')
    """)
    print("  [Statut] Valeurs corrompues corrigées ✓")

def fix_webform_client_scripts():
    """Push client_script from JSON files to DB (bench migrate ignores existing records)."""
    import os
    base = frappe.get_app_path("kya_hr", "web_form")
    updated = 0
    for wf_dir in ["permission_sortie_employe", "permission_sortie_stagiaire"]:
        json_path = os.path.join(base, wf_dir, f"{wf_dir}.json")
        if not os.path.exists(json_path):
            continue
        import json as _json
        with open(json_path) as f:
            data = _json.load(f)
        cs = data.get("client_script", "")
        if not cs:
            continue
        name_in_db = wf_dir.replace("_", "-")
        if frappe.db.exists("Web Form", name_in_db):
            frappe.db.set_value("Web Form", name_in_db, "client_script", cs)
            updated += 1
    print(f"  [WebForms] {updated} client_scripts mis à jour ✓")


def fix_kya_forms_dashboard():
    """Create 'KYA Forms' dashboard with Number Cards if it doesn't exist."""
    chart_name = "KYA Forms - Formulaires par mois"
    if not frappe.db.exists("Dashboard Chart", chart_name):
        chart = frappe.new_doc("Dashboard Chart")
        chart.chart_name = chart_name
        chart.document_type = "KYA Form"
        chart.based_on = "creation"
        chart.type = "Bar"
        chart.time_interval = "Monthly"
        chart.timespan = "Last Year"
        chart.filters_json = "[]"
        chart.is_standard = 0
        chart.save(ignore_permissions=True)

    dash_name = "KYA Forms"
    if frappe.db.exists("Dashboard", dash_name):
        print("  [Dashboard] KYA Forms déjà présent ✓")
        return

    dash = frappe.new_doc("Dashboard")
    dash.dashboard_name = dash_name
    dash.is_standard = 0
    dash.append("charts", {"chart": chart_name, "width": "Full"})
    for card in ["Total Formulaires", "Formulaires Actifs", "Réponses Reçues", "Total Évaluations"]:
        if frappe.db.exists("Number Card", card):
            dash.append("cards", {"card": card})
    dash.save(ignore_permissions=True)
    print("  [Dashboard] KYA Forms créé ✓")


def fix_kya_services_number_cards():
    """Ensure KYA Services Portail Enquête shortcut has correct type=URL (not DocType)."""
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET type = 'URL', url = '/kya-survey', link_to = ''
        WHERE parent = 'KYA Services' AND label = 'Portail Enquête'
    """)
    # Also ensure the 'Réponses Reçues' Number Card filter key is valid
    frappe.db.sql("""
        UPDATE `tabNumber Card`
        SET filters_json = '[["KYA Form Response","soumis_le","is","set",false]]'
        WHERE name = 'Réponses Reçues' AND document_type = 'KYA Form Response'
    """)
    print("  [KYA Services] Portail Enquête type=URL ✓ · Réponses Reçues filter ✓")


def fix_stagiaires_number_cards():
    """Create Number Cards for Stagiaires module and inject into workspace content."""
    cards_to_create = [
        {
            "name": "Stagiaires Actifs",
            "label": "Stagiaires Actifs",
            "document_type": "Employee",
            "function": "Count",
            "filters_json": '[["Employee","employment_type","=","Stage",false],["Employee","status","=","Active",false]]',
            "color": "#009688",
        },
        {
            "name": "Permissions Stagiaires en Attente",
            "label": "Permissions en Attente",
            "document_type": "Permission Sortie Stagiaire",
            "function": "Count",
            "filters_json": '[["Permission Sortie Stagiaire","workflow_state","not in",["Approuvé","Rejeté"],false]]',
            "color": "#e67e22",
        },
        {
            "name": "Bilans de Stage Soumis",
            "label": "Bilans Soumis",
            "document_type": "Bilan Fin de Stage",
            "function": "Count",
            "filters_json": '[["Bilan Fin de Stage","docstatus","!=",0,false]]',
            "color": "#1a5276",
        },
    ]
    created = 0
    for card_data in cards_to_create:
        name = card_data.pop("name")
        if not frappe.db.exists("Number Card", name):
            try:
                card = frappe.new_doc("Number Card")
                card.name = name
                card.label = card_data.pop("label", name)
                card.is_standard = 0
                for k, v in card_data.items():
                    setattr(card, k, v)
                card.insert(ignore_permissions=True, ignore_if_duplicate=True)
                created += 1
            except Exception as e:
                print(f"  [Stagiaires NC] Skipped '{name}': {e}")
    print(f"  [Stagiaires] {created} Number Cards créés ✓")

    # Inject Number Cards into Espace Stagiaires workspace content (DB)
    ws_content_raw = frappe.db.get_value("Workspace", "Espace Stagiaires", "content") or "[]"
    ws_content = json.loads(ws_content_raw)
    has_nc = any(b.get("type") == "number_card" for b in ws_content)
    if not has_nc:
        ws_content.append({"id": "spacer_nc", "type": "spacer", "data": {"col": 12}})
        ws_content.append({"id": "nc_hdr", "type": "header",
                           "data": {"text": "<b>Indicateurs</b>", "level": 4, "col": 12}})
        nc_names = [
            "Stagiaires Actifs",
            "Permissions Stagiaires en Attente",
            "Bilans de Stage Soumis",
        ]
        for i, nm in enumerate(nc_names):
            if frappe.db.exists("Number Card", nm):
                ws_content.append({"id": f"snc{i}", "type": "number_card",
                                   "data": {"number_card_name": nm, "col": 4}})
        frappe.db.sql(
            "UPDATE tabWorkspace SET content = %s WHERE name = 'Espace Stagiaires'",
            (json.dumps(ws_content),)
        )
        print("  [Stagiaires] Workspace content mis à jour avec Number Cards ✓")


def fix_kya_services_total_reponses():
    """Ensure 'Total Réponses' and 'Formulaires Actifs' Number Cards exist."""
    nc_definitions = [
        {
            "name": "Formulaires Actifs",
            "label": "Formulaires Actifs",
            "document_type": "KYA Form",
            "function": "Count",
            "filters_json": '[["KYA Form","statut","=","Actif"]]',
            "color": "#4caf50",
        },
        {
            "name": "Total Réponses",
            "label": "Total Réponses",
            "document_type": "KYA Form Response",
            "function": "Count",
            "filters_json": "[]",
            "color": "#2196f3",
        },
    ]
    created = 0
    for nc_def in nc_definitions:
        name = nc_def["name"]
        if not frappe.db.exists("Number Card", name):
            try:
                card = frappe.new_doc("Number Card")
                for k, v in nc_def.items():
                    setattr(card, k, v)
                card.is_standard = 1
                card.module = "KYA HR"
                card.insert(ignore_permissions=True)
                created += 1
            except Exception as e:
                print(f"  [NC] Skipped '{name}': {e}")
    print(f"  [KYA Services NC] {created} Number Cards créés ✓")
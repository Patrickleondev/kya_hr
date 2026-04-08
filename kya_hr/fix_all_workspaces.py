"""
KYA — Fix all workspace issues in one pass (SQL-only, pas de ws.save).
bench --site frontend execute kya_hr.fix_all_workspaces.execute
"""
import frappe
import json


def _table_exists(table_name):
    """Check if a DB table exists (safe for cross-app references)."""
    try:
        frappe.db.sql(f"SELECT 1 FROM `{table_name}` LIMIT 1")
        return True
    except Exception:
        frappe.db.rollback()
        return False


def _kya_services_ready():
    """Check if kya_services tables exist (may not during fresh install)."""
    return _table_exists("tabKYA Form")


def execute():
    print("=== KYA FIX ALL WORKSPACES ===")
    fix_workspace_schema_nulls()
    fix_missing_workflow_states()
    fix_bad_doctype_shortcuts()
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
    fix_gestion_equipe_dashboard()
    fix_kya_services_number_cards()
    fix_stagiaires_number_cards()
    fix_kya_services_total_reponses()
    fix_navbar_logo()
    fix_splash_logo()
    fix_dashboard_shortcuts_to_stats_page()
    fix_workspace_number_card_links()
    fix_stagiaires_permissions()
    fix_kya_indicator_perms()
    frappe.db.commit()
    frappe.clear_cache()
    print("=== ALL FIXES APPLIED + CACHE CLEARED ===")


def fix_workspace_schema_nulls():
    """Fix NULL type/title in tabWorkspace — survives every migrate.

    Root causes:
    - Frappe core 'Welcome Workspace' JSON has no 'type' field → type=NULL in DB
    - Any kya_hr workspace JSON missing 'title' field → title=NULL in DB
    Both cause a silent JS crash that makes the workspace sidebar blank.
    """
    n_type = frappe.db.sql(
        "UPDATE `tabWorkspace` SET `type`='Workspace' WHERE `type` IS NULL OR `type`=''"
    )
    n_title = frappe.db.sql(
        "UPDATE `tabWorkspace` SET `title`=`label` WHERE `title` IS NULL OR `title`=''"
    )
    print(f"  [Workspace] Fixed type nulls and title nulls")


def fix_missing_workflow_states():
    """Create required workflow states if missing in DB."""
    required = [
        {"name": "En attente DAAF", "style": "Warning"},
    ]

    for state in required:
        if not frappe.db.exists("Workflow State", state["name"]):
            doc = frappe.get_doc({
                "doctype": "Workflow State",
                "name": state["name"],
                "workflow_state_name": state["name"],
                "style": state["style"],
            })
            doc.insert(ignore_permissions=True)
            print(f"  [Workflow State] Created '{state['name']}' ✓")


def fix_card_break_links():
    """Clean Card Break entries with link_to='None' and shortcuts with invalid DocType link_to."""
    # 1. Card Break rows with NULL/None link_to
    frappe.db.sql("""
        UPDATE `tabWorkspace Link`
        SET link_to = '', link_type = ''
        WHERE type = 'Card Break' AND (link_to = 'None' OR link_to IS NULL)
    """)
    # 2. Shortcuts with url='None' (string literal)
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET url = ''
        WHERE url = 'None'
    """)
    # 3. Shortcuts with type='DocType' but link_to is short (<3 chars), 'None', or non-existent
    #    This catches "DocType s introuvable" where link_to was corrupted to a single letter
    bad_shortcuts = frappe.db.sql("""
        SELECT name, parent, label, link_to
        FROM `tabWorkspace Shortcut`
        WHERE type = 'DocType'
          AND (
            link_to IS NULL
            OR link_to = ''
            OR link_to = 'None'
            OR LENGTH(link_to) < 3
            OR link_to NOT IN (SELECT name FROM tabDocType)
          )
    """, as_dict=True)
    for row in bad_shortcuts:
        frappe.db.sql("""
            UPDATE `tabWorkspace Shortcut`
            SET type = 'URL', url = '', link_to = ''
            WHERE name = %s
        """, (row["name"],))
        print(f"  [Card Break] Fixed bad shortcut '{row['parent']}/{row['label']}' (link_to={repr(row['link_to'])})")
    # 4. Workspace Links with type='DocType' and non-existent link_to
    frappe.db.sql("""
        UPDATE `tabWorkspace Link`
        SET link_to = '', type = 'Card Break'
        WHERE type = 'DocType'
          AND link_to IS NOT NULL AND link_to != '' AND link_to != 'None'
          AND link_to NOT IN (SELECT name FROM tabDocType)
    """)
    print("  [Card Break] Cleaned link_to='None' entries + bad DocType refs ✓")


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
        {"id": "sc_stats", "type": "shortcut", "data": {"shortcut_name": "📈 Statistiques", "col": 4}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        {"id": "hdr_ind", "type": "header", "data": {"text": "📊 Indicateurs", "col": 12}},
        {"id": "nc1", "type": "number_card", "data": {"number_card_name": "Formulaires Actifs", "col": 6}},
        {"id": "nc2", "type": "number_card", "data": {"number_card_name": "Total Réponses", "col": 6}},
    ]
    frappe.db.sql(
        "UPDATE tabWorkspace SET content = %s WHERE name = 'KYA Services'",
        (json.dumps(content),)
    )
    _upsert_workspace_shortcut(
        "KYA Services", "📈 Statistiques",
        "URL", "/kya-stats", "#1565c0", "bar-chart-2"
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
    if "Mon Espace" not in existing:
        to_add.append(("Mon Espace", "URL", "/mon-espace", "#2c3e50", "home"))
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
        {"id": "shortcut-4", "type": "shortcut",
         "data": {"shortcut_name": "📊 Dashboard Équipe", "col": 4}},
        {"id": "spacer-1", "type": "spacer", "data": {"col": 12}},
        {"id": "header-1", "type": "header",
         "data": {"text": "📋 Gestion des Tâches", "col": 12, "level": 4}},
        {"id": "spacer-2", "type": "spacer", "data": {"col": 12}},
    ]
    frappe.db.set_value("Workspace", "Gestion Équipe", "content", json.dumps(new_content))
    _upsert_workspace_shortcut(
        "Gestion Équipe", "📊 Dashboard Équipe",
        "URL", "/app/dashboard/Gestion-%C3%89quipe", "#673ab7", "bar-chart-2"
    )
    print("  [Gestion Équipe] Removed card/link blocks, rebuilt content ✓")


def fix_espace_stagiaires():
    """Ensure Espace Stagiaires is visible, public, with correct icon and content."""
    frappe.db.sql("""
        UPDATE tabWorkspace
        SET public = 1, is_hidden = 0, icon = 'graduation-cap'
        WHERE name = 'Espace Stagiaires'
    """)
    frappe.db.sql("""
        DELETE FROM `tabWorkspace Shortcut`
        WHERE parent = 'Espace Stagiaires' AND label = 'Mon Espace'
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
    if not _kya_services_ready():
        print("  [Statut] SKIP — kya_services tables not yet created")
        return
    # KYA Form: valid options are Brouillon, Actif, Fermé
    frappe.db.sql("""
        UPDATE `tabKYA Form`
        SET statut = 'Actif'
        WHERE statut NOT IN ('Brouillon', 'Actif', 'Ferm\u00e9')
          AND (statut LIKE '%tiv%' OR statut LIKE '%ctif%' OR statut LIKE '%Activ%')
    """)
    # KYA Evaluation: valid options are Brouillon, Soumis, Validé
    if _table_exists("tabKYA Evaluation"):
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
    """Rebuild 'KYA Forms' dashboard — toujours lie les charts + cards."""
    if not _kya_services_ready():
        print("  [Dashboard] SKIP KYA Forms — kya_services tables not yet created")
        return
    # ── Charts ────────────────────────────────────────────────────────────────
    charts_def = [
        ("KYA - Réponses par mois",  "KYA Form Response", "Line"),
        ("KYA - Formulaires créés",  "KYA Form",          "Bar"),
    ]
    chart_names = []
    for cname, doctype, ctype in charts_def:
        if not frappe.db.exists("Dashboard Chart", cname):
            chart = frappe.new_doc("Dashboard Chart")
            chart.chart_name    = cname
            chart.document_type = doctype
            chart.based_on      = "creation"
            chart.type          = ctype
            chart.time_interval = "Monthly"
            chart.timespan      = "Last Year"
            chart.filters_json  = "[]"
            chart.is_standard   = 0
            chart.save(ignore_permissions=True)
        chart_names.append(cname)

    # ── Number Cards ──────────────────────────────────────────────────────────
    nc_def = [
        ("Total Formulaires",  "KYA Form",          "[]",                                   "#607d8b"),
        ("Formulaires Actifs", "KYA Form",          '[["KYA Form","statut","=","Actif"]]',  "#4caf50"),
        ("Total Réponses KYA", "KYA Form Response", "[]",                                   "#2196f3"),
    ]
    card_names = []
    for nm, dt, filters, color in nc_def:
        if not frappe.db.exists("Number Card", nm):
            try:
                card = frappe.new_doc("Number Card")
                card.name          = nm
                card.label         = nm
                card.document_type = dt
                card.function      = "Count"
                card.filters_json  = filters
                card.color         = color
                card.is_standard   = 0
                card.insert(ignore_permissions=True)
            except Exception:
                pass
        card_names.append(nm)

    # ── Dashboard (get or create, toujours rebuild charts + cards) ────────────
    dash_name = "KYA Forms"
    if frappe.db.exists("Dashboard", dash_name):
        dash = frappe.get_doc("Dashboard", dash_name)
    else:
        dash = frappe.new_doc("Dashboard")
        dash.dashboard_name = dash_name
        dash.is_standard    = 0

    dash.charts = []
    for cname in chart_names:
        if frappe.db.exists("Dashboard Chart", cname):
            dash.append("charts", {"chart": cname, "width": "Full"})

    dash.cards = []
    for nm in card_names:
        if frappe.db.exists("Number Card", nm):
            dash.append("cards", {"card": nm})

    dash.save(ignore_permissions=True)
    print("  [Dashboard] KYA Forms → {} charts, {} cards ✓".format(
        len(dash.charts), len(dash.cards)))


def fix_kya_services_number_cards():
    """Ensure KYA Services Portail Enquête shortcut has correct type=URL (not DocType)."""
    if not _kya_services_ready():
        print("  [KYA Services NC] SKIP — kya_services tables not yet created")
        return
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
    if not _kya_services_ready():
        print("  [KYA Services NC] SKIP Total Réponses — kya_services tables not yet created")
        return
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


def fix_navbar_logo():
    """Set Navbar Settings app_logo to KYA logo."""
    frappe.db.sql("""
        UPDATE tabSingles
        SET value = '/assets/kya_hr/images/kya_logo.png'
        WHERE doctype = 'Navbar Settings' AND field = 'app_logo'
    """)
    count = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    if not count:
        frappe.db.sql("""
            INSERT INTO tabSingles (doctype, field, value)
            VALUES ('Navbar Settings', 'app_logo', '/assets/kya_hr/images/kya_logo.png')
            ON DUPLICATE KEY UPDATE value = '/assets/kya_hr/images/kya_logo.png'
        """)
    print("  [Navbar] app_logo → /assets/kya_hr/images/kya_logo.png ✓")


def fix_splash_logo():
    """Set Website Settings splash_image and app_logo to KYA logo."""
    for field in ("app_logo", "splash_image"):
        frappe.db.sql("""
            UPDATE tabSingles SET value = %s
            WHERE doctype = 'Website Settings' AND field = %s
        """, ("/assets/kya_hr/images/kya_logo.png", field))
        count = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
        if not count:
            frappe.db.sql("""
                INSERT INTO tabSingles (doctype, field, value)
                VALUES ('Website Settings', %s, %s)
                ON DUPLICATE KEY UPDATE value = %s
            """, (field, "/assets/kya_hr/images/kya_logo.png", "/assets/kya_hr/images/kya_logo.png"))
    print("  [Website Settings] app_logo + splash_image → KYA logo ✓")


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARDS STRATÉGIQUES
# ═══════════════════════════════════════════════════════════════════════════════

def _upsert_workspace_shortcut(workspace, label, type_, url, color, icon="bar-chart"):
    """Insert ou met à jour un Workspace Shortcut (type=URL)."""
    existing = frappe.db.get_value(
        "Workspace Shortcut", {"parent": workspace, "label": label}, "name"
    )
    if existing:
        frappe.db.sql("""
            UPDATE `tabWorkspace Shortcut`
            SET type = %s, url = %s, link_to = '', color = %s, icon = %s
            WHERE name = %s
        """, (type_, url or "", color, icon, existing))
    else:
        name = frappe.generate_hash(length=10)
        frappe.db.sql("""
            INSERT INTO `tabWorkspace Shortcut`
              (name, parent, parenttype, parentfield, label, type, url, link_to, color, icon, idx)
            VALUES (
              %s, %s, 'Workspace', 'shortcuts', %s, %s, %s, '', %s, %s,
              COALESCE((SELECT MAX(t2.idx) FROM `tabWorkspace Shortcut` t2 WHERE t2.parent = %s), 0) + 1
            )
        """, (name, workspace, label, type_, url or "", color, icon, workspace))


def fix_gestion_equipe_dashboard():
    """Créer ou mettre à jour le dashboard stratégique Gestion Équipe."""
    # Plan Trimestriel and KYA Evaluation are kya_hr DocTypes (may not exist on fresh install
    # if their JSON files have not been created yet — guard both tables)
    if not _table_exists("tabPlan Trimestriel") or not _table_exists("tabKYA Evaluation"):
        print("  [Dashboard] SKIP Gestion Équipe — Plan Trimestriel / KYA Evaluation tables not yet created")
        return
    # ── Charts ────────────────────────────────────────────────────────────────
    charts_def = [
        ("Gestion Équipe - Plans par mois",       "Plan Trimestriel", "Bar"),
        ("Gestion Équipe - Évaluations par mois", "KYA Evaluation",   "Line"),
    ]
    chart_names = []
    for cname, doctype, ctype in charts_def:
        if not frappe.db.exists("Dashboard Chart", cname):
            try:
                chart = frappe.new_doc("Dashboard Chart")
                chart.chart_name    = cname
                chart.document_type = doctype
                chart.based_on      = "creation"
                chart.type          = ctype
                chart.time_interval = "Monthly"
                chart.timespan      = "Last Year"
                chart.filters_json  = "[]"
                chart.is_standard   = 0
                chart.save(ignore_permissions=True)
            except Exception as e:
                print("  [Dashboard] Chart skip '{}': {}".format(cname, e))
                continue
        chart_names.append(cname)

    # ── Number Cards ──────────────────────────────────────────────────────────
    nc_def = [
        ("Plans En Cours",
         "Plan Trimestriel", '[["Plan Trimestriel","statut","=","En cours"]]', "#2196f3"),
        ("Tâches En Cours",
         "Tache Equipe",     '[["Tache Equipe","statut","=","En cours"]]',      "#ff9800"),
        ("Évaluations à Valider",
         "KYA Evaluation",   '[["KYA Evaluation","statut","=","Soumis"]]',      "#9c27b0"),
    ]
    card_names = []
    for nm, dt, filters, color in nc_def:
        if not frappe.db.exists("Number Card", nm):
            try:
                card = frappe.new_doc("Number Card")
                card.name          = nm
                card.label         = nm
                card.document_type = dt
                card.function      = "Count"
                card.filters_json  = filters
                card.color         = color
                card.is_standard   = 0
                card.insert(ignore_permissions=True)
            except Exception:
                pass
        card_names.append(nm)

    # ── Dashboard (get or create, toujours rebuild) ───────────────────────────
    dash_name = "Gestion Équipe"
    if frappe.db.exists("Dashboard", dash_name):
        dash = frappe.get_doc("Dashboard", dash_name)
    else:
        dash = frappe.new_doc("Dashboard")
        dash.dashboard_name = dash_name
        dash.is_standard    = 0

    dash.charts = []
    for cname in chart_names:
        if frappe.db.exists("Dashboard Chart", cname):
            dash.append("charts", {"chart": cname, "width": "Full"})

    dash.cards = []
    for nm in card_names:
        if frappe.db.exists("Number Card", nm):
            dash.append("cards", {"card": nm})

    dash.save(ignore_permissions=True)
    print("  [Dashboard] Gestion Équipe → {} charts, {} cards ✓".format(
        len(dash.charts), len(dash.cards)))

    # ── Shortcut dans workspace Gestion Équipe ────────────────────────────────
    _upsert_workspace_shortcut(
        "Gestion Équipe", "📊 Dashboard Équipe",
        "URL", "/app/dashboard/Gestion%20%C3%89quipe", "#673ab7", "bar-chart-2"
    )
    print("  [Dashboard] Shortcuts Gestion Équipe + KYA Services mis à jour ✓")


def fix_bad_doctype_shortcuts():
    """Désactiver / corriger les shortcuts qui pointent vers des DocTypes inexistants.
    Ces shortcuts causent l'erreur 'DocType s introuvable' quand on clique dessus."""
    # Lister tous les shortcuts de type 'DocType' dont le link_to n'existe pas
    bad = frappe.db.sql("""
        SELECT ws.name, ws.parent, ws.label, ws.link_to
        FROM `tabWorkspace Shortcut` ws
        WHERE ws.type = 'DocType'
          AND ws.link_to != ''
          AND ws.link_to IS NOT NULL
          AND ws.link_to NOT IN (SELECT name FROM tabDocType)
    """, as_dict=True)

    fixed = 0
    for row in bad:
        # Essayer de trouver le bon DocType par mapping connu
        mapping = {
            "KYA Form Response": "KYA Form Response",
            "Plan Trimestriel": "Plan Trimestriel",
            "Tache Equipe": "Tache Equipe",
            "KYA Evaluation": "KYA Evaluation",
        }
        new_link = mapping.get(row["link_to"])
        if new_link and frappe.db.exists("DocType", new_link):
            frappe.db.sql("UPDATE `tabWorkspace Shortcut` SET link_to = %s WHERE name = %s",
                          (new_link, row["name"]))
        else:
            # Convertir en URL vide pour éviter l'erreur (shortcut visible mais inactif)
            frappe.db.sql("""
                UPDATE `tabWorkspace Shortcut`
                SET type = 'URL', url = '', link_to = ''
                WHERE name = %s
            """, (row["name"],))
        fixed += 1
        print(f"  [Bad Shortcut] Fixed: {row['parent']} / {row['label']} → {row['link_to']}")

    # Aussi vérifier les Workspace Links (cards)
    bad_links = frappe.db.sql("""
        SELECT wl.name, wl.parent, wl.label, wl.link_to, wl.type
        FROM `tabWorkspace Link` wl
        WHERE wl.type = 'DocType'
          AND wl.link_to != ''
          AND wl.link_to IS NOT NULL
          AND wl.link_to NOT IN (SELECT name FROM tabDocType)
    """, as_dict=True)

    for row in bad_links:
        frappe.db.sql("""
            UPDATE `tabWorkspace Link`
            SET link_to = '', type = 'Card Break'
            WHERE name = %s
        """, (row["name"],))
        fixed += 1

    print(f"  [Bad DocType] {fixed} shortcuts/links corrigés ✓")


def fix_dashboard_shortcuts_to_stats_page():
    """Pointer les shortcuts vers /kya-stats (page de stats réelles).
    Ne crée qu'UN seul shortcut stats (📈 Statistiques), pas de doublon.
    """
    # Supprimer le doublon « 📊 Dashboard KYA » s'il existe
    frappe.db.sql("""
        DELETE FROM `tabWorkspace Shortcut`
        WHERE parent = 'KYA Services' AND label = '📊 Dashboard KYA'
    """)

    # Shortcut unique « 📈 Statistiques » dans KYA Services → /kya-stats
    _upsert_workspace_shortcut(
        "KYA Services", "📈 Statistiques",
        "URL", "/kya-stats", "#0077b6", "trending-up"
    )

    # Shortcut dans Gestion Équipe → page native Frappe dashboard
    _upsert_workspace_shortcut(
        "Gestion Équipe", "📊 Dashboard Équipe",
        "URL", "/app/dashboard/Gestion-%C3%89quipe", "#673ab7", "bar-chart-2"
    )

    print("  [Dashboard Shortcuts] /kya-stats et /app/dashboard mis à jour ✓")


def fix_workspace_number_card_links():
    """Lier les Workspace Number Card rows aux documents Number Card existants.
    Sans ce lien, les indicateurs apparaissent vides dans le workspace."""
    # KYA Services
    kya_nc_map = {
        "Total Formulaires": "Total Formulaires",
        "Formulaires Actifs": "Formulaires Actifs",
        "Réponses Reçues": "Réponses Reçues",
        "Total Évaluations": "Total Évaluations",
    }
    for label, card_name in kya_nc_map.items():
        if frappe.db.exists("Number Card", card_name):
            frappe.db.sql(
                "UPDATE `tabWorkspace Number Card` SET number_card_name=%s "
                "WHERE parent='KYA Services' AND label=%s AND (number_card_name IS NULL OR number_card_name='')",
                (card_name, label)
            )

    # Espace Stagiaires
    stag_nc_map = {
        "Stagiaires Actifs": "Stagiaires Actifs",
        "Permissions Stagiaires en Attente": "Permissions Stagiaires en Attente",
        "Bilans de Stage Soumis": "Bilans de Stage Soumis",
    }
    # Ensure rows exist (content JSON references them but child table may be empty)
    existing_labels = set(
        r[0] for r in frappe.db.sql(
            "SELECT label FROM `tabWorkspace Number Card` WHERE parent='Espace Stagiaires'"
        )
    )
    idx = len(existing_labels)
    for label, card_name in stag_nc_map.items():
        if not frappe.db.exists("Number Card", card_name):
            continue
        if label in existing_labels:
            frappe.db.sql(
                "UPDATE `tabWorkspace Number Card` SET number_card_name=%s "
                "WHERE parent='Espace Stagiaires' AND label=%s AND (number_card_name IS NULL OR number_card_name='')",
                (card_name, label)
            )
        else:
            idx += 1
            name = frappe.generate_hash(length=10)
            frappe.db.sql(
                "INSERT INTO `tabWorkspace Number Card` "
                "(name, parent, parenttype, parentfield, label, number_card_name, idx, "
                "creation, modified, modified_by, owner) "
                "VALUES (%s, 'Espace Stagiaires', 'Workspace', 'number_cards', %s, %s, %s, "
                "NOW(), NOW(), 'Administrator', 'Administrator')",
                (name, label, card_name, idx)
            )

    print("  [NC Links] Workspace Number Cards liés aux documents ✓")


def fix_stagiaires_permissions():
    """Ajouter les rôles Stagiaire + Responsable des Stagiaires aux DocTypes custom
    du module stagiaires (tabDocPerm — bench migrate ne les synchronise pas car custom=1)."""
    PERMS_TO_ADD = [
        ("Permission Sortie Stagiaire", [
            # (role, permlevel, read, write, create, submit, cancel, amend, if_owner)
            ("Stagiaire",                  0, 1, 1, 1, 0, 0, 0, 1),
            ("Responsable des Stagiaires", 0, 1, 1, 1, 1, 1, 0, 0),
        ]),
        ("Bilan Fin de Stage", [
            ("Stagiaire",                  0, 1, 1, 1, 1, 0, 0, 1),
            ("Responsable des Stagiaires", 0, 1, 1, 1, 1, 1, 0, 0),
        ]),
    ]
    inserted = 0
    for doctype, roles in PERMS_TO_ADD:
        if not frappe.db.exists("DocType", doctype):
            print(f"  [Permissions] DocType '{doctype}' introuvable, ignore")
            continue
        for (role, permlevel, read, write, create, submit, cancel, amend, if_owner) in roles:
            exists = frappe.db.sql(
                "SELECT name FROM `tabDocPerm` WHERE parent=%s AND role=%s AND permlevel=%s",
                (doctype, role, permlevel)
            )
            if exists:
                frappe.db.sql("""
                    UPDATE `tabDocPerm`
                    SET `read`=%s, `write`=%s, `create`=%s, `submit`=%s,
                        `cancel`=%s, `amend`=%s, `if_owner`=%s,
                        modified=NOW(), modified_by='Administrator'
                    WHERE parent=%s AND role=%s AND permlevel=%s
                """, (read, write, create, submit, cancel, amend, if_owner,
                      doctype, role, permlevel))
                print(f"  [Permissions] Mis a jour: {doctype} / {role}")
            else:
                name = frappe.generate_hash(length=10)
                frappe.db.sql("""
                    INSERT INTO `tabDocPerm`
                      (name, parent, parenttype, parentfield, permlevel, role,
                       `read`, `write`, `create`, `submit`, `cancel`, `amend`, `if_owner`,
                       idx, creation, modified, modified_by, owner)
                    VALUES (%s, %s, 'DocType', 'permissions', %s, %s,
                            %s, %s, %s, %s, %s, %s, %s,
                            COALESCE((SELECT MAX(t2.idx)+1 FROM `tabDocPerm` t2 WHERE t2.parent=%s), 1),
                            NOW(), NOW(), 'Administrator', 'Administrator')
                """, (name, doctype, permlevel, role,
                      read, write, create, submit, cancel, amend, if_owner,
                      doctype))
                inserted += 1
                print(f"  [Permissions] Insere: {doctype} / {role}")
    frappe.clear_cache(doctype="Permission Sortie Stagiaire")
    frappe.clear_cache(doctype="Bilan Fin de Stage")
    print(f"  [Permissions Stagiaires] {inserted} entrees ajoutees")


def fix_kya_indicator_perms():
    """Set role permissions on KYA Indicator, Plan Trimestriel, Tache Equipe, KYA Evaluation."""
    PERMS = [
        # (DocType, role, permlevel, read, write, create, delete, submit, cancel, amend, if_owner)
        ("KYA Indicator", "HR Manager",           0, 1, 1, 1, 1, 0, 0, 0, 0),
        ("KYA Indicator", "HR User",              0, 1, 0, 0, 0, 0, 0, 0, 0),
        ("KYA Indicator", "Chef d'Équipe",        0, 1, 0, 0, 0, 0, 0, 0, 0),
        ("KYA Indicator", "Accounts Manager",     0, 1, 0, 0, 0, 0, 0, 0, 0),
        ("KYA Indicator", "Purchase Manager",     0, 1, 0, 0, 0, 0, 0, 0, 0),
        ("Plan Trimestriel", "HR Manager",        0, 1, 1, 1, 1, 0, 0, 0, 0),
        ("Plan Trimestriel", "HR User",           0, 1, 1, 1, 0, 0, 0, 0, 0),
        ("Plan Trimestriel", "Chef d'Équipe",     0, 1, 1, 1, 0, 0, 0, 0, 0),
        ("Tache Equipe",     "HR Manager",        0, 1, 1, 1, 1, 0, 0, 0, 0),
        ("Tache Equipe",     "HR User",           0, 1, 1, 1, 0, 0, 0, 0, 0),
        ("Tache Equipe",     "Chef d'Équipe",     0, 1, 1, 1, 0, 0, 0, 0, 0),
        ("Tache Equipe",     "Employee",          0, 1, 1, 0, 0, 0, 0, 0, 1),
        ("KYA Evaluation",   "HR Manager",        0, 1, 1, 1, 1, 0, 0, 0, 0),
        ("KYA Evaluation",   "HR User",           0, 1, 0, 0, 0, 0, 0, 0, 0),
        ("KYA Evaluation",   "Chef d'Équipe",     0, 1, 1, 1, 0, 0, 0, 0, 0),
        ("KYA Evaluation",   "Employee",          0, 1, 1, 1, 0, 0, 0, 0, 1),
    ]
    inserted = 0
    for (doctype, role, permlevel, read, write, create, delete, submit, cancel, amend, if_owner) in PERMS:
        if not frappe.db.exists("DocType", doctype):
            continue
        exists = frappe.db.sql(
            "SELECT name FROM `tabDocPerm` WHERE parent=%s AND role=%s AND permlevel=%s",
            (doctype, role, permlevel)
        )
        if not exists:
            name = frappe.generate_hash(length=10)
            frappe.db.sql("""
                INSERT INTO `tabDocPerm`
                  (name, parent, parenttype, parentfield, permlevel, role,
                   `read`, `write`, `create`, `delete`, `submit`, `cancel`, `amend`, `if_owner`,
                   idx, creation, modified, modified_by, owner)
                VALUES (%s, %s, 'DocType', 'permissions', %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        COALESCE((SELECT MAX(t2.idx)+1 FROM `tabDocPerm` t2 WHERE t2.parent=%s), 1),
                        NOW(), NOW(), 'Administrator', 'Administrator')
            """, (name, doctype, permlevel, role,
                  read, write, create, delete, submit, cancel, amend, if_owner,
                  doctype))
            inserted += 1
    print(f"  [Indicator Perms] {inserted} permission entries added ✓")
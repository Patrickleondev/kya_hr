"""
KYA ΓÇö Fix all workspace issues in one pass (SQL-only, pas de ws.save).
bench --site frontend execute kya_hr.fix_all_workspaces.execute
"""
import frappe
import json


def execute():
    print("=== KYA FIX ALL WORKSPACES ===")
    fix_missing_workflow_states()
    fix_bad_doctype_shortcuts()
    fix_card_break_links()
    fix_kya_services_portail()
    fix_kya_services_content()
    fix_espace_employes()
    fix_gestion_equipe()
    fix_tableau_de_bord_shortcut()
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
    frappe.db.commit()
    frappe.clear_cache()
    print("=== ALL FIXES APPLIED + CACHE CLEARED ===")


def fix_missing_workflow_states():
    """Ensure every workflow state referenced by custom workflows exists in DB."""
    required_states = [
        ("Brouillon", ""),
        ("En attente Chef", "Warning"),
        ("En attente RH", "Warning"),
        ("En attente DAAF", "Warning"),
        ("En attente DG", "Warning"),
        ("En attente Audit", "Warning"),
        ("En attente Magasin", "Warning"),
        ("En attente Direction", "Warning"),
        ("En attente Resp. Stagiaires", "Warning"),
        ("Approuv├⌐", "Success"),
        ("Rejet├⌐", "Danger"),
    ]
    created = 0
    for state_name, style in required_states:
        if frappe.db.exists("Workflow State", state_name):
            continue
        doc = frappe.get_doc({
            "doctype": "Workflow State",
            "workflow_state_name": state_name,
            "style": style,
        })
        doc.insert(ignore_permissions=True)
        created += 1
    print(f"  [Workflow States] {created} ├⌐tat(s) cr├⌐├⌐(s) si manquants Γ£ô")


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
    print("  [Card Break] Cleaned link_to='None' entries + bad DocType refs Γ£ô")


def fix_kya_services_portail():
    """Fix 'Portail Enqu├¬te' shortcut ΓÇö NULL link_to causes 'DocType introuvable'."""
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET url = '/kya-survey', link_to = ''
        WHERE parent = 'KYA Services' AND label = 'Portail Enqu├¬te'
    """)
    print("  [KYA Services] Fixed 'Portail Enqu├¬te' ΓåÆ url=/kya-survey Γ£ô")


def fix_kya_services_content():
    """Rebuild KYA Services workspace content JSON to avoid broken blocks."""
    content = [
        {"id": "hdr_forms", "type": "header", "data": {"text": "≡ƒô¥ Formulaires & Enqu├¬tes", "col": 12}},
        {"id": "sc_forms", "type": "shortcut", "data": {"shortcut_name": "Formulaires", "col": 4}},
        {"id": "sc_resp", "type": "shortcut", "data": {"shortcut_name": "R├⌐ponses", "col": 4}},
        {"id": "sc_portail", "type": "shortcut", "data": {"shortcut_name": "Portail Enqu├¬te", "col": 4}},
        {"id": "hdr_evals", "type": "header", "data": {"text": "≡ƒôï ├ëvaluations", "col": 12}},
        {"id": "sc_evals", "type": "shortcut", "data": {"shortcut_name": "├ëvaluations", "col": 4}},
        {"id": "sc_stats", "type": "shortcut", "data": {"shortcut_name": "≡ƒôê Statistiques", "col": 4}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        {"id": "hdr_ind", "type": "header", "data": {"text": "≡ƒôè Indicateurs", "col": 12}},
        {"id": "nc1", "type": "number_card", "data": {"number_card_name": "Formulaires Actifs", "col": 6}},
        {"id": "nc2", "type": "number_card", "data": {"number_card_name": "Total R├⌐ponses", "col": 6}},
    ]
    frappe.db.sql(
        "UPDATE tabWorkspace SET content = %s WHERE name = 'KYA Services'",
        (json.dumps(content),)
    )
    _upsert_workspace_shortcut(
        "KYA Services", "≡ƒôê Statistiques",
        "URL", "/kya-stats", "#1565c0", "bar-chart-2"
    )
    print("  [KYA Services] Content JSON rebuilt Γ£ô")


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
        WHERE parent = 'Espace Employes' AND label = 'Tableau de Bord Employ├⌐s'
          AND (link_to IS NULL OR link_to = '')
    """)
    # Fix Planning Cong├⌐ ΓåÆ Leave Application si DocType inexistant
    if not frappe.db.exists("DocType", "Planning Conge"):
        frappe.db.sql("""
            UPDATE `tabWorkspace Shortcut`
            SET link_to = 'Leave Application'
            WHERE parent = 'Espace Employes' AND label = 'Planning Cong├⌐'
              AND link_to = 'Planning Conge'
        """)
        print("  [Espace Employes] Fixed 'Planning Cong├⌐' ΓåÆ Leave Application")

    # Ajouter les shortcuts manquants via INSERT direct
    existing = set(r[0] for r in frappe.db.sql(
        "SELECT label FROM `tabWorkspace Shortcut` WHERE parent='Espace Employes'"
    ))

    to_add = []
    if "Demande d'Achat" not in existing:
        to_add.append(("Demande d'Achat", "URL", "/demande-achat/new", "#1a5276", "file"))
    if "PV Sortie Mat├⌐riel" not in existing:
        to_add.append(("PV Sortie Mat├⌐riel", "URL", "/pv-sortie-materiel/new", "#e67e22", "file"))

    for label, stype, url, color, icon in to_add:
        name = frappe.generate_hash(length=10)
        frappe.db.sql("""
            INSERT INTO `tabWorkspace Shortcut`
              (name, parent, parenttype, parentfield, label, type, url, color, icon, idx)
            VALUES (%s, 'Espace Employes', 'Workspace', 'shortcuts', %s, %s, %s, %s, %s,
              COALESCE((SELECT MAX(idx) FROM `tabWorkspace Shortcut` t2 WHERE t2.parent='Espace Employes'),0)+1)
        """, (name, label, stype, url, color, icon))
        print(f"  [Espace Employes] Added '{label}' Γ£ô")

    # Rebuild content JSON
    shortcuts = frappe.db.sql(
        "SELECT label FROM `tabWorkspace Shortcut` WHERE parent='Espace Employes' ORDER BY idx",
        as_dict=True
    )
    content = [{"id": "hero", "type": "header", "data": {
        "text": "<div class='ellipsis' title='Espace Employ├⌐s'>≡ƒæñ Espace Employ├⌐s KYA</div>",
        "level": 3, "col": 12
    }}]
    for i, s in enumerate(shortcuts):
        content.append({"id": f"s{i+1}", "type": "shortcut",
                        "data": {"shortcut_name": s.label, "col": 3}})
    content.append({"id": "spacer1", "type": "spacer", "data": {"col": 12}})
    frappe.db.set_value("Workspace", "Espace Employes", "content", json.dumps(content))
    print(f"  [Espace Employes] Rebuilt content ({len(shortcuts)} shortcuts) Γ£ô")


def fix_gestion_equipe():
    """Remove unsupported 'card'/'link' blocks from Gestion ├ëquipe content."""
    new_content = [
        {"id": "shortcut-1", "type": "shortcut",
         "data": {"shortcut_name": "Plans Trimestriels", "col": 4}},
        {"id": "shortcut-2", "type": "shortcut",
         "data": {"shortcut_name": "T├óches d'├ëquipe", "col": 4}},
        {"id": "shortcut-3", "type": "shortcut",
         "data": {"shortcut_name": "Tableau de Bord", "col": 4}},
        {"id": "spacer-1", "type": "spacer", "data": {"col": 12}},
        {"id": "header-1", "type": "header",
         "data": {"text": "≡ƒôï Gestion des T├óches", "col": 12, "level": 4}},
        {"id": "spacer-2", "type": "spacer", "data": {"col": 12}},
    ]
    frappe.db.set_value("Workspace", "Gestion ├ëquipe", "content", json.dumps(new_content))
    # Nettoyer l'ancien shortcut "≡ƒôè Dashboard ├ëquipe" s'il existe encore
    frappe.db.sql("""
        DELETE FROM `tabWorkspace Shortcut`
        WHERE parent = 'Gestion \u00c9quipe'
          AND label = '\U0001f4ca Dashboard \u00c9quipe'
    """)
    print("  [Gestion ├ëquipe] Removed card/link blocks, rebuilt content Γ£ô")


def fix_espace_stagiaires():
    """Ensure Espace Stagiaires is visible, public, with correct icon and content."""
    frappe.db.sql("""
        UPDATE tabWorkspace
        SET public = 1, is_hidden = 0, icon = 'graduation-cap'
        WHERE name = 'Espace Stagiaires'
    """)
    # Rebuild content with 3 Number Cards + shortcuts
    content = [
        {"type": "header", "data": {"text": "≡ƒôè Tableau de Bord", "col": 12}},
        {"type": "number_card", "data": {"number_card_name": "Stagiaires Actifs", "col": 4}},
        {"type": "number_card", "data": {"number_card_name": "Permissions Stagiaires en Attente", "col": 4}},
        {"type": "number_card", "data": {"number_card_name": "Bilans de Stage Soumis", "col": 4}},
        {"type": "header", "data": {"text": "≡ƒöù Acc├¿s Rapide", "col": 12}},
        {"type": "shortcut", "data": {"shortcut_name": "Stagiaires", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Permissions", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Bilan", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Demander une Permission", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Bilan de Stage Γåù", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Tableau de Bord", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "Mon Espace", "col": 4}},
    ]
    frappe.db.set_value("Workspace", "Espace Stagiaires", "content", json.dumps(content))
    print("  [Espace Stagiaires] Visible + public + icon + content rebuilt Γ£ô")


def fix_website_settings_appname():
    """Force Website Settings.app_name = KYA-Energy Group (was 'Frappe')."""
    frappe.db.sql("""
        UPDATE tabSingles
        SET value = 'KYA-Energy Group'
        WHERE doctype = 'Website Settings' AND field = 'app_name'
    """)
    count = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    if not count:
        # Row might not exist ΓÇö insert it
        frappe.db.sql("""
            INSERT INTO tabSingles (doctype, field, value)
            VALUES ('Website Settings', 'app_name', 'KYA-Energy Group')
            ON DUPLICATE KEY UPDATE value = 'KYA-Energy Group'
        """)
    print("  [Website Settings] app_name ΓåÆ KYA-Energy Group Γ£ô")


def fix_corrupted_statut_values():
    """Correct statut values that may be corrupted/outdated in DB."""
    # KYA Form: valid options are Brouillon, Actif, Ferm├⌐
    frappe.db.sql("""
        UPDATE `tabKYA Form`
        SET statut = 'Actif'
        WHERE statut NOT IN ('Brouillon', 'Actif', 'Ferm\u00e9')
          AND (statut LIKE '%tiv%' OR statut LIKE '%ctif%' OR statut LIKE '%Activ%')
    """)
    # KYA Evaluation: valid options are Brouillon, Soumis, Valid├⌐
    frappe.db.sql("""
        UPDATE `tabKYA Evaluation`
        SET statut = 'Brouillon'
        WHERE statut NOT IN ('Brouillon', 'Soumis', 'Valid\u00e9')
    """)
    print("  [Statut] Valeurs corrompues corrig├⌐es Γ£ô")

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
    print(f"  [WebForms] {updated} client_scripts mis ├á jour Γ£ô")


def fix_kya_forms_dashboard():
    """Rebuild 'KYA Forms' dashboard ΓÇö toujours lie les charts + cards."""
    # ΓöÇΓöÇ Charts ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    charts_def = [
        ("KYA - R├⌐ponses par mois",  "KYA Form Response", "Line"),
        ("KYA - Formulaires cr├⌐├⌐s",  "KYA Form",          "Bar"),
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

    # ΓöÇΓöÇ Number Cards ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    nc_def = [
        ("Total Formulaires",  "KYA Form",          "[]",                                   "#607d8b"),
        ("Formulaires Actifs", "KYA Form",          '[["KYA Form","statut","=","Actif"]]',  "#4caf50"),
        ("Total R├⌐ponses KYA", "KYA Form Response", "[]",                                   "#2196f3"),
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

    # ΓöÇΓöÇ Dashboard (get or create, toujours rebuild charts + cards) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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
    print("  [Dashboard] KYA Forms ΓåÆ {} charts, {} cards Γ£ô".format(
        len(dash.charts), len(dash.cards)))


def fix_kya_services_number_cards():
    """Ensure KYA Services Portail Enqu├¬te shortcut has correct type=URL (not DocType)."""
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET type = 'URL', url = '/kya-survey', link_to = ''
        WHERE parent = 'KYA Services' AND label = 'Portail Enqu├¬te'
    """)
    # Also ensure the 'R├⌐ponses Re├ºues' Number Card filter key is valid
    frappe.db.sql("""
        UPDATE `tabNumber Card`
        SET filters_json = '[["KYA Form Response","soumis_le","is","set"]]'
        WHERE name = 'R├⌐ponses Re├ºues' AND document_type = 'KYA Form Response'
    """)
    print("  [KYA Services] Portail Enqu├¬te type=URL Γ£ô ┬╖ R├⌐ponses Re├ºues filter Γ£ô")


def fix_stagiaires_number_cards():
    """Create Number Cards for Stagiaires module and inject into workspace content."""
    cards_to_create = [
        {
            "name": "Stagiaires Actifs",
            "label": "Stagiaires Actifs",
            "document_type": "Employee",
            "function": "Count",
            "filters_json": '[["Employee","employment_type","=","Stage"],["Employee","status","=","Active"]]',
            "color": "#009688",
        },
        {
            "name": "Permissions Stagiaires en Attente",
            "label": "Permissions Stagiaires en Attente",
            "legacy_labels": ["Permissions en Attente"],
            "document_type": "Permission Sortie Stagiaire",
            "function": "Count",
            "filters_json": '[["Permission Sortie Stagiaire","workflow_state","not in",["Approuv├⌐","Rejet├⌐"]]]',
            "color": "#e67e22",
        },
        {
            "name": "Bilans de Stage Soumis",
            "label": "Bilans de Stage Soumis",
            "legacy_labels": ["Bilans Soumis"],
            "document_type": "Bilan Fin de Stage",
            "function": "Count",
            "filters_json": '[["Bilan Fin de Stage","docstatus","!=",0]]',
            "color": "#1a5276",
        },
    ]
    created = 0
    updated = 0
    for card_data in cards_to_create:
        name = card_data["name"]
        label = card_data["label"]
        legacy_labels = card_data.get("legacy_labels", [])
        payload = {
            "label": label,
            "document_type": card_data["document_type"],
            "function": card_data["function"],
            "filters_json": card_data["filters_json"],
            "color": card_data["color"],
            "is_standard": 0,
        }

        try:
            existing_name = frappe.db.exists("Number Card", name)
            if not existing_name:
                for legacy_label in [label, *legacy_labels]:
                    existing_name = frappe.db.get_value("Number Card", {"label": legacy_label}, "name")
                    if existing_name:
                        break

            if existing_name:
                frappe.db.set_value("Number Card", existing_name, payload)
                if existing_name != name and not frappe.db.exists("Number Card", name):
                    try:
                        frappe.rename_doc("Number Card", existing_name, name, force=True, ignore_if_exists=True)
                        existing_name = name
                    except Exception as rename_exc:
                        print(f"  [Stagiaires NC] Rename '{existing_name}' -> '{name}' skipped: {rename_exc}")
                updated += 1
            else:
                card = frappe.new_doc("Number Card")
                card.name = name
                for k, v in payload.items():
                    setattr(card, k, v)
                card.insert(ignore_permissions=True, ignore_if_duplicate=True)
                if card.name != name and not frappe.db.exists("Number Card", name):
                    try:
                        frappe.rename_doc("Number Card", card.name, name, force=True, ignore_if_exists=True)
                    except Exception as rename_exc:
                        print(f"  [Stagiaires NC] Rename '{card.name}' -> '{name}' skipped: {rename_exc}")
                created += 1
        except Exception as e:
            print(f"  [Stagiaires NC] Skipped '{name}': {e}")

    print(f"  [Stagiaires] {created} Number Cards cr├⌐├⌐s ┬╖ {updated} mis ├á jour Γ£ô")

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
        print("  [Stagiaires] Workspace content mis ├á jour avec Number Cards Γ£ô")


def fix_kya_services_total_reponses():
    """Ensure 'Total R├⌐ponses' and 'Formulaires Actifs' Number Cards exist."""
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
            "name": "Total R├⌐ponses",
            "label": "Total R├⌐ponses",
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
    print(f"  [KYA Services NC] {created} Number Cards cr├⌐├⌐s Γ£ô")


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
    print("  [Navbar] app_logo ΓåÆ /assets/kya_hr/images/kya_logo.png Γ£ô")


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
    print("  [Website Settings] app_logo + splash_image ΓåÆ KYA logo Γ£ô")


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# DASHBOARDS STRAT├ëGIQUES
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ

def _upsert_workspace_shortcut(workspace, label, type_, url, color, icon="bar-chart"):
    """Insert ou met ├á jour un Workspace Shortcut (type=URL)."""
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
    """Cr├⌐er ou mettre ├á jour le dashboard strat├⌐gique Gestion ├ëquipe."""
    # ΓöÇΓöÇ Charts ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    charts_def = [
        {
            "name": "Gestion ├ëquipe - Plans par mois",
            "document_type": "Plan Trimestriel",
            "type": "Bar",
            "based_on": "creation",
            "time_interval": "Monthly",
            "timespan": "Last Year",
        },
        {
            "name": "Gestion ├ëquipe - ├ëvaluations par mois",
            "document_type": "KYA Evaluation",
            "type": "Line",
            "based_on": "creation",
            "time_interval": "Monthly",
            "timespan": "Last Year",
        },
        {
            "name": "≡ƒÅå Score collectif par ├⌐quipe",
            "document_type": "Plan Trimestriel",
            "chart_type": "Group By",
            "group_by_based_on": "equipe",
            "group_by_type": "Average",
            "value_based_on": "score_collectif",
            "aggregate_function_based_on": "score_collectif",
            "type": "Bar",
        },
        {
            "name": "≡ƒæÑ Performance par ├⌐quipe",
            "document_type": "Tache Equipe",
            "chart_type": "Group By",
            "group_by_based_on": "equipe",
            "group_by_type": "Average",
            "value_based_on": "taux_effectif",
            "aggregate_function_based_on": "taux_effectif",
            "type": "Bar",
        },
    ]
    chart_names = []
    for chart_def in charts_def:
        cname = chart_def["name"]
        if not frappe.db.exists("Dashboard Chart", cname):
            try:
                chart = frappe.new_doc("Dashboard Chart")
                chart.chart_name    = cname
                chart.document_type = chart_def["document_type"]
                chart.type          = chart_def.get("type", "Bar")
                chart.chart_type    = chart_def.get("chart_type", "Count")
                chart.based_on      = chart_def.get("based_on", "creation")
                chart.time_interval = chart_def.get("time_interval", "Monthly")
                chart.timespan      = chart_def.get("timespan", "Last Year")
                chart.group_by_based_on = chart_def.get("group_by_based_on", "")
                chart.group_by_type = chart_def.get("group_by_type", "Count")
                chart.value_based_on = chart_def.get("value_based_on", "")
                chart.aggregate_function_based_on = chart_def.get("aggregate_function_based_on", "")
                chart.filters_json  = "[]"
                chart.is_standard   = 0
                chart.save(ignore_permissions=True)
            except Exception as e:
                print("  [Dashboard] Chart skip '{}': {}".format(cname, e))
                continue
        chart_names.append(cname)

    # ΓöÇΓöÇ Number Cards ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    nc_def = [
        ("Plans En Cours",
         "Plan Trimestriel", '[["Plan Trimestriel","statut","=","En cours"]]', "#2196f3"),
        ("T├óches En Cours",
         "Tache Equipe",     '[["Tache Equipe","statut","=","En cours"]]',      "#ff9800"),
        ("├ëvaluations ├á Valider",
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

    # ΓöÇΓöÇ Dashboard (get or create, toujours rebuild) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    dash_name = "Gestion ├ëquipe"
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
    print("  [Dashboard] Gestion ├ëquipe ΓåÆ {} charts, {} cards Γ£ô".format(
        len(dash.charts), len(dash.cards)))

    # ΓöÇΓöÇ Shortcut dans workspace Gestion ├ëquipe ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    _upsert_workspace_shortcut(
        "Gestion ├ëquipe", "≡ƒôè Dashboard ├ëquipe",
        "URL", "/app/dashboard/Gestion%20%C3%89quipe", "#673ab7", "bar-chart-2"
    )
    print("  [Dashboard] Shortcuts Gestion ├ëquipe + KYA Services mis ├á jour Γ£ô")


def fix_bad_doctype_shortcuts():
    """Corriger les shortcuts qui pointent vers des DocTypes inexistants.
    Ces shortcuts causent l'erreur 'DocType xxx introuvable' quand on clique dessus."""
    # Lister tous les shortcuts de type 'DocType' dont le link_to n'existe pas
    bad = frappe.db.sql("""
        SELECT ws.name, ws.parent, ws.label, ws.link_to
        FROM `tabWorkspace Shortcut` ws
        WHERE ws.type = 'DocType'
          AND (ws.link_to IS NULL OR ws.link_to = '' OR ws.link_to NOT IN (SELECT name FROM tabDocType))
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
            # Convertir en URL vide pour ├⌐viter l'erreur (shortcut visible mais inactif)
            frappe.db.sql("""
                UPDATE `tabWorkspace Shortcut`
                SET type = 'URL', url = '', link_to = ''
                WHERE name = %s
            """, (row["name"],))
        fixed += 1
        print(f"  [Bad Shortcut] Fixed: {row['parent']} / {row['label']} ΓåÆ {row['link_to']}")

    # Aussi v├⌐rifier les Workspace Links (cards)
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

    print(f"  [Bad DocType] {fixed} shortcuts/links corrig├⌐s Γ£ô")


def fix_dashboard_shortcuts_to_stats_page():
    """Pointer les shortcuts vers /kya-stats (page de stats r├⌐elles).
    Ne cr├⌐e qu'UN seul shortcut stats (≡ƒôê Statistiques), pas de doublon.
    """
    # Supprimer le doublon ┬½ ≡ƒôè Dashboard KYA ┬╗ s'il existe
    frappe.db.sql("""
        DELETE FROM `tabWorkspace Shortcut`
        WHERE parent = 'KYA Services' AND label = '≡ƒôè Dashboard KYA'
    """)

    # Shortcut unique ┬½ ≡ƒôê Statistiques ┬╗ dans KYA Services ΓåÆ /kya-stats
    _upsert_workspace_shortcut(
        "KYA Services", "≡ƒôê Statistiques",
        "URL", "/kya-stats", "#0077b6", "trending-up"
    )

    # Shortcut dans Gestion ├ëquipe ΓåÆ dashboard custom KYA
    _upsert_workspace_shortcut(
        "Gestion ├ëquipe", "≡ƒôè Dashboard ├ëquipe",
        "URL", "/kya-dashboard-equipe", "#673ab7", "bar-chart-2"
    )

    print("  [Dashboard Shortcuts] /kya-stats et /app/dashboard mis ├á jour Γ£ô")


def fix_workspace_number_card_links():
    """Lier les Workspace Number Card rows aux documents Number Card existants.
    Sans ce lien, les indicateurs apparaissent vides dans le workspace."""
    # KYA Services
    kya_nc_map = {
        "Total Formulaires": "Total Formulaires",
        "Formulaires Actifs": "Formulaires Actifs",
        "R├⌐ponses Re├ºues": "R├⌐ponses Re├ºues",
        "Total ├ëvaluations": "Total ├ëvaluations",
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

    print("  [NC Links] Workspace Number Cards li├⌐s aux documents Γ£ô")


def fix_stagiaires_permissions():
    """Ajouter les r├┤les Stagiaire + Responsable des Stagiaires aux DocTypes custom
    du module stagiaires (tabDocPerm ΓÇö bench migrate ne les synchronise pas car custom=1)."""
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


def fix_tableau_de_bord_shortcut():
    """Fix 'Tableau de Bord' shortcut in Gestion Equipe to point to /kya-dashboard-equipe."""
    _upsert_workspace_shortcut(
        "Gestion \u00c9quipe", "Tableau de Bord",
        "URL", "/kya-dashboard-equipe", "#1a237e", "bar-chart-2"
    )
    # Remove the '≡ƒôè Dashboard Equipe' duplicate if it still exists
    frappe.db.sql("""
        DELETE FROM `tabWorkspace Shortcut`
        WHERE parent = 'Gestion \u00c9quipe'
          AND label = '\U0001f4ca Dashboard \u00c9quipe'
    """)
    frappe.db.commit()
    print("  [Gestion Equipe] 'Tableau de Bord' -> /kya-dashboard-equipe OK")
    print("  [Gestion Equipe] Duplicate Dashboard shortcut removed")


def fix_ws_shortcuts_and_nc_filters():
    """Fix: (1) Remove duplicate Tableau de Bord shortcut from Gestion Equipe.
            (2) Fix Number Card filters to use valid 4-element Frappe v16 format."""
    import json

    # ΓöÇΓöÇ 1. Remove duplicate "Tableau de Bord" shortcut from Gestion Equipe ΓöÇΓöÇΓöÇΓöÇ
    # Keep "≡ƒôè Dashboard ├ëquipe", remove the plain "Tableau de Bord" duplicate
    deleted = frappe.db.sql("""
        DELETE FROM `tabWorkspace Shortcut`
        WHERE parent = 'Gestion \u00c9quipe'
          AND label = 'Tableau de Bord'
    """)
    rows_deleted = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    print(f"  [Gestion Equipe] Removed {rows_deleted} duplicate 'Tableau de Bord' shortcut(s) Γ£ô")

    # ΓöÇΓöÇ 2. Fix Number Card filters (remove invalid 5th element) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    nc_fixes = [
        (
            "Stagiaires Actifs",
            json.dumps([
                ["Employee", "employment_type", "=", "Stage"],
                ["Employee", "status", "=", "Active"]
            ])
        ),
        (
            "Permissions Stagiaires en Attente",
            json.dumps([
                ["Permission Sortie Stagiaire", "workflow_state", "not in",
                 ["Approuv\u00e9", "Rejet\u00e9"]]
            ])
        ),
        (
            "Bilans de Stage Soumis",
            json.dumps([
                ["Bilan Fin de Stage", "docstatus", "!=", 0]
            ])
        ),
    ]
    updated_nc = 0
    for nc_name, filters in nc_fixes:
        if frappe.db.exists("Number Card", nc_name):
            frappe.db.set_value("Number Card", nc_name, "filters_json", filters)
            updated_nc += 1
            print(f"  [Number Card] '{nc_name}' filters updated Γ£ô")
        else:
            print(f"  [Number Card] '{nc_name}' NOT FOUND ΓÇö skipping")

    frappe.db.commit()
    frappe.clear_cache()
    print(f"  [fix_ws_shortcuts_and_nc_filters] DONE ΓÇö {rows_deleted} shortcuts removed, {updated_nc} NC filters fixed")

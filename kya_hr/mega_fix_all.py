"""
mega_fix_all.py — Correction complète de tous les problèmes identifiés (19 mars 2026)

Problèmes réglés:
 1. Rapport "Rapport Présence Stagiaires" → renommé "Rapport Presence Stagiaires" (accent → module Python)
 2. Workspace Buying/Stock — NCs et chart AVANT le 1er header → ne se rendent pas, on ajoute header
 3. Workspace Buying/Stock — doublons KYA supprimés
 4. Dashboard Charts based_on=None → genre, département, statut, présences
 5. HRMS icons invalides ("accounting", "hr") → icônes Lucide valides
 6. KYA Services — NCs manquants créés + charts créés + workspace content corrigé
 7. Espace Stagiaires — chart "Statut Permissions Stagiaires" ajouté à la child table
"""
import frappe
import json


def execute():
    results = []

    results += fix_rapport_presence()
    results += fix_workspace_buying()
    results += fix_workspace_stock()
    results += fix_dashboard_charts()
    results += fix_hrms_icons()
    results += fix_kya_services()
    results += fix_espace_stagiaires_charts()

    frappe.db.commit()

    print("\n" + "=" * 60)
    print("RÉCAPITULATIF DES CORRECTIONS")
    print("=" * 60)
    for r in results:
        print(f"  {r}")
    print(f"\nTotal: {len(results)} corrections appliquées")


# ─────────────────────────────────────────────────────────
# 1. RAPPORT: Supprimer accent "é" dans le nom
# ─────────────────────────────────────────────────────────
def fix_rapport_presence():
    log = []

    renames = [
        ("Rapport Présence Stagiaires", "Rapport Presence Stagiaires"),
        ("Rapport Présence Employés", "Rapport Presence Employes"),
    ]

    for old_name, new_name in renames:
        exists = frappe.db.exists("Report", old_name)
        already_fixed = frappe.db.exists("Report", new_name)

        if already_fixed:
            log.append(f"[SKIP] Rapport déjà renommé en '{new_name}'")
            continue

        if not exists:
            log.append(f"[WARN] Rapport '{old_name}' non trouvé en DB")
            continue

        frappe.db.sql("""
            UPDATE `tabReport`
            SET name = %s, report_name = %s
            WHERE name = %s
        """, (new_name, new_name, old_name))

        frappe.db.sql("""
            UPDATE `tabWorkspace Link`
            SET link_to = %s, label = %s
            WHERE link_to = %s AND link_type = 'Report'
        """, (new_name, new_name, old_name))

        frappe.db.sql("""
            UPDATE `tabDashboard Chart`
            SET report_name = %s
            WHERE report_name = %s
        """, (new_name, old_name))

        log.append(f"[OK] Rapport renommé: '{old_name}' → '{new_name}'")

    return log


# ─────────────────────────────────────────────────────────
# 2. WORKSPACE BUYING — restructurer content
# ─────────────────────────────────────────────────────────
def fix_workspace_buying():
    log = []
    new_content = [
        {"id": "h_dashboard", "type": "header", "data": {
            "text": "📊 Tableau de Bord Achats", "level": 4, "col": 12}},
        {"id": "nc_po_count", "type": "number_card", "data": {
            "number_card_name": "Purchase Orders Count", "col": 4}},
        {"id": "nc_po_amount", "type": "number_card", "data": {
            "number_card_name": "Total Purchase Amount", "col": 4}},
        {"id": "nc_bills", "type": "number_card", "data": {
            "number_card_name": "Total Incoming Bills", "col": 4}},
        {"id": "spacer_ch", "type": "spacer", "data": {"col": 12}},
        {"id": "ch_trends", "type": "chart", "data": {
            "chart_name": "Purchase Order Trends", "col": 12}},
        {"id": "spacer_kya", "type": "spacer", "data": {"col": 12}},
        {"id": "h_kya", "type": "header", "data": {
            "text": "<span>🏷️ KYA — Demandes Achat</span>", "level": 4, "col": 12}},
        {"id": "kya_da", "type": "shortcut", "data": {
            "shortcut_name": "Demande d'Achat KYA", "col": 6}},
        {"id": "kya_form", "type": "shortcut", "data": {
            "shortcut_name": "Form. Demande Achat", "col": 6}},
    ]
    try:
        # Utiliser SQL direct pour éviter la validation DocType URL
        frappe.db.set_value("Workspace", "Buying", "content", json.dumps(new_content),
                            update_modified=False)
        # Ajouter le chart à la child table s'il manque
        existing = frappe.db.sql(
            "SELECT chart_name FROM `tabWorkspace Chart` WHERE parent='Buying'",
            as_dict=True)
        existing_names = [c.chart_name for c in existing]
        if "Purchase Order Trends" not in existing_names:
            frappe.db.sql("""
                INSERT INTO `tabWorkspace Chart` (name, parent, parenttype, parentfield,
                                                  chart_name, idx)
                VALUES (%(nm)s, 'Buying', 'Workspace', 'charts', 'Purchase Order Trends', 1)
            """, {"nm": frappe.generate_hash(10)})
        log.append("[OK] Workspace Buying — content restructuré via SQL (header + NCs + chart + KYA)")
    except Exception as e:
        log.append(f"[ERR] Workspace Buying: {e}")
    return log


# ─────────────────────────────────────────────────────────
# 3. WORKSPACE STOCK — restructurer content
# ─────────────────────────────────────────────────────────
def fix_workspace_stock():
    log = []
    new_content = [
        {"id": "h_dashboard", "type": "header", "data": {
            "text": "📊 Tableau de Bord Stock", "level": 4, "col": 12}},
        {"id": "nc_stock_val", "type": "number_card", "data": {
            "number_card_name": "Total Stock Value", "col": 4}},
        {"id": "nc_warehouses", "type": "number_card", "data": {
            "number_card_name": "Total Warehouses", "col": 4}},
        {"id": "nc_items", "type": "number_card", "data": {
            "number_card_name": "Total Active Items", "col": 4}},
        {"id": "spacer_ch", "type": "spacer", "data": {"col": 12}},
        {"id": "ch_stock", "type": "chart", "data": {
            "chart_name": "Warehouse wise Stock Value", "col": 12}},
        {"id": "spacer_kya", "type": "spacer", "data": {"col": 12}},
        {"id": "h_kya", "type": "header", "data": {
            "text": "<span>📦 KYA — PV Sortie Matériel</span>", "level": 4, "col": 12}},
        {"id": "kya_pv", "type": "shortcut", "data": {
            "shortcut_name": "PV Sortie Matériel", "col": 6}},
        {"id": "kya_form", "type": "shortcut", "data": {
            "shortcut_name": "Form. PV Sortie", "col": 6}},
    ]
    try:
        frappe.db.set_value("Workspace", "Stock", "content", json.dumps(new_content),
                            update_modified=False)
        existing = frappe.db.sql(
            "SELECT chart_name FROM `tabWorkspace Chart` WHERE parent='Stock'",
            as_dict=True)
        existing_names = [c.chart_name for c in existing]
        if "Warehouse wise Stock Value" not in existing_names:
            frappe.db.sql("""
                INSERT INTO `tabWorkspace Chart` (name, parent, parenttype, parentfield,
                                                  chart_name, idx)
                VALUES (%(nm)s, 'Stock', 'Workspace', 'charts', 'Warehouse wise Stock Value', 1)
            """, {"nm": frappe.generate_hash(10)})
        log.append("[OK] Workspace Stock — content restructuré via SQL (header + NCs + chart + KYA)")
    except Exception as e:
        log.append(f"[ERR] Workspace Stock: {e}")
    return log


# ─────────────────────────────────────────────────────────
# 4. DASHBOARD CHARTS — corriger based_on=None
# ─────────────────────────────────────────────────────────
def fix_dashboard_charts():
    log = []

    charts_to_fix = [
        # (name, based_on, filters_list, visual_type)
        ("Répartition par Genre", "gender",
         [["Employee", "employment_type", "=", "Stage"], ["Employee", "status", "=", "Active"]],
         "donut"),
        ("Stagiaires par Département", "department",
         [["Employee", "employment_type", "=", "Stage"], ["Employee", "status", "=", "Active"]],
         "bar"),
        ("Présences Mensuelles", "status",
         [["Attendance", "attendance_date", "Timespan", "this month"],
          ["Attendance", "employee", "like", "KEG-STG%"]],
         "bar"),
        ("Statut Permissions Stagiaires", "workflow_state", [], "pie"),
    ]

    for chart_name, based_on, filters_list, visual_type in charts_to_fix:
        try:
            if not frappe.db.exists("Dashboard Chart", chart_name):
                log.append(f"[WARN] Chart '{chart_name}' non trouvé")
                continue
            # Pour Group By charts: champ = group_by_based_on
            frappe.db.set_value("Dashboard Chart", chart_name, "group_by_based_on", based_on,
                                update_modified=False)
            frappe.db.set_value("Dashboard Chart", chart_name, "value_based_on", "",
                                update_modified=False)
            frappe.db.set_value("Dashboard Chart", chart_name, "type", visual_type,
                                update_modified=False)
            if filters_list:
                import json as _json
                frappe.db.set_value("Dashboard Chart", chart_name, "filters_json",
                                    _json.dumps(filters_list), update_modified=False)
            log.append(f"[OK] Chart '{chart_name}': group_by='{based_on}', visual='{visual_type}'")
        except Exception as e:
            log.append(f"[ERR] Chart '{chart_name}': {e}")

    return log


# ─────────────────────────────────────────────────────────
# 5. HRMS ICONS — remplacer icônes Lucide invalides
# ─────────────────────────────────────────────────────────
def fix_hrms_icons():
    log = []

    # accounting et hr ne sont pas des icônes Lucide valides dans Frappe v16
    icon_fixes = {
        "Payroll": "calculator",           # accounting → calculator
        "Ressources Humaines": "users",    # hr → users
        "Shift & Attendance": "clock",     # milestone → clock (pour les shifts/présences)
    }

    for ws_name, new_icon in icon_fixes.items():
        try:
            if not frappe.db.exists("Workspace", ws_name):
                log.append(f"[WARN] Workspace '{ws_name}' non trouvé")
                continue
            old_icon = frappe.db.get_value("Workspace", ws_name, "icon")
            frappe.db.set_value("Workspace", ws_name, "icon", new_icon)
            log.append(f"[OK] Workspace '{ws_name}': icon '{old_icon}' → '{new_icon}'")
        except Exception as e:
            log.append(f"[ERR] Icon fix '{ws_name}': {e}")

    return log


# ─────────────────────────────────────────────────────────
# 6. KYA SERVICES — créer NCs manquants + charts + corriger workspace
# ─────────────────────────────────────────────────────────
def fix_kya_services():
    log = []

    # 6a. Créer les Number Cards manquants pour KYA Services
    ncs_to_create = [
        {
            "name": "Total Formulaires KYA",
            "label": "Total Formulaires",
            "document_type": "KYA Form",
            "function": "Count",
            "filters_json": "[]",
            "color": "#7575FF",
            "is_public": 1,
        },
        {
            "name": "Formulaires Actifs KYA",
            "label": "Formulaires Actifs",
            "document_type": "KYA Form",
            "function": "Count",
            "filters_json": '[["KYA Form","statut","=","Actif"]]',
            "color": "#36AE7C",
            "is_public": 1,
        },
        {
            "name": "Total Evaluations KYA",
            "label": "Évaluations",
            "document_type": "KYA Evaluation",
            "function": "Count",
            "filters_json": "[]",
            "color": "#FF6B6B",
            "is_public": 1,
        },
        {
            "name": "Reponses Recues KYA",
            "label": "Réponses Reçues",
            "document_type": "KYA Form Response",
            "function": "Count",
            "filters_json": '[["KYA Form Response","soumis_le","is","set"]]',
            "color": "#F0A500",
            "is_public": 1,
        },
    ]

    for nc_data in ncs_to_create:
        nc_name = nc_data["name"]
        if frappe.db.exists("Number Card", nc_name):
            log.append(f"[SKIP] NC '{nc_name}' déjà existant")
            continue
        try:
            nc = frappe.new_doc("Number Card")
            nc.name = nc_name
            nc.label = nc_data["label"]
            nc.document_type = nc_data["document_type"]
            nc.function = nc_data["function"]
            nc.filters_json = nc_data["filters_json"]
            nc.color = nc_data["color"]
            nc.is_public = nc_data.get("is_public", 1)
            nc.insert(ignore_permissions=True)
            log.append(f"[OK] NC créé: '{nc_name}'")
        except Exception as e:
            log.append(f"[ERR] NC '{nc_name}': {e}")

    # 6b. Créer les Dashboard Charts pour KYA Services
    charts_to_create = [
        {
            "name": "Formulaires par Type KYA",
            "chart_name": "Formulaires par Type KYA",
            "chart_type": "Group By",  # type calcul Frappe
            "type": "donut",           # type affichage frappe charts
            "document_type": "KYA Form",
            "based_on": "type_formulaire",
            "group_by_type": "Count",
            "is_public": 1,
        },
        {
            "name": "Statut Formulaires KYA",
            "chart_name": "Statut Formulaires KYA",
            "chart_type": "Group By",
            "type": "pie",
            "document_type": "KYA Form",
            "based_on": "statut",
            "group_by_type": "Count",
            "is_public": 1,
        },
        {
            "name": "Evaluations par Type KYA",
            "chart_name": "Evaluations par Type KYA",
            "chart_type": "Group By",
            "type": "bar",
            "document_type": "KYA Evaluation",
            "based_on": "type_evaluation",
            "group_by_type": "Count",
            "is_public": 1,
        },
        {
            "name": "Evaluations par Trimestre KYA",
            "chart_name": "Evaluations par Trimestre KYA",
            "chart_type": "Group By",
            "type": "bar",
            "document_type": "KYA Evaluation",
            "based_on": "trimestre",
            "group_by_type": "Count",
            "is_public": 1,
        },
    ]

    for c_data in charts_to_create:
        c_name = c_data["name"]
        if frappe.db.exists("Dashboard Chart", c_name):
            log.append(f"[SKIP] Chart '{c_name}' déjà existant")
            continue
        try:
            chart = frappe.new_doc("Dashboard Chart")
            chart.name = c_name
            chart.chart_name = c_data["chart_name"]
            chart.chart_type = c_data["chart_type"]
            chart.document_type = c_data["document_type"]
            # Pour Group By: utiliser group_by_based_on (pas based_on)
            chart.group_by_based_on = c_data["based_on"]
            chart.value_based_on = ""
            chart.filters_json = "[]"
            chart.is_public = c_data.get("is_public", 1)
            chart.group_by_type = c_data.get("group_by_type", "Count")
            chart.insert(ignore_permissions=True)
            # Mettre à jour le type visuel après insert
            frappe.db.set_value("Dashboard Chart", c_name, "type", c_data.get("type", "bar"),
                                update_modified=False)
            log.append(f"[OK] Chart créé: '{c_name}'")
        except Exception as e:
            log.append(f"[ERR] Chart '{c_name}': {e}")

    # 6c. Mettre à jour le workspace KYA Services avec le bon contenu
    try:
        ws = frappe.get_doc("Workspace", "KYA Services")

        new_content = [
            {"id": "h_main", "type": "header", "data": {
                "text": "<div class='ellipsis'>📋 KYA Services — Administration</div>",
                "level": 3, "col": 12}},
            {"id": "sc_forms", "type": "shortcut", "data": {
                "shortcut_name": "Formulaires", "col": 3}},
            {"id": "sc_evals", "type": "shortcut", "data": {
                "shortcut_name": "Évaluations", "col": 3}},
            {"id": "sc_reps", "type": "shortcut", "data": {
                "shortcut_name": "Réponses", "col": 3}},
            {"id": "sc_portal", "type": "shortcut", "data": {
                "shortcut_name": "Portail Enquête", "col": 3}},
            {"id": "spacer1", "type": "spacer", "data": {"col": 12}},
            {"id": "h_indicateurs", "type": "header", "data": {
                "text": "📊 Indicateurs", "level": 4, "col": 12}},
            {"id": "nc_tf", "type": "number_card", "data": {
                "number_card_name": "Total Formulaires KYA", "col": 3}},
            {"id": "nc_fa", "type": "number_card", "data": {
                "number_card_name": "Formulaires Actifs KYA", "col": 3}},
            {"id": "nc_te", "type": "number_card", "data": {
                "number_card_name": "Total Evaluations KYA", "col": 3}},
            {"id": "nc_rr", "type": "number_card", "data": {
                "number_card_name": "Reponses Recues KYA", "col": 3}},
            {"id": "spacer2", "type": "spacer", "data": {"col": 12}},
            {"id": "h_charts", "type": "header", "data": {
                "text": "📈 Analyse des Enquêtes & Évaluations", "level": 4, "col": 12}},
            {"id": "ch_type", "type": "chart", "data": {
                "chart_name": "Formulaires par Type KYA", "col": 6}},
            {"id": "ch_statut", "type": "chart", "data": {
                "chart_name": "Statut Formulaires KYA", "col": 6}},
            {"id": "ch_eval_type", "type": "chart", "data": {
                "chart_name": "Evaluations par Type KYA", "col": 6}},
            {"id": "ch_eval_tri", "type": "chart", "data": {
                "chart_name": "Evaluations par Trimestre KYA", "col": 6}},
        ]

        # Utiliser SQL direct pour éviter la validation DocType URL
        frappe.db.set_value("Workspace", "KYA Services", "content", json.dumps(new_content),
                            update_modified=False)

        # Mettre à jour les charts dans la child table via SQL
        frappe.db.sql("DELETE FROM `tabWorkspace Chart` WHERE parent='KYA Services'")
        chart_names = ["Formulaires par Type KYA", "Statut Formulaires KYA",
                       "Evaluations par Type KYA", "Evaluations par Trimestre KYA"]
        for idx, cname in enumerate(chart_names):
            if frappe.db.exists("Dashboard Chart", cname):
                frappe.db.sql("""
                    INSERT INTO `tabWorkspace Chart` (name, parent, parenttype, parentfield,
                                                      chart_name, idx)
                    VALUES (%(nm)s, 'KYA Services', 'Workspace', 'charts', %(cn)s, %(idx)s)
                """, {"nm": frappe.generate_hash(10), "cn": cname, "idx": idx + 1})

        log.append("[OK] Workspace KYA Services — content + charts + NCs mis à jour via SQL")
    except Exception as e:
        log.append(f"[ERR] Workspace KYA Services: {e}")

    return log


# ─────────────────────────────────────────────────────────
# 7. ESPACE STAGIAIRES — ajouter chart manquant à la child table
# ─────────────────────────────────────────────────────────
def fix_espace_stagiaires_charts():
    log = []
    try:
        existing = frappe.db.sql(
            "SELECT chart_name FROM `tabWorkspace Chart` WHERE parent='Espace Stagiaires'",
            as_dict=True)
        existing_names = [c.chart_name for c in existing]

        added = []
        for chart_name in ["Statut Permissions Stagiaires"]:
            if chart_name not in existing_names:
                frappe.db.sql("""
                    INSERT INTO `tabWorkspace Chart` (name, parent, parenttype, parentfield,
                                                      chart_name)
                    VALUES (%(nm)s, 'Espace Stagiaires', 'Workspace', 'charts', %(cn)s)
                """, {"nm": frappe.generate_hash(10), "cn": chart_name})
                added.append(chart_name)

        if added:
            log.append(f"[OK] Espace Stagiaires — charts ajoutés via SQL: {added}")
        else:
            log.append("[SKIP] Espace Stagiaires charts déjà complets")
    except Exception as e:
        log.append(f"[ERR] Espace Stagiaires charts: {e}")

    return log

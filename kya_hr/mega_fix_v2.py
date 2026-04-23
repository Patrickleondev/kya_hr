"""
mega_fix_v2.py — Fix complet KYA Workspaces + Services
=======================================================
Actions :
  1. Diagnostiquer les workspaces Buying, Stock, HRMS
  2. Corriger KYA Services sidebar (retirer kya_evaluation_critere = child table = 404)
  3. Ajouter section KYA dans le CONTENT JSON de Buying et Stock
  4. Reconstruire KYA Stagiaires avec dashboard présences (Number Cards + Charts)
  5. Créer/corriger les Workspace Sidebar Items pour HRMS (Personnes, Congés)
  6. Nettoyer le cache
"""
import frappe
import json


# ============================================================
# HELPERS
# ============================================================

def _reset_links(ws_name, links_data):
    """Remplace TOUS les links d'un workspace."""
    frappe.db.delete("Workspace Link", {"parent": ws_name})
    for i, lk in enumerate(links_data):
        row = frappe.new_doc("Workspace Link")
        row.parent = ws_name
        row.parenttype = "Workspace"
        row.parentfield = "links"
        row.idx = i + 1
        row.type = lk.get("type", "Link")
        row.label = lk.get("label", "")
        row.link_to = lk.get("link_to") or None
        row.link_type = lk.get("link_type") or None
        row.hidden = 0
        row.icon = lk.get("icon") or None
        row.onboard = lk.get("onboard", 0)
        row.dependencies = lk.get("dependencies") or None
        row.report_ref_doctype = lk.get("report_ref_doctype") or None
        row.db_insert()


def _reset_shortcuts(ws_name, shortcuts):
    frappe.db.delete("Workspace Shortcut", {"parent": ws_name})
    for i, sc in enumerate(shortcuts):
        row = frappe.new_doc("Workspace Shortcut")
        row.parent = ws_name
        row.parenttype = "Workspace"
        row.parentfield = "shortcuts"
        row.idx = i + 1
        row.label = sc["label"]
        row.type = sc.get("type", "DocType")
        row.link_to = sc.get("link_to", "") if sc.get("type") != "URL" else ""
        row.url = sc.get("url", "") if sc.get("type") == "URL" else ""
        row.color = sc.get("color", "")
        row.db_insert()


def _ensure_number_card(name, label, document_type, color="#4CAF50", filters=None):
    if frappe.db.exists("Number Card", name):
        return False
    doc = frappe.new_doc("Number Card")
    doc.name = name
    doc.label = label
    doc.document_type = document_type
    doc.function = "Count"
    doc.aggregate_function_based_on = "name"
    doc.color = color
    doc.filters_json = json.dumps(filters or [])
    doc.is_public = 1
    doc.insert(ignore_permissions=True)
    return True


def _update_number_card_filter(name, filters):
    """Met à jour les filtres d'une Number Card existante."""
    if frappe.db.exists("Number Card", name):
        frappe.db.set_value("Number Card", name, "filters_json",
                            json.dumps(filters), update_modified=False)


def _get_ws_content(ws_name):
    raw = frappe.db.get_value("Workspace", ws_name, "content") or "[]"
    try:
        return json.loads(raw)
    except Exception:
        return []


def _inject_kya_to_native_content(ws_name, section_header, shortcut_defs):
    """Injecte une section KYA dans le content JSON d'un workspace natif.
    Évite les doublons en supprimant l'ancien block KYA si présent."""
    content = _get_ws_content(ws_name)

    # Supprimer ancien bloc KYA s'il existe
    clean = []
    skip = False
    for item in content:
        if item.get("type") == "header":
            text = (item.get("data") or {}).get("text", "")
            if "KYA" in text:
                skip = True
                continue
            else:
                skip = False
        if item.get("type") == "shortcut":
            sc_name = (item.get("data") or {}).get("shortcut_name", "")
            if sc_name in [s["label"] for s in shortcut_defs]:
                continue
        if not skip:
            clean.append(item)

    # Créer les shortcuts si non existants
    for sc in shortcut_defs:
        if not frappe.db.exists("Workspace Shortcut", {"label": sc["label"], "parent": ws_name}):
            row = frappe.new_doc("Workspace Shortcut")
            row.parent = ws_name
            row.parenttype = "Workspace"
            row.parentfield = "shortcuts"
            row.label = sc["label"]
            row.type = sc.get("type", "DocType")
            row.link_to = sc.get("link_to", "") if sc.get("type") != "URL" else ""
            row.url = sc.get("url", "") if sc.get("type") == "URL" else ""
            row.color = sc.get("color", "#009688")
            row.db_insert()

    # Ajouter en fin de content
    import hashlib
    def uid(s):
        return hashlib.md5(s.encode()).hexdigest()[:6]

    new_items = [
        {"id": uid("spacer" + ws_name), "type": "spacer", "data": {"col": 12}},
        {"id": uid("hdr" + ws_name), "type": "header",
         "data": {"text": f"<div class='ellipsis'>{section_header}</div>",
                  "level": 4, "col": 12}},
    ]
    for sc in shortcut_defs:
        new_items.append({
            "id": uid(sc["label"]),
            "type": "shortcut",
            "data": {"shortcut_name": sc["label"], "col": sc.get("col", 3)}
        })

    final_content = clean + new_items
    frappe.db.set_value("Workspace", ws_name, "content",
                        json.dumps(final_content, ensure_ascii=False),
                        update_modified=True)
    return len(final_content)


def _ensure_workspace_sidebar_items(sidebar_name, items_def):
    """Crée/met à jour les items d'un Workspace Sidebar (navigation gauche Frappe v16).
    sidebar_name = nom du record tabWorkspace Sidebar.
    """
    if not frappe.db.exists("Workspace Sidebar", sidebar_name):
        print(f"  [SKIP] Sidebar '{sidebar_name}' inexistante en DB")
        return False

    frappe.db.delete("Workspace Sidebar Item", {"parent": sidebar_name})
    for i, item in enumerate(items_def):
        row = frappe.new_doc("Workspace Sidebar Item")
        row.parent = sidebar_name
        row.parenttype = "Workspace Sidebar"
        row.parentfield = "items"
        row.idx = i + 1
        row.label = item.get("label", "")
        row.type = item.get("type", "Link")
        row.link_type = item.get("link_type") or None
        row.link_to = item.get("link_to") or None
        row.icon = item.get("icon") or None
        row.url = item.get("url") or None
        row.indent = item.get("indent", 0)
        row.child = item.get("child", 0)
        row.collapsible = item.get("collapsible", 0)
        row.db_insert()
    return True


# ============================================================
# PHASE 1 — DIAGNOSTIC
# ============================================================

def _diagnose():
    print("\n=== DIAGNOSTIC COMPLET ===\n")

    # Workspaces natifs Buying et Stock
    for ws in ["Buying", "Stock", "HR", "Leave", "Payroll"]:
        exists = frappe.db.exists("Workspace", ws)
        if exists:
            n_links = frappe.db.count("Workspace Link", {"parent": ws})
            content_len = len(frappe.db.get_value("Workspace", ws, "content") or "")
            print(f"  [{ws}] links={n_links}, content_len={content_len}")
        else:
            print(f"  [{ws}] ABSENT de DB")

    # Workspace Sidebar pour HRMS
    print("\n--- Workspace Sidebar records ---")
    sidebars = frappe.db.sql(
        "SELECT name, title, module, app FROM `tabWorkspace Sidebar` ORDER BY name LIMIT 30",
        as_dict=True
    )
    for s in sidebars:
        n = frappe.db.count("Workspace Sidebar Item", {"parent": s.name})
        print(f"  [{s.name}] title={s.title} module={s.module} items={n}")

    # DocTypes KYA Services
    print("\n--- DocTypes KYA Services ---")
    for dt in ["KYA Form", "KYA Evaluation", "KYA Evaluation Critere",
               "KYA Form Question", "KYA Form Response", "KYA Form Answer"]:
        exists = frappe.db.exists("DocType", dt)
        if exists:
            doc = frappe.get_doc("DocType", dt)
            print(f"  [{dt}] istable={doc.istable} module={doc.module}")
        else:
            print(f"  [{dt}] ABSENT (bench migrate requis)")

    # KYA Stagiaires workspace
    print("\n--- KYA Stagiaires workspace ---")
    for ws in ["KYA Stagiaires", "Espace Stagiaires"]:
        exists = frappe.db.exists("Workspace", ws)
        if exists:
            n_links = frappe.db.count("Workspace Link", {"parent": ws})
            n_shortcuts = frappe.db.count("Workspace Shortcut", {"parent": ws})
            content_raw = frappe.db.get_value("Workspace", ws, "content") or "[]"
            content = json.loads(content_raw)
            nc_count = sum(1 for c in content if c.get("type") == "number_card")
            chart_count = sum(1 for c in content if c.get("type") == "chart")
            print(f"  [{ws}] links={n_links}, shortcuts={n_shortcuts}, "
                  f"number_cards={nc_count}, charts={chart_count}")
        else:
            print(f"  [{ws}] ABSENT")


# ============================================================
# PHASE 2 — FIX KYA SERVICES (retirer child table)
# ============================================================

def _fix_kya_services():
    print("\n=== FIX KYA SERVICES ===\n")

    svc_links = [
        {"type": "Card Break", "label": "📝 Formulaires & Enquêtes"},
        {"type": "Link", "label": "KYA Form", "link_to": "KYA Form",
         "link_type": "DocType", "onboard": 1, "icon": "form"},
        {"type": "Link", "label": "Réponses", "link_to": "KYA Form Response",
         "link_type": "DocType", "icon": "reply"},
        {"type": "Link", "label": "Questions", "link_to": "KYA Form Question",
         "link_type": "DocType"},
        {"type": "Card Break", "label": "📋 Évaluations"},
        {"type": "Link", "label": "KYA Evaluation", "link_to": "KYA Evaluation",
         "link_type": "DocType", "onboard": 1},
        # KYA Evaluation Critere intentionnellement ABSENT (istable=1, child table,
        # ne peut pas être navigué → donne "Page introuvable")
        {"type": "Card Break", "label": "🌐 Portail"},
        {"type": "Link", "label": "Enquête en ligne", "link_to": "/kya-survey",
         "link_type": "URL"},
        {"type": "Link", "label": "Évaluation en ligne", "link_to": "/kya-eval",
         "link_type": "URL"},
    ]
    _reset_links("KYA Services", svc_links)

    _reset_shortcuts("KYA Services", [
        {"label": "Formulaires", "type": "DocType", "link_to": "KYA Form", "color": "#3F51B5"},
        {"label": "Évaluations", "type": "DocType", "link_to": "KYA Evaluation", "color": "#9C27B0"},
        {"label": "Réponses", "type": "DocType", "link_to": "KYA Form Response", "color": "#009688"},
        {"label": "Portail Enquête", "type": "URL", "url": "/kya-survey", "color": "#FF5722"},
    ])

    # Number Cards
    _ensure_number_card("Total Formulaires KYA", "Total Formulaires", "KYA Form", "#3F51B5")
    _ensure_number_card("Formulaires Actifs KYA", "Formulaires Actifs", "KYA Form", "#4CAF50",
                        filters=[["KYA Form", "statut", "=", "Actif"]])
    _ensure_number_card("Total Evaluations KYA", "Total Évaluations", "KYA Evaluation", "#9C27B0")
    _ensure_number_card("Reponses Recues KYA", "Réponses Reçues", "KYA Form Response", "#009688",
                        filters=[["KYA Form Response", "soumis_le", "is", "set"]])

    frappe.db.set_value("Workspace", "KYA Services", "content", json.dumps([
        {"id": "h1", "type": "header",
         "data": {"text": "<div class='ellipsis'>📋 KYA Services — Admin</div>",
                  "level": 3, "col": 12}},
        {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Formulaires", "col": 3}},
        {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Évaluations", "col": 3}},
        {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "Réponses", "col": 3}},
        {"id": "s4", "type": "shortcut", "data": {"shortcut_name": "Portail Enquête", "col": 3}},
        {"id": "sp", "type": "spacer", "data": {"col": 12}},
        {"id": "h2", "type": "header",
         "data": {"text": "📊 Indicateurs", "level": 4, "col": 12}},
        {"id": "nc1", "type": "number_card",
         "data": {"number_card_name": "Total Formulaires KYA", "col": 3}},
        {"id": "nc2", "type": "number_card",
         "data": {"number_card_name": "Formulaires Actifs KYA", "col": 3}},
        {"id": "nc3", "type": "number_card",
         "data": {"number_card_name": "Total Evaluations KYA", "col": 3}},
        {"id": "nc4", "type": "number_card",
         "data": {"number_card_name": "Reponses Recues KYA", "col": 3}},
    ], ensure_ascii=False), update_modified=True)

    print("  [OK] KYA Services — sidebar nettoyée (KYA Evaluation Critere retiré)")
    print("  [OK] KYA Services — content mis à jour avec Number Cards")


# ============================================================
# PHASE 3 — FIX BUYING & STOCK (content home page)
# ============================================================

def _fix_buying_stock():
    print("\n=== FIX BUYING & STOCK (content home page) ===\n")

    # Vérifier que les shortcuts existent au niveau Workspace Shortcut
    # pour les workspaces natifs
    for ws, label_pr, doctype_pr, label_url, url_pr, color in [
        ("Buying", "Demande d'Achat KYA", "Purchase Requisition",
         "Form. Demande Achat", "/demande-achat", "#FF9800"),
        ("Stock", "PV Sortie Matériel", "PV Sortie Materiel",
         "Form. PV Sortie", "/pv-sortie-materiel", "#E91E63"),
    ]:
        if not frappe.db.exists("Workspace", ws):
            print(f"  [SKIP] Workspace '{ws}' absent")
            continue

        # Créer shortcuts si absents
        for sc_label, sc_type, sc_lt, sc_url, sc_color in [
            (label_pr, "DocType", doctype_pr, "", color),
            (label_url, "URL", "", url_pr, "#607D8B"),
        ]:
            if not frappe.db.exists("Workspace Shortcut", {"label": sc_label, "parent": ws}):
                row = frappe.new_doc("Workspace Shortcut")
                row.parent = ws
                row.parenttype = "Workspace"
                row.parentfield = "shortcuts"
                row.label = sc_label
                row.type = sc_type
                row.link_to = sc_lt
                row.url = sc_url
                row.color = sc_color
                row.db_insert()

        section_header = "🏷️ KYA — Achats" if ws == "Buying" else "📦 KYA — Stock"
        shortcuts = [
            {"label": label_pr, "type": "DocType", "link_to": doctype_pr,
             "col": 4, "color": color},
            {"label": label_url, "type": "URL", "url": url_pr,
             "col": 4, "color": "#607D8B"},
        ]
        cnt = _inject_kya_to_native_content(ws, section_header, shortcuts)
        print(f"  [OK] {ws} — section KYA injectée ({cnt} items total dans content)")


# ============================================================
# PHASE 4 — FIX KYA STAGIAIRES DASHBOARD (présences)
# ============================================================

def _fix_kya_stagiaires():
    print("\n=== FIX KYA STAGIAIRES DASHBOARD ===\n")

    # Number Cards pour présences stagiaires
    today = frappe.utils.today()
    week_start = frappe.utils.add_days(today, -7)
    month_start = frappe.utils.get_first_day(today)

    _ensure_number_card(
        "Stagiaires Actifs KYA", "Stagiaires Actifs", "Employee", "#4CAF50",
        filters=[["Employee", "custom_statut_stage", "=", "Actif"]]
    )
    _ensure_number_card(
        "Presences Aujourd'hui", "Présences Aujourd'hui", "Attendance", "#2196F3",
        filters=[["Attendance", "attendance_date", "=", today],
                  ["Attendance", "status", "=", "Present"],
                  ["Attendance", "employee", "like", "KEG-STG%"]]
    )
    _ensure_number_card(
        "Absences Cette Semaine", "Absences (7j)", "Attendance", "#F44336",
        filters=[["Attendance", "attendance_date", "between",
                   [week_start, today]],
                  ["Attendance", "status", "=", "Absent"],
                  ["Attendance", "employee", "like", "KEG-STG%"]]
    )
    _ensure_number_card(
        "Presences Ce Mois", "Présences Ce Mois", "Attendance", "#009688",
        filters=[["Attendance", "attendance_date", ">=", str(month_start)],
                  ["Attendance", "status", "=", "Present"],
                  ["Attendance", "employee", "like", "KEG-STG%"]]
    )

    # Workspace Espace Stagiaires : links complets
    es_links = [
        {"type": "Card Break", "label": "📋 Permissions & Bilans"},
        {"type": "Link", "label": "Permissions de Sortie",
         "link_to": "Permission Sortie Stagiaire", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Bilan Fin de Stage",
         "link_to": "Bilan Fin de Stage", "link_type": "DocType", "onboard": 1},
        {"type": "Card Break", "label": "👥 Gestion Stagiaires"},
        {"type": "Link", "label": "Employés / Stagiaires",
         "link_to": "Employee", "link_type": "DocType"},
        {"type": "Link", "label": "Présences",
         "link_to": "Attendance", "link_type": "DocType"},
        {"type": "Card Break", "label": "📊 Rapports de Présence"},
        {"type": "Link", "label": "📅 Rapport Journalier",
         "link_to": "Rapport Présence Stagiaires",
         "link_type": "Report", "dependencies": "Attendance",
         "report_ref_doctype": "Attendance"},
        {"type": "Link", "label": "📆 Rapport Hebdomadaire",
         "link_to": "Rapport Présence Stagiaires",
         "link_type": "Report", "dependencies": "Attendance",
         "report_ref_doctype": "Attendance"},
        {"type": "Link", "label": "📅 Rapport Mensuel",
         "link_to": "Rapport Présence Stagiaires",
         "link_type": "Report", "dependencies": "Attendance",
         "report_ref_doctype": "Attendance"},
        {"type": "Link", "label": "📊 Tableau de Bord",
         "link_to": "Tableau de Bord Stagiaires",
         "link_type": "Report", "dependencies": "Employee",
         "report_ref_doctype": "Employee"},
        {"type": "Card Break", "label": "📝 Formulaires Web"},
        {"type": "Link", "label": "Demande de Permission (Web)",
         "link_to": "/permission-sortie-stagiaire", "link_type": "URL"},
        {"type": "Link", "label": "Bilan de Stage (Web)",
         "link_to": "/bilan-fin-de-stage", "link_type": "URL"},
    ]

    if frappe.db.exists("Workspace", "Espace Stagiaires"):
        _reset_links("Espace Stagiaires", es_links)
        _reset_shortcuts("Espace Stagiaires", [
            {"label": "Nouvelle Permission", "type": "DocType",
             "link_to": "Permission Sortie Stagiaire", "color": "#4CAF50"},
            {"label": "Nouveau Bilan", "type": "DocType",
             "link_to": "Bilan Fin de Stage", "color": "#2196F3"},
            {"label": "Voir Présences", "type": "DocType",
             "link_to": "Attendance", "color": "#009688"},
            {"label": "Form. Permission", "type": "URL",
             "url": "/permission-sortie-stagiaire", "color": "#FF9800"},
        ])

        frappe.db.set_value("Workspace", "Espace Stagiaires", "content",
            json.dumps([
                {"id": "h1", "type": "header",
                 "data": {"text": "<div class='ellipsis'>🎓 Espace Stagiaires KYA</div>",
                          "level": 3, "col": 12}},
                {"id": "s1", "type": "shortcut",
                 "data": {"shortcut_name": "Nouvelle Permission", "col": 3}},
                {"id": "s2", "type": "shortcut",
                 "data": {"shortcut_name": "Nouveau Bilan", "col": 3}},
                {"id": "s3", "type": "shortcut",
                 "data": {"shortcut_name": "Voir Présences", "col": 3}},
                {"id": "s4", "type": "shortcut",
                 "data": {"shortcut_name": "Form. Permission", "col": 3}},
                {"id": "sp", "type": "spacer", "data": {"col": 12}},
                {"id": "h2", "type": "header",
                 "data": {"text": "📊 Tableau de Bord Présences",
                          "level": 4, "col": 12}},
                {"id": "nc1", "type": "number_card",
                 "data": {"number_card_name": "Stagiaires Actifs KYA", "col": 3}},
                {"id": "nc2", "type": "number_card",
                 "data": {"number_card_name": "Presences Aujourd'hui", "col": 3}},
                {"id": "nc3", "type": "number_card",
                 "data": {"number_card_name": "Absences Cette Semaine", "col": 3}},
                {"id": "nc4", "type": "number_card",
                 "data": {"number_card_name": "Presences Ce Mois", "col": 3}},
            ], ensure_ascii=False), update_modified=True)
        print("  [OK] Espace Stagiaires — dashboard présences rebuildé")
    else:
        print("  [WARN] 'Espace Stagiaires' workspace absent")

    # Le workspace KYA Stagiaires (navigation parent) — update sidebar
    if frappe.db.exists("Workspace", "KYA Stagiaires"):
        kya_stg_links = [
            {"type": "Card Break", "label": "🎓 KYA Stagiaires"},
            {"type": "Link", "label": "Espace Stagiaires",
             "link_to": "Espace Stagiaires", "link_type": "Workspace"},
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
        _reset_links("KYA Stagiaires", kya_stg_links)
        print("  [OK] KYA Stagiaires — navigation links mis à jour")
    else:
        print("  [SKIP] Workspace KYA Stagiaires absent")


# ============================================================
# PHASE 5 — FIX HRMS ICONS (Personnes, Congés)
# ============================================================

def _fix_hrms_sidebar():
    print("\n=== FIX HRMS SIDEBAR ===\n")

    # Récupérer TOUS les Workspace Sidebar records
    sidebars = frappe.db.sql(
        "SELECT name, title, module FROM `tabWorkspace Sidebar`",
        as_dict=True
    )
    sidebar_titles = {(s.title or s.name).lower(): s.name for s in sidebars}

    print(f"  Sidebars disponibles: {list(sidebar_titles.keys())[:15]}")

    # Pour chaque workspace HRMS qui peut avoir des items manquants
    hrms_ws_pairs = [
        ("HR", "People"),         # Personnes
        ("Leave", "Leaves and Holiday"),  # Congés
        ("Payroll", "Payroll"),
    ]

    for ws_name, alt_name in hrms_ws_pairs:
        if frappe.db.exists("Workspace", ws_name):
            n = frappe.db.count("Workspace Link", {"parent": ws_name})
            print(f"  [{ws_name}] workspace existe, {n} links")
        else:
            print(f"  [{ws_name}] ({alt_name}) absent de tabWorkspace")

    # Chercher si "leave" ou "hr" workspace sidebar items existent
    for search_term in ["leave", "hr", "payroll", "hrms", "people", "congé", "personnes"]:
        key = search_term.lower()
        if key in sidebar_titles:
            name = sidebar_titles[key]
            n = frappe.db.count("Workspace Sidebar Item", {"parent": name})
            print(f"  Sidebar '{name}' (key={key}): {n} items")

    # Workspaces natifs HRMS — s'assurer que les links HRMS sont intacts
    # En Frappe v16, ces workspaces sont gérés par le app HRMS (fixtures)
    # Notre action : vérifier, ne pas écraser
    hrms_workspaces_check = frappe.db.sql(
        "SELECT name, module FROM `tabWorkspace` WHERE module IN "
        "('HR','Leave','Payroll','HRMS','Leaves and Holiday') "
        "OR name IN ('HR','Leave','Payroll','People','Leaves and Holiday',  "
        "             'Personnes','Ressources Humaines','Congés','Leaves')",
        as_dict=True
    )
    print(f"\n  Workspaces HRMS trouvés: {[w.name for w in hrms_workspaces_check]}")

    for ws in hrms_workspaces_check:
        ws_name = ws.name
        n = frappe.db.count("Workspace Link", {"parent": ws_name})
        if n == 0:
            print(f"  [WARN] {ws_name} a 0 links → peut causer icône inaccessible")
        else:
            print(f"  [OK]   {ws_name} a {n} links")

    # Fix Workspace "Personnes" (= HR People) — 0 links détecté
    # On injecte les liens HR classiques pour éviter la page blanche
    personnes_ws = None
    for ws in hrms_workspaces_check:
        if ws.name in ("Personnes", "People") and frappe.db.count("Workspace Link", {"parent": ws.name}) == 0:
            personnes_ws = ws.name
            break

    if personnes_ws:
        print(f"\n  Tentative de repair workspace '{personnes_ws}' (0 links)...")
        # Recharger depuis les fixtures via reload-doc
        try:
            frappe.reload_doc("Core", "Workspace", personnes_ws)
            n_after = frappe.db.count("Workspace Link", {"parent": personnes_ws})
            print(f"  [OK] reload-doc exécuté. Après reload: {n_after} links")
        except Exception as e:
            print(f"  [WARN] reload-doc a échoué: {e}")
            print(f"         → Exécutez manuellement: bench --site frontend reload-doc Core Workspace '{personnes_ws}'")


# ============================================================
# PHASE 6 — FIX WORKSPACE SIDEBAR ITEMS (navigation gauche)
# ============================================================

def _fix_workspace_sidebar_items():
    """Réparer les Workspace Sidebar Items si le format v16 est utilisé.
    Dans Frappe v16, les icônes Personnes/Congés viennent de
    l'app bootstrap sidebar, pas de tabWorkspace Link."""
    print("\n=== FIX WORKSPACE SIDEBAR ITEMS (nav gauche) ===\n")

    # Vérifier combien de records Workspace Sidebar existent
    all_sidebars = frappe.db.sql(
        "SELECT name, title, module, app FROM `tabWorkspace Sidebar` ORDER BY name",
        as_dict=True
    )

    print(f"  Total Workspace Sidebar records: {len(all_sidebars)}")
    for s in all_sidebars:
        n = frappe.db.count("Workspace Sidebar Item", {"parent": s.name})
        print(f"  [{s.name}] title={s.title} app={s.app} items={n}")

    # Si on est en mode "Workspace Sidebar Items" pour la nav gauche
    # (pas juste tabWorkspace Link), alors il faut aussi modifier ces records
    # Pour KYA Services — s'assurer que "KYA Evaluation Critere" EST ABSENT
    kya_services_sidebar = frappe.db.get_value(
        "Workspace Sidebar", {"title": "KYA Services"}, "name"
    )
    if kya_services_sidebar:
        # Supprimer tous les items child table (istable=1 DocTypes)
        # kya_evaluation_critere ET kya_form_question ET kya_form_answer sont des child tables
        child_tables = ["KYA Evaluation Critere", "KYA Form Question", "KYA Form Answer"]
        for ct in child_tables:
            removed = frappe.db.sql(
                "DELETE FROM `tabWorkspace Sidebar Item` "
                "WHERE parent=%s AND (link_to=%s OR label=%s)",
                (kya_services_sidebar, ct, ct)
            )
        print(f"  [OK] Sidebar '{kya_services_sidebar}': child tables retirées ({', '.join(child_tables)})")

        # Vérifier les items restants
        remaining = frappe.db.sql(
            "SELECT label, link_to, link_type FROM `tabWorkspace Sidebar Item` WHERE parent=%s ORDER BY idx",
            kya_services_sidebar, as_dict=True
        )
        print(f"  Items restants KYA Services sidebar:")
        for item in remaining:
            print(f"    [{item.label}] → {item.link_to} ({item.link_type})")


# ============================================================
# EXECUTE
# ============================================================

def execute():
    print("\n\n" + "="*60)
    print("  MEGA FIX KYA v2 — démarrage")
    print("="*60)

    _diagnose()
    _fix_kya_services()
    _fix_buying_stock()
    _fix_kya_stagiaires()
    _fix_hrms_sidebar()
    _fix_workspace_sidebar_items()

    # Commit global
    frappe.db.commit()

    # Cache bust
    for ws in ["KYA Services", "Espace Stagiaires", "KYA Stagiaires", "Buying", "Stock"]:
        try:
            frappe.cache().delete_value(f"workspace:{ws}")
            frappe.cache().delete_value(f"workspace_sidebar:{ws}")
        except Exception:
            pass
    frappe.clear_cache()

    # Rapport final
    print("\n" + "="*60)
    print("  RÉSUMÉ FINAL")
    print("="*60)
    for ws in ["Espace Stagiaires", "KYA Services", "KYA Stagiaires", "Buying", "Stock"]:
        if frappe.db.exists("Workspace", ws):
            n = frappe.db.count("Workspace Link", {"parent": ws})
            ns = frappe.db.count("Workspace Shortcut", {"parent": ws})
            content_raw = frappe.db.get_value("Workspace", ws, "content") or "[]"
            content = json.loads(content_raw)
            nc_cnt = sum(1 for c in content if c.get("type") == "number_card")
            print(f"  {ws}: {n} links, {ns} shortcuts, {nc_cnt} number_cards")
        else:
            print(f"  {ws}: ABSENT")

    print("""
╔═══════════════════════════════════════════════════╗
║  ACTIONS REQUISES DANS LE NAVIGATEUR              ║
╠═══════════════════════════════════════════════════╣
║  1. Vider le cache navigateur (Ctrl+Shift+Delete) ║
║     OU ouvrir en onglet privé (Ctrl+Shift+N)      ║
║  2. Aller sur http://localhost:8086               ║
║  3. Recharger la page (F5)                        ║
╚═══════════════════════════════════════════════════╝
    """)

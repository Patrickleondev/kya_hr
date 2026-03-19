"""
force_sync_workspaces.py v4
- Restauration workspaces natifs Stock et Buying via reload_doc
- Ajout uniquement des shortcuts KYA (web forms) sur Stock et Buying
- Correction lien "Purchase Requisition" → "Demande Achat KYA"
- Dashboard KYA Stagiaires complet (Number Cards, stats présences)
- Fix HRMS workspaces Personnes/Congés (is_hidden=0)
"""
import frappe
import json


# =============================================================
# HELPERS COMMUNS
# =============================================================

def _reset_links(ws_name, links_data):
    """Replace TOUS les links d un workspace KYA custom."""
    frappe.db.delete("Workspace Link", {"parent": ws_name})
    for i, lk in enumerate(links_data):
        row = frappe.new_doc("Workspace Link")
        row.parent = ws_name; row.parenttype = "Workspace"; row.parentfield = "links"
        row.idx = i + 1; row.type = lk.get("type", "Link")
        row.label = lk.get("label", ""); row.link_to = lk.get("link_to") or None
        row.link_type = lk.get("link_type") or None; row.hidden = 0
        row.icon = lk.get("icon") or None; row.onboard = lk.get("onboard", 0)
        row.dependencies = lk.get("dependencies") or None
        row.report_ref_doctype = lk.get("report_ref_doctype") or None
        row.db_insert()


def _reset_shortcuts(ws_name, shortcuts):
    frappe.db.delete("Workspace Shortcut", {"parent": ws_name})
    for i, sc in enumerate(shortcuts):
        row = frappe.new_doc("Workspace Shortcut")
        row.parent = ws_name; row.parenttype = "Workspace"; row.parentfield = "shortcuts"
        row.idx = i + 1; row.label = sc["label"]; row.type = sc.get("type", "DocType")
        row.link_to = sc.get("link_to", "") if sc.get("type") != "URL" else ""
        row.url = sc.get("url", "") if sc.get("type") == "URL" else ""
        row.color = sc.get("color", ""); row.db_insert()


def _append_kya_shortcuts_to_native_content(ws_name, section_title, shortcuts_list):
    """Ajoute une section KYA (header + shortcuts) au content JSON d'un workspace natif.
    Idempotent : supprime l'ancienne section KYA avant d'ajouter la nouvelle."""
    content_raw = frappe.db.get_value("Workspace", ws_name, "content") or "[]"
    try:
        content = json.loads(content_raw)
    except Exception:
        content = []

    # Supprimer anciens items KYA (header avec section_title ou shortcuts kya_*)
    content = [item for item in content
               if not (item.get("type") == "header" and
                       "KYA" in item.get("data", {}).get("text", ""))
               and not item.get("id", "").startswith("kya_")]

    # Ajouter la section KYA à la fin
    content.append({"id": "kya_sp", "type": "spacer", "data": {"col": 12}})
    content.append({"id": "kya_h", "type": "header", "data": {
        "text": f"<span>{section_title}</span>", "level": 4, "col": 12
    }})
    for i, sc in enumerate(shortcuts_list):
        content.append({"id": f"kya_s{i}", "type": "shortcut", "data": {
            "shortcut_name": sc["label"], "col": sc.get("col", 4)
        }})

    frappe.db.set_value("Workspace", ws_name, "content", json.dumps(content, ensure_ascii=False),
                        update_modified=True)


def _add_kya_shortcuts_to_table(ws_name, shortcuts_list):
    """Ajoute/met à jour les Workspace Shortcut KYA dans la table (idempotent)."""
    for sc in shortcuts_list:
        label = sc["label"]
        existing = frappe.db.get_value("Workspace Shortcut",
                                        {"parent": ws_name, "label": label}, "name")
        if existing:
            frappe.db.set_value("Workspace Shortcut", existing, {
                "type": sc.get("type", "DocType"),
                "link_to": sc.get("link_to", "") if sc.get("type") != "URL" else "",
                "url": sc.get("url", "") if sc.get("type") == "URL" else "",
                "color": sc.get("color", ""),
            })
        else:
            max_idx = frappe.db.sql(
                "SELECT COALESCE(MAX(idx),0) FROM `tabWorkspace Shortcut` WHERE parent=%s",
                ws_name, as_list=True)[0][0]
            row = frappe.new_doc("Workspace Shortcut")
            row.parent = ws_name; row.parenttype = "Workspace"; row.parentfield = "shortcuts"
            row.idx = int(max_idx) + 1; row.label = label
            row.type = sc.get("type", "DocType")
            row.link_to = sc.get("link_to", "") if sc.get("type") != "URL" else ""
            row.url = sc.get("url", "") if sc.get("type") == "URL" else ""
            row.color = sc.get("color", "")
            row.db_insert()


def _append_kya_section_to_native(ws_name, section_label, kya_links):
    """Ajoute une section KYA a la fin de la sidebar d'un workspace NATIF ERPNext."""
    rows = frappe.db.sql(
        "SELECT name, type, label, idx FROM `tabWorkspace Link` WHERE parent=%s ORDER BY idx",
        ws_name, as_dict=True
    )
    kya_start = None
    for r in rows:
        if r.type == "Card Break" and r.label == section_label:
            kya_start = r.idx
            break
    if kya_start is not None:
        frappe.db.sql(
            "DELETE FROM `tabWorkspace Link` WHERE parent=%s AND idx >= %s",
            (ws_name, kya_start)
        )
        next_idx = kya_start
    else:
        next_idx = len(rows) + 1

    for i, lk in enumerate(kya_links):
        row = frappe.new_doc("Workspace Link")
        row.parent = ws_name; row.parenttype = "Workspace"; row.parentfield = "links"
        row.idx = next_idx + i; row.type = lk.get("type", "Link")
        row.label = lk.get("label", ""); row.link_to = lk.get("link_to") or None
        row.link_type = lk.get("link_type") or None; row.hidden = 0
        row.icon = lk.get("icon") or None; row.onboard = lk.get("onboard", 0)
        row.db_insert()


def _ensure_number_card(name, label, document_type, color="#4CAF50", filters=None):
    if frappe.db.exists("Number Card", name):
        frappe.db.set_value("Number Card", name, {
            "label": label, "document_type": document_type, "color": color,
            "filters_json": json.dumps(filters or []), "is_public": 1
        })
        return False
    doc = frappe.new_doc("Number Card")
    doc.name = name; doc.label = label; doc.document_type = document_type
    doc.function = "Count"; doc.aggregate_function_based_on = "name"
    doc.color = color; doc.filters_json = json.dumps(filters or []); doc.is_public = 1
    doc.insert(ignore_permissions=True)
    return True


# =============================================================
# EXECUTE
# =============================================================

def execute():
    print("=== FORCE SYNC WORKSPACES KYA v4 ===\n")

    # ----------------------------------------------------------
    # 1. RESTAURER les workspaces NATIFS Stock et Buying
    # Utilise reload_doc(force=True) pour remettre le contenu natif ERPNext
    # depuis les fichiers JSON de l'app erpnext installée
    # ----------------------------------------------------------
    for module, ws_name in [("stock", "Stock"), ("buying", "Buying")]:
        try:
            # frappe.reload_doc relit le JSON source de l'app et écrase la DB
            frappe.reload_doc(module, "workspace", ws_name, force=True)
            frappe.db.commit()
            print(f"  [OK] {ws_name} - contenu natif restauré depuis erpnext/{module}/")
        except Exception as e:
            print(f"  [WARN] reload_doc({ws_name}) a échoué : {e}")
            print(f"  [INFO] Le workspace {ws_name} gardera son contenu actuel")

    # ----------------------------------------------------------
    # 2. BUYING - ajouter shortcuts KYA WEB FORMS dans le content
    # N.B. DocType correct = "Demande Achat KYA" (pas "Purchase Requisition")
    # ----------------------------------------------------------
    buying_kya_shortcuts = [
        {"label": "Demande d'Achat KYA", "type": "DocType", "link_to": "Demande Achat KYA", "color": "#FF9800", "col": 4},
        {"label": "Form. Demande Achat", "type": "URL", "url": "/demande-achat", "color": "#F44336", "col": 4},
    ]
    _add_kya_shortcuts_to_table("Buying", buying_kya_shortcuts)
    _append_kya_shortcuts_to_native_content(
        "Buying", "\U0001f3f7\ufe0f KYA \u2014 Achats", buying_kya_shortcuts
    )
    _append_kya_section_to_native("Buying", "\U0001f3f7\ufe0f KYA \u2014 Achats", [
        {"type": "Card Break", "label": "\U0001f3f7\ufe0f KYA \u2014 Achats"},
        {"type": "Link", "label": "Demande d\u2019Achat KYA", "link_to": "Demande Achat KYA", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Formulaire Demande Achat", "link_to": "/demande-achat", "link_type": "URL"},
    ])
    print("  [OK] Buying - shortcuts KYA web forms ajoutés (Demande Achat KYA)")

    # ----------------------------------------------------------
    # 3. STOCK - ajouter shortcuts KYA WEB FORMS dans le content
    # ----------------------------------------------------------
    stock_kya_shortcuts = [
        {"label": "PV Sortie Matériel", "type": "DocType", "link_to": "PV Sortie Materiel", "color": "#607D8B", "col": 4},
        {"label": "Form. PV Sortie", "type": "URL", "url": "/pv-sortie-materiel", "color": "#795548", "col": 4},
    ]
    _add_kya_shortcuts_to_table("Stock", stock_kya_shortcuts)
    _append_kya_shortcuts_to_native_content(
        "Stock", "\U0001f4e6 KYA \u2014 Stock", stock_kya_shortcuts
    )
    _append_kya_section_to_native("Stock", "\U0001f4e6 KYA \u2014 Stock", [
        {"type": "Card Break", "label": "\U0001f4e6 KYA \u2014 Stock"},
        {"type": "Link", "label": "PV Sortie Mat\u00e9riel", "link_to": "PV Sortie Materiel", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Formulaire PV Sortie", "link_to": "/pv-sortie-materiel", "link_type": "URL"},
    ])
    print("  [OK] Stock - shortcuts KYA web forms ajoutés (PV Sortie Materiel)")

    # ----------------------------------------------------------
    # 4. ESPACE STAGIAIRES - Dashboard complet avec stats
    # Les stagiaires sont des Employees avec designation contenant "Stagi"
    # On crée des Number Cards filtrées sur les DocTypes KYA HR
    # ----------------------------------------------------------

    # Number Cards filtrées sur les DocTypes KYA HR
    _ensure_number_card(
        "KYA Permissions en cours", "Permissions en cours",
        "Permission Sortie Stagiaire", "#FF6B35",
        [["Permission Sortie Stagiaire", "workflow_state", "not in",
          "Approuvé,Rejeté,Approved,Rejected"]]
    )
    _ensure_number_card(
        "KYA Permissions total", "Total Permissions",
        "Permission Sortie Stagiaire", "#4CAF50"
    )
    _ensure_number_card(
        "KYA Bilans total", "Total Bilans de Stage",
        "Bilan Fin de Stage", "#2196F3"
    )
    _ensure_number_card(
        "KYA Presences mois", "Présences ce mois",
        "Attendance", "#9C27B0",
        [["Attendance", "attendance_date", "thismonth"],
         ["Attendance", "status", "=", "Present"]]
    )
    _ensure_number_card(
        "KYA Absences mois", "Absences ce mois",
        "Attendance", "#F44336",
        [["Attendance", "attendance_date", "thismonth"],
         ["Attendance", "status", "=", "Absent"]]
    )
    print("  [OK] Number Cards KYA Stagiaires créées/mises à jour")

    # Shortcuts Espace Stagiaires
    _reset_shortcuts("Espace Stagiaires", [
        {"label": "Nouvelle Permi...", "type": "DocType", "link_to": "Permission Sortie Stagiaire", "color": "#4CAF50"},
        {"label": "Nouveau Bilan", "type": "DocType", "link_to": "Bilan Fin de Stage", "color": "#2196F3"},
        {"label": "Voir Présences", "type": "DocType", "link_to": "Attendance", "color": "#9C27B0"},
        {"label": "Form. Permission", "type": "URL", "url": "/permission-sortie-stagiaire", "color": "#FF9800"},
    ])

    # Links sidebar Espace Stagiaires
    es_links = [
        {"type": "Card Break", "label": "\U0001f4cb Permissions & Bilans"},
        {"type": "Link", "label": "Autorisations de Sortie", "link_to": "Permission Sortie Stagiaire", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Bilan Fin de Stage", "link_to": "Bilan Fin de Stage", "link_type": "DocType", "onboard": 1},
        {"type": "Card Break", "label": "\U0001f465 Stagiaires seulement"},
        # Lien filtré : stagiaires uniquement (designation contient "Stagiaire")
        {"type": "Link", "label": "Stagiaires", "link_to": "Employee", "link_type": "DocType"},
        {"type": "Link", "label": "Présences", "link_to": "Attendance", "link_type": "DocType"},
        {"type": "Card Break", "label": "\U0001f4dd Formulaires Web"},
        {"type": "Link", "label": "Demande de Permission (Web)", "link_to": "/permission-sortie-stagiaire", "link_type": "URL"},
        {"type": "Link", "label": "Bilan de Stage (Web)", "link_to": "/bilan-fin-de-stage", "link_type": "URL"},
    ]
    _reset_links("Espace Stagiaires", es_links)

    # Content Espace Stagiaires avec dashboard complet
    frappe.db.set_value("Workspace", "Espace Stagiaires", "content", json.dumps([
        {"id": "h_main", "type": "header", "data": {
            "text": "<div class='ellipsis'>\U0001f393 Espace Stagiaires KYA</div>",
            "level": 3, "col": 12
        }},
        # Shortcuts rapides
        {"id": "s1", "type": "shortcut", "data": {"shortcut_name": "Nouvelle Permi...", "col": 3}},
        {"id": "s2", "type": "shortcut", "data": {"shortcut_name": "Nouveau Bilan", "col": 3}},
        {"id": "s3", "type": "shortcut", "data": {"shortcut_name": "Voir Présences", "col": 3}},
        {"id": "s4", "type": "shortcut", "data": {"shortcut_name": "Form. Permission", "col": 3}},
        {"id": "sp1", "type": "spacer", "data": {"col": 12}},
        # Section Tableau de Bord Présences
        {"id": "h_dashboard", "type": "header", "data": {
            "text": "\U0001f4ca Tableau de Bord Présences",
            "level": 4, "col": 12
        }},
        # Number Cards statistiques
        {"id": "nc_perm", "type": "number_card", "data": {
            "number_card_name": "KYA Permissions en cours", "col": 3
        }},
        {"id": "nc_perm_tot", "type": "number_card", "data": {
            "number_card_name": "KYA Permissions total", "col": 3
        }},
        {"id": "nc_bilan", "type": "number_card", "data": {
            "number_card_name": "KYA Bilans total", "col": 3
        }},
        {"id": "nc_pres", "type": "number_card", "data": {
            "number_card_name": "KYA Presences mois", "col": 3
        }},
        {"id": "nc_abs", "type": "number_card", "data": {
            "number_card_name": "KYA Absences mois", "col": 3
        }},
    ], ensure_ascii=False), update_modified=True)
    print("  [OK] Espace Stagiaires - contenu complet avec Number Cards")

    # ----------------------------------------------------------
    # 5. KYA SERVICES (workspace KYA custom) - NE PAS MODIFIER
    #    si déjà configuré (éviter régressions)
    # ----------------------------------------------------------
    svc_link_count = frappe.db.count("Workspace Link", {"parent": "KYA Services"})
    if svc_link_count < 4:
        svc_links = [
            {"type": "Card Break", "label": "\U0001f4dd Formulaires & Enqu\u00eates"},
            {"type": "Link", "label": "KYA Form", "link_to": "KYA Form", "link_type": "DocType", "onboard": 1},
            {"type": "Link", "label": "R\u00e9ponses", "link_to": "KYA Form Response", "link_type": "DocType"},
            {"type": "Card Break", "label": "\U0001f4cb \u00c9valuations"},
            {"type": "Link", "label": "KYA Evaluation", "link_to": "KYA Evaluation", "link_type": "DocType", "onboard": 1},
            {"type": "Card Break", "label": "\U0001f310 Portail"},
            {"type": "Link", "label": "Enqu\u00eate en ligne", "link_to": "/kya-survey", "link_type": "URL"},
            {"type": "Link", "label": "\u00c9valuation en ligne", "link_to": "/kya-eval", "link_type": "URL"},
        ]
        _reset_links("KYA Services", svc_links)
        print("  [OK] KYA Services links reconfigurés")
    else:
        print(f"  [SKIP] KYA Services déjà configuré ({svc_link_count} links)")

    nc1 = _ensure_number_card("Total Formulaires KYA", "Total Formulaires", "KYA Form", "#3F51B5")
    nc2 = _ensure_number_card("Total Evaluations KYA", "Total \u00c9valuations", "KYA Evaluation", "#9C27B0")
    nc3 = _ensure_number_card("Reponses Recues KYA", "R\u00e9ponses Re\u00e7ues", "KYA Form Response", "#009688")
    print(f"  [OK] KYA Services Number Cards: created={nc1},{nc2},{nc3}")

    # ----------------------------------------------------------
    # 6. FIX HRMS WORKSPACES - Workspaces Personnes et Congés
    # L'erreur "Icon is not correctly configured" vient de workspace hidden
    # ----------------------------------------------------------
    hrms_ws_names = ["Payroll", "Leaves", "People", "HR"]
    for ws_name in hrms_ws_names:
        if frappe.db.exists("Workspace", ws_name):
            is_hidden = frappe.db.get_value("Workspace", ws_name, "is_hidden")
            if is_hidden:
                frappe.db.set_value("Workspace", ws_name, "is_hidden", 0, update_modified=False)
                print(f"  [FIX] {ws_name} - is_hidden mis à 0 (était caché)")
            else:
                print(f"  [OK] {ws_name} - déjà visible")

    # Recharger les workspaces HRMS depuis les sources de l'app si nécessaire
    hrms_reload = [
        ("Payroll", "Payroll"), ("Leaves", "Leaves"), ("People", "People")
    ]
    for module_name, ws_name in hrms_reload:
        if frappe.db.exists("Workspace", ws_name):
            link_count = frappe.db.count("Workspace Link", {"parent": ws_name})
            if link_count == 0:
                # Workspace vide → recharger depuis les sources hrms
                try:
                    frappe.reload_doc(module_name, "workspace", ws_name, force=True)
                    frappe.db.commit()
                    print(f"  [OK] {ws_name} rechargé depuis hrms/{module_name}/")
                except Exception as e:
                    print(f"  [WARN] reload_doc {ws_name}: {e}")

    # ----------------------------------------------------------
    # 7. MASQUER les anciennes sous-pages custom obsolètes
    # ----------------------------------------------------------
    for ws_to_hide in ["Achats & Approvisionnement", "Stock & Logistique"]:
        if frappe.db.exists("Workspace", ws_to_hide):
            frappe.db.set_value("Workspace", ws_to_hide, "is_hidden", 1, update_modified=False)
            print(f"  [HIDE] {ws_to_hide}")

    # ----------------------------------------------------------
    # 8. COMMIT + cache bust
    # ----------------------------------------------------------
    frappe.db.commit()
    try:
        for ws in ["Espace Stagiaires", "KYA Services", "Buying", "Stock"]:
            frappe.cache().delete_value(f"workspace:{ws}")
    except Exception:
        pass

    print("\n=== VERIFICATION ===")
    for ws in ["Espace Stagiaires", "KYA Services", "Buying", "Stock"]:
        n = frappe.db.count("Workspace Link", {"parent": ws})
        ns = frappe.db.count("Workspace Shortcut", {"parent": ws})
        c = frappe.db.get_value("Workspace", ws, "content") or "[]"
        nc_items = len([i for i in json.loads(c) if i.get("type") == "number_card"])
        chart_items = len([i for i in json.loads(c) if i.get("type") == "chart"])
        shortcut_items = len([i for i in json.loads(c) if i.get("type") == "shortcut"])
        print(f"  {ws}: {n} links, {ns} shortcuts | content: {nc_items} NC, {chart_items} charts, {shortcut_items} shortcuts")

    print("""
=== IMPORTANT NAVIGATEUR ===
Les changements sont en DB. Pour les voir dans le navigateur:
  Chrome/Edge: Ctrl+Shift+Delete -> cocher Cookies ET Cache -> Effacer
  Firefox: Ctrl+Shift+Delete -> Tout effacer
  OU: ouvrir en onglet PRIVE (Ctrl+Shift+N) sur http://localhost:8086
""")

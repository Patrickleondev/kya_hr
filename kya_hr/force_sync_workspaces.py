"""
force_sync_workspaces.py v3
- Workspaces propres KYA : Espace Stagiaires, KYA Services
- Workspaces natifs augmentes : Buying (Achats), Stock
- Cache bust localStorage via JS flag
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


def _append_kya_section_to_native(ws_name, section_label, kya_links):
    """Ajoute une section KYA a la fin d un workspace NATIF ERPNext.
    Si la section existait (d un precedent execute), la remplace proprement.
    Ne touche JAMAIS aux liens natifs ERPNext existants."""
    rows = frappe.db.sql(
        "SELECT name, type, label, idx FROM `tabWorkspace Link` WHERE parent=%s ORDER BY idx",
        ws_name, as_dict=True
    )
    # Supprimer l ancienne section KYA si presente
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
    print("=== FORCE SYNC WORKSPACES KYA v3 ===\n")

    # ----------------------------------------------------------
    # 1. ESPACE STAGIAIRES (workspace KYA custom)
    # ----------------------------------------------------------
    es_links = [
        {"type": "Card Break", "label": "\U0001f4cb Permissions & Bilans"},
        {"type": "Link", "label": "Permissions de Sortie", "link_to": "Permission Sortie Stagiaire", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Bilan Fin de Stage", "link_to": "Bilan Fin de Stage", "link_type": "DocType", "onboard": 1},
        {"type": "Card Break", "label": "\U0001f465 Gestion Stagiaires"},
        {"type": "Link", "label": "Employes / Stagiaires", "link_to": "Employee", "link_type": "DocType"},
        {"type": "Link", "label": "Presences", "link_to": "Attendance", "link_type": "DocType"},
        {"type": "Card Break", "label": "\U0001f4dd Formulaires Web"},
        {"type": "Link", "label": "Demande de Permission (Web)", "link_to": "/permission-sortie-stagiaire", "link_type": "URL"},
        {"type": "Link", "label": "Bilan de Stage (Web)", "link_to": "/bilan-fin-de-stage", "link_type": "URL"},
        {"type": "Card Break", "label": "\U0001f4ca Rapports"},
        {"type": "Link", "label": "Tableau de Bord Stagiaires", "link_to": "Tableau de Bord Stagiaires", "link_type": "Report", "dependencies": "Employee", "report_ref_doctype": "Employee"},
        {"type": "Link", "label": "Rapport Presence Stagiaires", "link_to": "Rapport Pr\u00e9sence Stagiaires", "link_type": "Report", "dependencies": "Attendance", "report_ref_doctype": "Attendance"},
    ]
    _reset_links("Espace Stagiaires", es_links)
    _reset_shortcuts("Espace Stagiaires", [
        {"label": "Nouvelle Permission", "type": "DocType", "link_to": "Permission Sortie Stagiaire", "color": "#4CAF50"},
        {"label": "Nouveau Bilan", "type": "DocType", "link_to": "Bilan Fin de Stage", "color": "#2196F3"},
        {"label": "Form. Permission", "type": "URL", "url": "/permission-sortie-stagiaire", "color": "#FF9800"},
    ])
    frappe.db.set_value("Workspace", "Espace Stagiaires", "content", json.dumps([
        {"id":"h1","type":"header","data":{"text":"<div class='ellipsis'>\U0001f393 Espace Stagiaires KYA</div>","level":3,"col":12}},
        {"id":"s1","type":"shortcut","data":{"shortcut_name":"Nouvelle Permission","col":4}},
        {"id":"s2","type":"shortcut","data":{"shortcut_name":"Nouveau Bilan","col":4}},
        {"id":"s3","type":"shortcut","data":{"shortcut_name":"Form. Permission","col":4}},
    ], ensure_ascii=False), update_modified=True)
    print("  [OK] Espace Stagiaires (custom)")

    # ----------------------------------------------------------
    # 2. KYA SERVICES (workspace KYA custom)
    # ----------------------------------------------------------
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
    _reset_shortcuts("KYA Services", [
        {"label": "Formulaires", "type": "DocType", "link_to": "KYA Form", "color": "#3F51B5"},
        {"label": "\u00c9valuations", "type": "DocType", "link_to": "KYA Evaluation", "color": "#9C27B0"},
        {"label": "R\u00e9ponses", "type": "DocType", "link_to": "KYA Form Response", "color": "#009688"},
        {"label": "Portail Enqu\u00eate", "type": "URL", "url": "/kya-survey", "color": "#FF5722"},
    ])
    nc1 = _ensure_number_card("Total Formulaires KYA", "Total Formulaires", "KYA Form", "#3F51B5")
    nc2 = _ensure_number_card("Total Evaluations KYA", "Total \u00c9valuations", "KYA Evaluation", "#9C27B0")
    nc3 = _ensure_number_card("Reponses Recues KYA", "R\u00e9ponses Re\u00e7ues", "KYA Form Response", "#009688")
    fa = "Formulaires Actifs" if frappe.db.exists("Number Card", "Formulaires Actifs") else "Total Formulaires KYA"
    frappe.db.set_value("Workspace", "KYA Services", "content", json.dumps([
        {"id":"h1","type":"header","data":{"text":"<div class='ellipsis'>\U0001f4cb KYA Services</div>","level":3,"col":12}},
        {"id":"s1","type":"shortcut","data":{"shortcut_name":"Formulaires","col":3}},
        {"id":"s2","type":"shortcut","data":{"shortcut_name":"\u00c9valuations","col":3}},
        {"id":"s3","type":"shortcut","data":{"shortcut_name":"R\u00e9ponses","col":3}},
        {"id":"s4","type":"shortcut","data":{"shortcut_name":"Portail Enqu\u00eate","col":3}},
        {"id":"sp","type":"spacer","data":{"col":12}},
        {"id":"h2","type":"header","data":{"text":"\U0001f4ca Indicateurs","level":4,"col":12}},
        {"id":"nc1","type":"number_card","data":{"number_card_name":fa,"col":3}},
        {"id":"nc2","type":"number_card","data":{"number_card_name":"Total Formulaires KYA","col":3}},
        {"id":"nc3","type":"number_card","data":{"number_card_name":"Total Evaluations KYA","col":3}},
        {"id":"nc4","type":"number_card","data":{"number_card_name":"Reponses Recues KYA","col":3}},
    ], ensure_ascii=False), update_modified=True)
    print(f"  [OK] KYA Services (custom) | Number Cards: {nc1},{nc2},{nc3}")

    # ----------------------------------------------------------
    # 3. BUYING (workspace NATIF) - ajouter section KYA
    # ----------------------------------------------------------
    buying_kya = [
        {"type": "Card Break", "label": "\U0001f3f7\ufe0f KYA \u2014 Achats"},
        {"type": "Link", "label": "Demandes d\u2019Achat (KYA)", "link_to": "Purchase Requisition", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Formulaire Demande Achat", "link_to": "/demande-achat", "link_type": "URL"},
    ]
    _append_kya_section_to_native("Buying", "\U0001f3f7\ufe0f KYA \u2014 Achats", buying_kya)
    print("  [OK] Buying (natif) - section KYA ajoutee")

    # ----------------------------------------------------------
    # 4. STOCK (workspace NATIF) - ajouter section KYA
    # ----------------------------------------------------------
    stock_kya = [
        {"type": "Card Break", "label": "\U0001f4e6 KYA \u2014 Stock"},
        {"type": "Link", "label": "PV Sortie Mat\u00e9riel", "link_to": "PV Sortie Materiel", "link_type": "DocType", "onboard": 1},
        {"type": "Link", "label": "Formulaire PV Sortie", "link_to": "/pv-sortie-materiel", "link_type": "URL"},
    ]
    _append_kya_section_to_native("Stock", "\U0001f4e6 KYA \u2014 Stock", stock_kya)
    print("  [OK] Stock (natif) - section KYA ajoutee")

    # ----------------------------------------------------------
    # 5. MASQUER les anciennes sous-pages custom (plus necessaires)
    # ----------------------------------------------------------
    for ws_to_hide in ["Achats & Approvisionnement", "Stock & Logistique"]:
        if frappe.db.exists("Workspace", ws_to_hide):
            frappe.db.set_value("Workspace", ws_to_hide, "is_hidden", 1, update_modified=False)
            print(f"  [HIDE] {ws_to_hide}")

    # ----------------------------------------------------------
    # 6. COMMIT + cache bust
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
        print(f"  {ws}: {n} links, {ns} shortcuts")

    print("""
=== IMPORTANT NAVIGATEUR ===
Les changements sont en DB. Pour les voir dans le navigateur:
  Chrome/Edge: Ctrl+Shift+Delete -> cocher Cookies ET Cache -> Effacer
  Firefox: Ctrl+Shift+Delete -> Tout effacer
  OU: ouvrir en onglet PRIVE (Ctrl+Shift+N) sur http://localhost:8086
""")

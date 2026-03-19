"""
Fix complet des workspaces KYA:
1. Reset Workspace Links (sidebar)
2. Reset Workspace Shortcuts (tuiles page principale)
3. Reset content JSON (page principale)
4. Creer les Number Cards manquants pour KYA Services
"""
import frappe
import json


def _reset_links(ws_name, links_data):
    frappe.db.delete("Workspace Link", {"parent": ws_name})
    frappe.db.delete("Workspace Shortcut", {"parent": ws_name})
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
        row.hidden = lk.get("hidden", 0)
        row.icon = lk.get("icon") or None
        row.is_query_report = lk.get("is_query_report", 0)
        row.link_count = lk.get("link_count", 0)
        row.onboard = lk.get("onboard", 0)
        row.dependencies = lk.get("dependencies") or None
        row.report_ref_doctype = lk.get("report_ref_doctype") or None
        row.db_insert()


def _insert_shortcut(ws_name, idx, label, sc_type, link_to, color="", url=""):
    row = frappe.new_doc("Workspace Shortcut")
    row.parent = ws_name
    row.parenttype = "Workspace"
    row.parentfield = "shortcuts"
    row.idx = idx
    row.label = label
    row.type = sc_type
    row.link_to = link_to if sc_type != "URL" else ""
    row.url = url if sc_type == "URL" else ""
    row.color = color
    row.db_insert()


def _ensure_number_card(name, label, document_type, color="#4CAF50"):
    if frappe.db.exists("Number Card", name):
        return False
    doc = frappe.new_doc("Number Card")
    doc.name = name
    doc.label = label
    doc.document_type = document_type
    doc.function = "Count"
    doc.aggregate_function_based_on = "name"
    doc.color = color
    doc.filters_json = "[]"
    doc.is_public = 1
    doc.insert(ignore_permissions=True)
    return True


def execute():
    print("=== FORCE SYNC WORKSPACES KYA ===")

    # ----------------------------------------------------------------
    # 1. ESPACE STAGIAIRES
    # ----------------------------------------------------------------
    es_links = [
        {"type": "Card Break", "label": "\U0001f4cb Listes & Suivi"},
        {"type": "Link", "label": "Permissions de Sortie", "link_to": "Permission Sortie Stagiaire", "link_type": "DocType", "onboard": 1, "icon": "file"},
        {"type": "Link", "label": "Bilan Fin de Stage", "link_to": "Bilan Fin de Stage", "link_type": "DocType", "onboard": 1, "icon": "graduation-cap"},
        {"type": "Link", "label": "Liste des Stagiaires", "link_to": "Employee", "link_type": "DocType", "icon": "users"},
        {"type": "Card Break", "label": "\U0001f4dd Formulaires Web"},
        {"type": "Link", "label": "Demander une Permission", "link_to": "/permission-sortie-stagiaire", "link_type": "URL", "icon": "external-link"},
        {"type": "Link", "label": "Bilan de Stage (Web Form)", "link_to": "/bilan-fin-de-stage", "link_type": "URL", "icon": "external-link"},
        {"type": "Card Break", "label": "\U0001f4ca Suivi RH"},
        {"type": "Link", "label": "Pr\u00e9sences", "link_to": "Attendance", "link_type": "DocType", "icon": "clock"},
        {"type": "Link", "label": "Tableau de Bord Stagiaires", "link_to": "Tableau de Bord Stagiaires", "link_type": "Report", "dependencies": "Employee", "report_ref_doctype": "Employee"},
        {"type": "Link", "label": "Rapport Pr\u00e9sence Stagiaires", "link_to": "Rapport Pr\u00e9sence Stagiaires", "link_type": "Report", "dependencies": "Attendance", "report_ref_doctype": "Attendance"},
        {"type": "Link", "label": "Fiche Gestion Cong\u00e9s", "link_to": "Fiche Gestion Conges", "link_type": "Report", "dependencies": "Leave Application", "report_ref_doctype": "Leave Application"},
    ]
    _reset_links("Espace Stagiaires", es_links)
    _insert_shortcut("Espace Stagiaires", 1, "Nouvelle Permission", "DocType", "Permission Sortie Stagiaire", "#4CAF50")
    _insert_shortcut("Espace Stagiaires", 2, "Nouveau Bilan", "DocType", "Bilan Fin de Stage", "#2196F3")
    _insert_shortcut("Espace Stagiaires", 3, "Form. Permission", "URL", "", "#FF9800", url="/permission-sortie-stagiaire")
    frappe.db.set_value("Workspace", "Espace Stagiaires", "content", json.dumps([
        {"id":"hero","type":"header","data":{"text":"<div class='ellipsis'>\U0001f393 Espace Stagiaires KYA</div>","level":3,"col":12}},
        {"id":"s1","type":"shortcut","data":{"shortcut_name":"Nouvelle Permission","col":4}},
        {"id":"s2","type":"shortcut","data":{"shortcut_name":"Nouveau Bilan","col":4}},
        {"id":"s3","type":"shortcut","data":{"shortcut_name":"Form. Permission","col":4}},
    ], ensure_ascii=False), update_modified=True)
    print("  SYNCED: Espace Stagiaires")

    # ----------------------------------------------------------------
    # 2. KYA SERVICES
    # ----------------------------------------------------------------
    svc_links = [
        {"type": "Card Break", "label": "\U0001f4dd Formulaires & Enqu\u00eates"},
        {"type": "Link", "label": "KYA Form", "link_to": "KYA Form", "link_type": "DocType", "onboard": 1, "icon": "file-text"},
        {"type": "Link", "label": "R\u00e9ponses", "link_to": "KYA Form Response", "link_type": "DocType", "icon": "check-square"},
        {"type": "Card Break", "label": "\U0001f4cb \u00c9valuations"},
        {"type": "Link", "label": "KYA Evaluation", "link_to": "KYA Evaluation", "link_type": "DocType", "onboard": 1, "icon": "star"},
        {"type": "Card Break", "label": "\U0001f310 Pages Portail"},
        {"type": "Link", "label": "Enqu\u00eate de Satisfaction", "link_to": "/kya-survey", "link_type": "URL", "icon": "external-link"},
        {"type": "Link", "label": "\u00c9valuation en ligne", "link_to": "/kya-eval", "link_type": "URL", "icon": "external-link"},
    ]
    _reset_links("KYA Services", svc_links)
    _insert_shortcut("KYA Services", 1, "Formulaires", "DocType", "KYA Form", "#3F51B5")
    _insert_shortcut("KYA Services", 2, "\u00c9valuations", "DocType", "KYA Evaluation", "#9C27B0")
    _insert_shortcut("KYA Services", 3, "R\u00e9ponses", "DocType", "KYA Form Response", "#009688")
    _insert_shortcut("KYA Services", 4, "Portail Enqu\u00eate", "URL", "", "#FF5722", url="/kya-survey")

    # Number Cards manquants
    nc_total = _ensure_number_card("Total Formulaires KYA", "Total Formulaires", "KYA Form", "#3F51B5")
    nc_eval = _ensure_number_card("Total Evaluations KYA", "Total \u00c9valuations", "KYA Evaluation", "#9C27B0")
    nc_resp = _ensure_number_card("Reponses Recues KYA", "R\u00e9ponses Re\u00e7ues", "KYA Form Response", "#009688")
    print(f"  Number Cards crees: Total={nc_total}, Eval={nc_eval}, Resp={nc_resp}")

    fa_exists = frappe.db.exists("Number Card", "Formulaires Actifs")
    nc1 = "Formulaires Actifs" if fa_exists else "Total Formulaires KYA"
    frappe.db.set_value("Workspace", "KYA Services", "content", json.dumps([
        {"id":"hero","type":"header","data":{"text":"<div class='ellipsis'>\U0001f4cb KYA Services \u2014 Enqu\u00eates & \u00c9valuations</div>","level":3,"col":12}},
        {"id":"s1","type":"shortcut","data":{"shortcut_name":"Formulaires","col":3}},
        {"id":"s2","type":"shortcut","data":{"shortcut_name":"\u00c9valuations","col":3}},
        {"id":"s3","type":"shortcut","data":{"shortcut_name":"R\u00e9ponses","col":3}},
        {"id":"s4","type":"shortcut","data":{"shortcut_name":"Portail Enqu\u00eate","col":3}},
        {"id":"sp1","type":"spacer","data":{"col":12}},
        {"id":"nc_h","type":"header","data":{"text":"\U0001f4ca Indicateurs","level":4,"col":12}},
        {"id":"nc1","type":"number_card","data":{"number_card_name":nc1,"col":3}},
        {"id":"nc2","type":"number_card","data":{"number_card_name":"Total Formulaires KYA","col":3}},
        {"id":"nc3","type":"number_card","data":{"number_card_name":"Total Evaluations KYA","col":3}},
        {"id":"nc4","type":"number_card","data":{"number_card_name":"Reponses Recues KYA","col":3}},
    ], ensure_ascii=False), update_modified=True)
    print("  SYNCED: KYA Services")

    # ----------------------------------------------------------------
    # 3. ACHATS & APPROVISIONNEMENT
    # ----------------------------------------------------------------
    achats_links = [
        {"type": "Card Break", "label": "\U0001f6cd Achats KYA"},
        {"type": "Link", "label": "Demandes d\u2019Achat", "link_to": "Demande Achat KYA", "link_type": "DocType", "onboard": 1, "icon": "shopping-cart"},
        {"type": "Card Break", "label": "\U0001f4dd Formulaires Web"},
        {"type": "Link", "label": "Formulaire Demande d\u2019Achat", "link_to": "/demande-achat", "link_type": "URL", "icon": "external-link"},
    ]
    _reset_links("Achats & Approvisionnement", achats_links)
    _insert_shortcut("Achats & Approvisionnement", 1, "Nouvelle Demande", "DocType", "Demande Achat KYA", "#FF5722")
    _insert_shortcut("Achats & Approvisionnement", 2, "Form. Achat (Web)", "URL", "", "#795548", url="/demande-achat")
    frappe.db.set_value("Workspace", "Achats & Approvisionnement", "content", json.dumps([
        {"id":"hero","type":"header","data":{"text":"<div class='ellipsis'>\U0001f6cd Achats & Approvisionnement KYA</div>","level":3,"col":12}},
        {"id":"s1","type":"shortcut","data":{"shortcut_name":"Nouvelle Demande","col":6}},
        {"id":"s2","type":"shortcut","data":{"shortcut_name":"Form. Achat (Web)","col":6}},
    ], ensure_ascii=False), update_modified=True)
    print("  SYNCED: Achats & Approvisionnement")

    # ----------------------------------------------------------------
    # 4. STOCK & LOGISTIQUE
    # ----------------------------------------------------------------
    stock_links = [
        {"type": "Card Break", "label": "\U0001f4e6 Stock KYA"},
        {"type": "Link", "label": "PV Sortie Mat\u00e9riel", "link_to": "PV Sortie Materiel", "link_type": "DocType", "onboard": 1, "icon": "package"},
        {"type": "Card Break", "label": "\U0001f4dd Formulaires Web"},
        {"type": "Link", "label": "Formulaire PV Sortie", "link_to": "/pv-sortie-materiel", "link_type": "URL", "icon": "external-link"},
    ]
    _reset_links("Stock & Logistique", stock_links)
    _insert_shortcut("Stock & Logistique", 1, "Nouveau PV Sortie", "DocType", "PV Sortie Materiel", "#607D8B")
    _insert_shortcut("Stock & Logistique", 2, "Form. PV (Web)", "URL", "", "#78909C", url="/pv-sortie-materiel")
    frappe.db.set_value("Workspace", "Stock & Logistique", "content", json.dumps([
        {"id":"hero","type":"header","data":{"text":"<div class='ellipsis'>\U0001f4e6 Stock & Logistique KYA</div>","level":3,"col":12}},
        {"id":"s1","type":"shortcut","data":{"shortcut_name":"Nouveau PV Sortie","col":6}},
        {"id":"s2","type":"shortcut","data":{"shortcut_name":"Form. PV (Web)","col":6}},
    ], ensure_ascii=False), update_modified=True)
    print("  SYNCED: Stock & Logistique")

    # ----------------------------------------------------------------
    # 5. COMMIT + flush cache
    # ----------------------------------------------------------------
    frappe.db.commit()
    for ws in ["Espace Stagiaires", "KYA Services",
               "Achats & Approvisionnement", "Stock & Logistique"]:
        try:
            frappe.cache().delete_value(f"workspace:{ws}")
            frappe.cache().delete_key(f"workspace:{ws}")
        except Exception:
            pass

    print("\n=== VERIFICATION ===")
    for ws in ["Espace Stagiaires", "KYA Services",
               "Achats & Approvisionnement", "Stock & Logistique"]:
        n_links = frappe.db.count("Workspace Link", {"parent": ws})
        n_sc = frappe.db.count("Workspace Shortcut", {"parent": ws})
        print(f"  {ws}: {n_links} links, {n_sc} shortcuts")

    print("\nACTION REQUISE: Ctrl+Shift+Delete dans Chrome -> vider le cache navigateur")

"""
fix_workspace_final.py
- Ajoute les charts et Number Cards natifs dans le content de Stock et Buying
- Corrige l'icône manquante du workspace "Congés & Permissions"
- Met à jour Espace Stagiaires avec les vrais charts KYA existants
- Corrige les Number Cards stagiaires (filtre designation LIKE 'STAGE-%')
"""
import frappe
import json


def _nc_exists(name):
    return bool(frappe.db.exists("Number Card", name))


def _chart_exists(name):
    return bool(frappe.db.exists("Dashboard Chart", name))


def execute():
    print("=== FIX WORKSPACE FINAL ===\n")

    # ----------------------------------------------------------
    # 1. BUYING - injecter chart + NCs natifs dans le content JSON
    #    (garder les shortcuts KYA déjà ajoutés)
    # ----------------------------------------------------------
    buying_content_raw = frappe.db.get_value("Workspace", "Buying", "content") or "[]"
    try:
        buying_content = json.loads(buying_content_raw)
    except Exception:
        buying_content = []

    # Vérifier si les charts/NCs natifs sont déjà là
    has_native_chart = any(item.get("type") == "chart" for item in buying_content)
    has_native_nc = any(item.get("type") == "number_card" for item in buying_content)

    if not has_native_chart or not has_native_nc:
        # Séparer les items KYA des items natifs
        kya_items = [item for item in buying_content
                     if item.get("id", "").startswith("kya_")]
        non_kya_items = [item for item in buying_content
                         if not item.get("id", "").startswith("kya_")
                         and not (item.get("type") == "header"
                                  and "KYA" in item.get("data", {}).get("text", ""))]

        # Construire le bloc natif Buying
        native_buying_block = []

        # Chart principal
        if _chart_exists("Purchase Order Trends"):
            native_buying_block.append({
                "id": "buying_chart_1", "type": "chart",
                "data": {"chart_name": "Purchase Order Trends", "col": 12}
            })

        # Number Cards
        nc_buying = [
            ("Purchase Orders Count", "Purchase Orders Count"),
            ("Total Purchase Amount", "Montant Total d'Achat"),
            ("Total Incoming Bills", "Total Incoming Bills"),
        ]
        for nc_name, _ in nc_buying:
            if _nc_exists(nc_name):
                native_buying_block.append({
                    "id": f"buying_nc_{nc_name.replace(' ', '_').lower()}",
                    "type": "number_card",
                    "data": {"number_card_name": nc_name, "col": 4}
                })

        # Si le contenu non-KYA est vide (workspace écrasé), reconstruire
        if not non_kya_items or len(non_kya_items) < 3:
            new_content = native_buying_block + [{
                "id": "buying_sp", "type": "spacer", "data": {"col": 12}
            }] + kya_items
        else:
            # Insérer les charts/NCs natifs avant les items existants
            new_content = native_buying_block + [{
                "id": "buying_sp", "type": "spacer", "data": {"col": 12}
            }] + non_kya_items + kya_items

        frappe.db.set_value("Workspace", "Buying", "content",
                            json.dumps(new_content, ensure_ascii=False),
                            update_modified=True)
        print(f"  [OK] Buying - {len(native_buying_block)} éléments natifs ajoutés + KYA conservés")
    else:
        print(f"  [SKIP] Buying - charts/NCs natifs déjà présents ({len(buying_content)} items)")

    # ----------------------------------------------------------
    # 2. STOCK - injecter chart + NCs natifs dans le content JSON
    # ----------------------------------------------------------
    stock_content_raw = frappe.db.get_value("Workspace", "Stock", "content") or "[]"
    try:
        stock_content = json.loads(stock_content_raw)
    except Exception:
        stock_content = []

    has_stock_chart = any(item.get("type") == "chart" for item in stock_content)
    has_stock_nc = any(item.get("type") == "number_card" for item in stock_content)

    if not has_stock_chart or not has_stock_nc:
        kya_items = [item for item in stock_content
                     if item.get("id", "").startswith("kya_")]
        non_kya_items = [item for item in stock_content
                         if not item.get("id", "").startswith("kya_")
                         and not (item.get("type") == "header"
                                  and "KYA" in item.get("data", {}).get("text", ""))]

        native_stock_block = []

        if _chart_exists("Stock Value by Item Group"):
            native_stock_block.append({
                "id": "stock_chart_1", "type": "chart",
                "data": {"chart_name": "Stock Value by Item Group", "col": 12}
            })

        nc_stock = [
            ("Total Stock Value", "Valeur totale du stock"),
            ("Total Warehouses", "Total des entrepôts"),
            ("Total Active Items", "Total d'articles actifs"),
        ]
        for nc_name, _ in nc_stock:
            if _nc_exists(nc_name):
                native_stock_block.append({
                    "id": f"stock_nc_{nc_name.replace(' ', '_').lower()}",
                    "type": "number_card",
                    "data": {"number_card_name": nc_name, "col": 4}
                })

        if not non_kya_items or len(non_kya_items) < 3:
            new_content = native_stock_block + [{
                "id": "stock_sp", "type": "spacer", "data": {"col": 12}
            }] + kya_items
        else:
            new_content = native_stock_block + [{
                "id": "stock_sp", "type": "spacer", "data": {"col": 12}
            }] + non_kya_items + kya_items

        frappe.db.set_value("Workspace", "Stock", "content",
                            json.dumps(new_content, ensure_ascii=False),
                            update_modified=True)
        print(f"  [OK] Stock - {len(native_stock_block)} éléments natifs ajoutés + KYA conservés")
    else:
        print(f"  [SKIP] Stock - charts/NCs natifs déjà présents")

    # ----------------------------------------------------------
    # 3. ESPACE STAGIAIRES - mettre à jour avec les vrais charts KYA existants
    # ----------------------------------------------------------
    # Charts KYA existants (confirmés dans la DB)
    kya_charts = [
        "Stagiaires par Département",
        "Répartition par Genre",
        "Présences Mensuelles",
        "Statut Permissions Stagiaires",
    ]
    # NCs KYA existantes (confirmées dans la DB)
    kya_ncs = [
        "Stagiaires actifs",
        "Total Permissions",
        "Total Bilans de Stage",
        "Total Present (This Month)",
        "Total Absent (This Month)",
    ]

    # Mettre à jour la Number Card "Stagiaires actifs" avec le bon filtre
    if _nc_exists("Stagiaires actifs"):
        frappe.db.set_value("Number Card", "Stagiaires actifs", {
            "filters_json": json.dumps([
                ["Employee", "designation", "like", "STAGE-%"],
                ["Employee", "status", "=", "Active"]
            ]),
            "is_public": 1
        })
        print("  [OK] Number Card 'Stagiaires actifs' - filtre STAGE-% appliqué")

    # Construire le nouveau content pour Espace Stagiaires
    es_content = [
        {"id": "es_h_main", "type": "header", "data": {
            "text": "<div class='ellipsis'>\U0001f393 Espace Stagiaires KYA</div>",
            "level": 3, "col": 12
        }},
        # Shortcuts rapides
        {"id": "es_s1", "type": "shortcut", "data": {"shortcut_name": "Nouvelle Permi...", "col": 3}},
        {"id": "es_s2", "type": "shortcut", "data": {"shortcut_name": "Nouveau Bilan", "col": 3}},
        {"id": "es_s3", "type": "shortcut", "data": {"shortcut_name": "Voir Présences", "col": 3}},
        {"id": "es_s4", "type": "shortcut", "data": {"shortcut_name": "Form. Permission", "col": 3}},
        {"id": "es_sp1", "type": "spacer", "data": {"col": 12}},

        # Number Cards stagiaires
        {"id": "es_h_nc", "type": "header", "data": {
            "text": "\U0001f4ca Tableau de Bord Présences",
            "level": 4, "col": 12
        }},
    ]

    for nc_name in kya_ncs:
        if _nc_exists(nc_name):
            es_content.append({
                "id": f"es_nc_{nc_name.replace(' ', '_').lower()[:20]}",
                "type": "number_card",
                "data": {"number_card_name": nc_name, "col": 3}
            })

    # Spacer avant les charts
    es_content.append({"id": "es_sp2", "type": "spacer", "data": {"col": 12}})
    es_content.append({"id": "es_h_charts", "type": "header", "data": {
        "text": "\U0001f4c8 Statistiques Stagiaires",
        "level": 4, "col": 12
    }})

    for chart_name in kya_charts:
        if _chart_exists(chart_name):
            es_content.append({
                "id": f"es_chart_{chart_name.replace(' ', '_')[:20]}",
                "type": "chart",
                "data": {"chart_name": chart_name, "col": 6}
            })

    frappe.db.set_value("Workspace", "Espace Stagiaires", "content",
                        json.dumps(es_content, ensure_ascii=False),
                        update_modified=True)

    nc_added = len([i for i in es_content if i.get("type") == "number_card"])
    chart_added = len([i for i in es_content if i.get("type") == "chart"])
    print(f"  [OK] Espace Stagiaires - {nc_added} NCs + {chart_added} charts")

    # ----------------------------------------------------------
    # 4. FIX icône workspace "Congés & Permissions"
    # ----------------------------------------------------------
    if frappe.db.exists("Workspace", "Congés & Permissions"):
        current_icon = frappe.db.get_value("Workspace", "Congés & Permissions", "icon")
        if not current_icon:
            frappe.db.set_value("Workspace", "Congés & Permissions", "icon",
                                "leave-application", update_modified=False)
            print("  [OK] Congés & Permissions - icône 'leave-application' ajoutée")
        elif current_icon == "leave-application":
            print(f"  [OK] Congés & Permissions - icône déjà correcte: {current_icon}")
        else:
            print(f"  [INFO] Congés & Permissions - icône actuelle: {current_icon}")
    else:
        print("  [WARN] Workspace 'Congés & Permissions' introuvable")

    # ----------------------------------------------------------
    # 5. FIX KYA Services - s'assurer que le content est correct
    # ----------------------------------------------------------
    nc_kya_services = [
        ("Total Formulaires KYA", "Total Formulaires", "KYA Form", "#3F51B5"),
        ("Total Evaluations KYA", "Total Évaluations", "KYA Evaluation", "#9C27B0"),
        ("Reponses Recues KYA", "Réponses Reçues", "KYA Form Response", "#009688"),
    ]
    for nc_name, label, dt, color in nc_kya_services:
        # Utiliser la NC existante si elle a le bon nom
        # (d'après le listing, il y a des tas de doublons : -1, -2, etc.)
        # Forcer la NC canonique
        if frappe.db.exists("Number Card", nc_name):
            frappe.db.set_value("Number Card", nc_name, {
                "label": label, "document_type": dt, "color": color,
                "function": "Count", "is_public": 1
            })

    # S'assurer qu'il y a aussi "Total Formulaires" (NC native existante dans KYA Form)
    kya_svc_nc_list = []
    for nc_name in ["Total Formulaires KYA", "Total Evaluations KYA", "Reponses Recues KYA"]:
        if _nc_exists(nc_name):
            kya_svc_nc_list.append(nc_name)

    # Mettre à jour le content de KYA Services avec ces NCs
    svc_content_raw = frappe.db.get_value("Workspace", "KYA Services", "content") or "[]"
    try:
        svc_content = json.loads(svc_content_raw)
    except Exception:
        svc_content = []

    has_svc_nc = any(item.get("type") == "number_card" for item in svc_content)
    if not has_svc_nc and kya_svc_nc_list:
        svc_content.append({"id": "svc_sp", "type": "spacer", "data": {"col": 12}})
        svc_content.append({"id": "svc_h_nc", "type": "header", "data": {
            "text": "\U0001f4ca Indicateurs KYA Services",
            "level": 4, "col": 12
        }})
        for i, nc_name in enumerate(kya_svc_nc_list):
            svc_content.append({
                "id": f"svc_nc_{i}", "type": "number_card",
                "data": {"number_card_name": nc_name, "col": 4}
            })
        frappe.db.set_value("Workspace", "KYA Services", "content",
                            json.dumps(svc_content, ensure_ascii=False),
                            update_modified=True)
        print(f"  [OK] KYA Services - {len(kya_svc_nc_list)} NCs ajoutées")
    else:
        print(f"  [SKIP] KYA Services - NCs déjà présentes ou aucune NC disponible")

    # ----------------------------------------------------------
    # 6. COMMIT + cache clear
    # ----------------------------------------------------------
    frappe.db.commit()
    try:
        for ws in ["Espace Stagiaires", "KYA Services", "Buying", "Stock"]:
            frappe.cache().delete_value(f"workspace:{ws}")
        frappe.cache().delete_value("workspace:Congés & Permissions")
    except Exception:
        pass

    print("\n=== RÉSUMÉ FINAL ===")
    for ws in ["Espace Stagiaires", "KYA Services", "Buying", "Stock"]:
        c = json.loads(frappe.db.get_value("Workspace", ws, "content") or "[]")
        nc_c = len([i for i in c if i.get("type") == "number_card"])
        chart_c = len([i for i in c if i.get("type") == "chart"])
        sc_c = len([i for i in c if i.get("type") == "shortcut"])
        print(f"  {ws}: {nc_c} NC, {chart_c} charts, {sc_c} shortcuts ({len(c)} total)")

    print("""
=== ACTIONS NAVIGATEUR ===
1. Vider le cache navigateur (Ctrl+Shift+Delete)
2. Recharger la page (F5)
3. Si le problème persiste : ouvrir en onglet privé (Ctrl+Shift+N)
""")

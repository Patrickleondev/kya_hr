"""
Force sync tous les workspaces KYA depuis les fichiers JSON de l'app.
bench migrate ne met pas a jour les workspaces existants -> on force ici.
Run: bench --site frontend execute kya_hr.force_sync_workspaces.execute
"""
import frappe
import json
import os


def _get_app_workspace_path(ws_folder):
    """Retourne le chemin absolu du workspace JSON dans l'app kya_hr."""
    bench_path = frappe.utils.get_bench_path()
    return os.path.join(
        bench_path, "apps", "kya_hr", "kya_hr", "workspace", ws_folder
    )


def _get_kya_services_workspace_path():
    bench_path = frappe.utils.get_bench_path()
    return os.path.join(
        bench_path, "apps", "kya_services", "kya_services",
        "workspace", "kya_services", "kya_services.json"
    )


def _force_update_workspace(workspace_name, links_data, content_data=None):
    """Supprime les anciens liens et insere les nouveaux. Met a jour content si fourni."""
    if not frappe.db.exists("Workspace", workspace_name):
        print(f"  SKIP: {workspace_name} not found in DB")
        return

    # Delete existing child links (raw SQL pour bypasser les hooks)
    frappe.db.delete("Workspace Link", {"parent": workspace_name})
    frappe.db.delete("Workspace Shortcut", {"parent": workspace_name})

    # Reinsert links
    for i, lk in enumerate(links_data):
        row = frappe.new_doc("Workspace Link")
        row.parent = workspace_name
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

    # Update content if provided
    if content_data is not None:
        content_str = json.dumps(content_data, ensure_ascii=False)
        frappe.db.set_value("Workspace", workspace_name, "content", content_str,
                            update_modified=True)

    frappe.db.commit()
    print(f"  SYNCED: {workspace_name} ({len(links_data)} links)")


def execute():
    print("=== FORCE SYNC WORKSPACES KYA ===")

    # ================================================================
    # 1. Espace Stagiaires
    # ================================================================
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
    _force_update_workspace("Espace Stagiaires", es_links)

    # ================================================================
    # 2. KYA Services — retirer les child tables (istable:1)
    # ================================================================
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
    _force_update_workspace("KYA Services", svc_links)

    # ================================================================
    # 3. Achats & Approvisionnement — parent_page + liens web form
    # ================================================================
    achats_links = [
        {"type": "Card Break", "label": "\U0001f6cd Achats KYA"},
        {"type": "Link", "label": "Demandes d\u2019Achat", "link_to": "Demande Achat KYA", "link_type": "DocType", "onboard": 1, "icon": "shopping-cart"},
        {"type": "Card Break", "label": "\U0001f4dd Formulaires Web"},
        {"type": "Link", "label": "Formulaire Demande d\u2019Achat", "link_to": "/demande-achat", "link_type": "URL", "icon": "external-link"},
    ]
    _force_update_workspace("Achats & Approvisionnement", achats_links)

    # ================================================================
    # 4. Stock & Logistique — parent_page + liens web form
    # ================================================================
    stock_links = [
        {"type": "Card Break", "label": "\U0001f4e6 Stock KYA"},
        {"type": "Link", "label": "PV Sortie Mat\u00e9riel", "link_to": "PV Sortie Materiel", "link_type": "DocType", "onboard": 1, "icon": "package"},
        {"type": "Card Break", "label": "\U0001f4dd Formulaires Web"},
        {"type": "Link", "label": "Formulaire PV Sortie", "link_to": "/pv-sortie-materiel", "link_type": "URL", "icon": "external-link"},
    ]
    _force_update_workspace("Stock & Logistique", stock_links)

    # ================================================================
    # 5. Congés & Permissions — vérifier
    # ================================================================
    print()
    print("=== VERIFICATION POST-SYNC ===")
    for ws in ["Espace Stagiaires", "KYA Services", "Achats & Approvisionnement", "Stock & Logistique"]:
        count = frappe.db.count("Workspace Link", {"parent": ws})
        print(f"  {ws}: {count} links en DB")

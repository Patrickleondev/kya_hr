"""
fix_all_ws_issues.py
====================
Corrige :
1. Workspace Gestion Equipe — supprime le doublon "Tableau de Bord"
2. Workspace Espace Stagiaires — Name Cards filtres + shortcut Dashboard
3. Build kya_services app assets
"""
import frappe, json


def execute():
    frappe.db.auto_commit_on_many_writes = True

    # ─── 1) GESTION EQUIPE — supprimer "Tableau de Bord" (doublon) ───────────────
    try:
        ws_ge = frappe.get_doc("Workspace", "Gestion Equipe")
        before = [(s.label, s.type) for s in ws_ge.shortcuts]
        # Garder tout sauf "Tableau de Bord" (garder "Dashboard Équipe")
        ws_ge.shortcuts = [s for s in ws_ge.shortcuts
                           if s.label not in ("Tableau de Bord", "Tableau de Bord Gestion")]
        ws_ge.save(ignore_permissions=True)
        frappe.db.commit()
        after = [(s.label, s.type) for s in ws_ge.shortcuts]
        print(f"[Gestion Equipe] Shortcuts: {before} → {after}")
    except Exception as e:
        print(f"[Gestion Equipe] ERREUR: {e}")

    # ─── 2) ESPACE STAGIAIRES — corriger filtres Number Cards ────────────────────
    try:
        nc_stagiaires = frappe.db.get_value("Number Card", "Stagiaires Actifs", "name")
        if nc_stagiaires:
            correct_filter = json.dumps([
                ["Employee", "employment_type", "=", "Stage"],
                ["Employee", "status", "=", "Active"]
            ])
            frappe.db.set_value("Number Card", "Stagiaires Actifs", "filters_json", correct_filter)
            print("[NC Stagiaires Actifs] filtre corrigé ✓")
        else:
            print("[NC Stagiaires Actifs] non trouvée")
    except Exception as e:
        print(f"[NC Stagiaires Actifs] ERREUR: {e}")

    try:
        nc_perm = frappe.db.get_value("Number Card", "Permissions Stagiaires en Attente", "name")
        if nc_perm:
            correct_filter = json.dumps([
                ["Permission Sortie Stagiaire", "workflow_state", "not in", ["Approuvé", "Rejeté"]]
            ])
            frappe.db.set_value("Number Card", "Permissions Stagiaires en Attente", "filters_json", correct_filter)
            print("[NC Permissions] filtre corrigé ✓")
    except Exception as e:
        print(f"[NC Permissions] ERREUR: {e}")

    try:
        nc_bilan = frappe.db.get_value("Number Card", "Bilans de Stage Soumis", "name")
        if nc_bilan:
            correct_filter = json.dumps([
                ["Bilan Fin de Stage", "docstatus", "!=", 0]
            ])
            frappe.db.set_value("Number Card", "Bilans de Stage Soumis", "filters_json", correct_filter)
            print("[NC Bilans] filtre corrigé ✓")
    except Exception as e:
        print(f"[NC Bilans] ERREUR: {e}")

    frappe.db.commit()

    # ─── 3) ESPACE STAGIAIRES — s'assurer que le shortcut Dashboard est là ───────
    try:
        ws_stag = frappe.get_doc("Workspace", "Espace Stagiaires")
        labels = [s.label for s in ws_stag.shortcuts]
        print(f"[Espace Stagiaires] shortcuts actuels: {labels}")

        dashboard_labels = ["📊 Dashboard Stagiaires", "Dashboard Stagiaires"]
        has_dashboard = any(l in labels for l in dashboard_labels)

        if not has_dashboard:
            ws_stag.append("shortcuts", {
                "label": "📊 Dashboard Stagiaires",
                "type": "URL",
                "url": "/kya-dashboard-stagiaires",
                "color": "Green",
                "icon": "bar-chart-line"
            })
            ws_stag.save(ignore_permissions=True)
            frappe.db.commit()
            print("[Espace Stagiaires] shortcut Dashboard ajouté ✓")
        else:
            print("[Espace Stagiaires] shortcut Dashboard déjà présent ✓")
    except Exception as e:
        print(f"[Espace Stagiaires] ERREUR: {e}")

    frappe.db.commit()
    print("=== DONE ===")


# ─── 1) GESTION EQUIPE — supprimer "Tableau de Bord" (doublon) ───────────────
try:
    ws_ge = frappe.get_doc("Workspace", "Gestion Equipe")
    before = [(s.label, s.type) for s in ws_ge.shortcuts]
    # Garder tout sauf "Tableau de Bord" (garder "Dashboard Équipe")
    ws_ge.shortcuts = [s for s in ws_ge.shortcuts
                       if s.label not in ("Tableau de Bord", "Tableau de Bord Gestion")]
    ws_ge.save(ignore_permissions=True)
    frappe.db.commit()
    after = [(s.label, s.type) for s in ws_ge.shortcuts]
    print(f"[Gestion Equipe] Shortcuts: {before} → {after}")
except Exception as e:
    print(f"[Gestion Equipe] ERREUR: {e}")

# ─── 2) ESPACE STAGIAIRES — corriger filtres Number Cards ────────────────────
try:
    # Filtre Stagiaires Actifs (5 éléments → 4)
    nc_stagiaires = frappe.db.get_value("Number Card", "Stagiaires Actifs", "name")
    if nc_stagiaires:
        correct_filter = json.dumps([
            ["Employee", "employment_type", "=", "Stage"],
            ["Employee", "status", "=", "Active"]
        ])
        frappe.db.set_value("Number Card", "Stagiaires Actifs", "filters_json", correct_filter)
        print("[NC Stagiaires Actifs] filtre corrigé ✓")
    else:
        print("[NC Stagiaires Actifs] non trouvée")
except Exception as e:
    print(f"[NC Stagiaires Actifs] ERREUR: {e}")

try:
    nc_perm = frappe.db.get_value("Number Card", "Permissions Stagiaires en Attente", "name")
    if nc_perm:
        correct_filter = json.dumps([
            ["Permission Sortie Stagiaire", "workflow_state", "not in", ["Approuvé", "Rejeté"]]
        ])
        frappe.db.set_value("Number Card", "Permissions Stagiaires en Attente", "filters_json", correct_filter)
        print("[NC Permissions] filtre corrigé ✓")
except Exception as e:
    print(f"[NC Permissions] ERREUR: {e}")

try:
    nc_bilan = frappe.db.get_value("Number Card", "Bilans de Stage Soumis", "name")
    if nc_bilan:
        correct_filter = json.dumps([
            ["Bilan Fin de Stage", "docstatus", "!=", 0]
        ])
        frappe.db.set_value("Number Card", "Bilans de Stage Soumis", "filters_json", correct_filter)
        print("[NC Bilans] filtre corrigé ✓")
except Exception as e:
    print(f"[NC Bilans] ERREUR: {e}")

frappe.db.commit()

# ─── 3) ESPACE STAGIAIRES — s'assurer que le shortcut Dashboard est là ───────
try:
    ws_stag = frappe.get_doc("Workspace", "Espace Stagiaires")
    labels = [s.label for s in ws_stag.shortcuts]
    print(f"[Espace Stagiaires] shortcuts: {labels}")

    dashboard_labels = ["📊 Dashboard Stagiaires", "Dashboard Stagiaires"]
    has_dashboard = any(l in labels for l in dashboard_labels)

    if not has_dashboard:
        ws_stag.append("shortcuts", {
            "label": "📊 Dashboard Stagiaires",
            "type": "URL",
            "url": "/kya-dashboard-stagiaires",
            "color": "Green",
            "icon": "bar-chart-line"
        })
        ws_stag.save(ignore_permissions=True)
        frappe.db.commit()
        print("[Espace Stagiaires] shortcut Dashboard ajouté ✓")
    else:
        print("[Espace Stagiaires] shortcut Dashboard déjà présent ✓")
except Exception as e:
    print(f"[Espace Stagiaires] ERREUR: {e}")

frappe.db.commit()
print("=== DONE ===")

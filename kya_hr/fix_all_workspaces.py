"""
KYA — Fix all workspace issues in one pass (SQL-only, pas de ws.save).
bench --site frontend execute kya_hr.fix_all_workspaces.execute
"""
import frappe
import json


def execute():
    print("=== KYA FIX ALL WORKSPACES ===")
    fix_kya_services_portail()
    fix_espace_employes()
    fix_gestion_equipe()
    fix_espace_stagiaires()
    fix_website_settings_appname()
    fix_corrupted_statut_values()
    frappe.db.commit()
    print("=== ALL FIXES APPLIED ===")


def fix_kya_services_portail():
    """Fix 'Portail Enquête' shortcut — NULL link_to causes 'DocType introuvable'."""
    frappe.db.sql("""
        UPDATE `tabWorkspace Shortcut`
        SET url = '/kya-survey', link_to = ''
        WHERE parent = 'KYA Services' AND label = 'Portail Enquête'
    """)
    print("  [KYA Services] Fixed 'Portail Enquête' → url=/kya-survey ✓")


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
        {"id": "spacer-1", "type": "spacer", "data": {"col": 12}},
        {"id": "header-1", "type": "header",
         "data": {"text": "📋 Gestion des Tâches", "col": 12, "level": 4}},
        {"id": "spacer-2", "type": "spacer", "data": {"col": 12}},
    ]
    frappe.db.set_value("Workspace", "Gestion Équipe", "content", json.dumps(new_content))
    print("  [Gestion Équipe] Removed card/link blocks, rebuilt content ✓")


def fix_espace_stagiaires():
    """Ensure Espace Stagiaires is visible, public, with correct icon."""
    frappe.db.sql("""
        UPDATE tabWorkspace
        SET public = 1, is_hidden = 0, icon = 'education'
        WHERE name = 'Espace Stagiaires'
    """)
    print("  [Espace Stagiaires] Visible + public + icon=education ✓")


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
    # KYA Form: valid options are Brouillon, Actif, Fermé
    frappe.db.sql("""
        UPDATE `tabKYA Form`
        SET statut = 'Actif'
        WHERE statut NOT IN ('Brouillon', 'Actif', 'Ferm\u00e9')
          AND (statut LIKE '%tiv%' OR statut LIKE '%ctif%' OR statut LIKE '%Activ%')
    """)
    # KYA Evaluation: valid options are Brouillon, Soumis, Validé
    frappe.db.sql("""
        UPDATE `tabKYA Evaluation`
        SET statut = 'Brouillon'
        WHERE statut NOT IN ('Brouillon', 'Soumis', 'Valid\u00e9')
    """)
    print("  [Statut] Valeurs corrompues corrigées ✓")

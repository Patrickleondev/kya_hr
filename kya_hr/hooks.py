app_name = "kya_hr"
app_title = "KYA HR"
app_publisher = "KYA-Energy Group"
app_description = "Personnalisations RH et traductions pour KYA-Energy Group"
app_email = "info@kya-energy.com"
app_license = "mit"

# CSS + JS pour les web forms publics
web_include_css = ["/assets/kya_hr/css/kya_webform.css"]
web_include_js = ["/assets/kya_hr/js/kya_webform.js"]

# CSS Desk léger uniquement (le CSS webform reste limité aux web forms publics)
app_include_css = ["/assets/kya_hr/css/kya_desk.css"]
app_include_js = [
    "/assets/kya_hr/js/employee_list.js",
    "/assets/kya_hr/js/kya_desktop_fix.js",
    "/assets/kya_hr/js/kya_new_doc_to_webform.js",
    "/assets/kya_hr/js/kya_sidebar_router.js",
    "/assets/kya_hr/js/kya_list_to_webform.js",
]

# Fixtures pour les flux, rôles et personnalisations de champs
fixtures = [
    {"dt": "Workflow"},
    {"dt": "Workflow State"},
    {"dt": "Workflow Action"},
    {"dt": "Role"},
    {"dt": "Custom Field"},
    {"dt": "Property Setter"},
    {"dt": "Email Template"},
    {"dt": "Notification"},
    {"dt": "Letter Head"},
    {"dt": "Employment Type", "filters": [["name", "in", ["CDI", "CDD", "Stage", "Prestataire"]]]},
]

# DocType client scripts
# IMPORTANT : tous les chemins doivent pointer vers public/js/ pour que bench build
# copie les fichiers dans sites/assets/kya_hr/js/ (nginx les sert).
doctype_js = {
    "Employee": "public/js/employee.js",
    "Permission Sortie Stagiaire": "public/js/permission_sortie_stagiaire.js",
    "Permission Sortie Employe": "public/js/permission_sortie_employe.js",
    "Bilan Fin de Stage": "public/js/bilan_fin_de_stage.js",
    "PV Sortie Materiel": "public/js/pv_sortie_materiel.js",
    "Planning Conge": "public/js/planning_conge.js",
    "Demande Achat KYA": "public/js/demande_achat_kya.js",
    "PV Entree Materiel": "doctype/pv_entree_materiel/pv_entree_materiel.js",
    "Inventaire KYA": "doctype/inventaire_kya/inventaire_kya.js",
    "KYA Contrat": "public/js/kya_contrat.js",
    "Brouillard Caisse": "doctype/brouillard_caisse/brouillard_caisse.js",
    "KYA Compta Import": "doctype/kya_compta_import/kya_compta_import.js",
    "Marche KYA": "doctype/marche_kya/marche_kya.js",
}

# Jinja environment
jinja = {
    "methods": [
        "kya_hr.utils.get_kya_email_footer",
    ],
}

override_whitelisted_methods = {
    "frappe.utils.print_format.download_pdf": "kya_hr.api.print_format.download_pdf",
}

# Grille indiciaire : calcul automatique de la valeur indiciaire (Employee)
doc_events = {
    "Employee": {
        "before_save": "kya_hr.grille_indiciaire.calculer_indice_employee",
    },
    # Chef routing + notifications demandeur (confirmation soumission + mises à jour état)
    "Demande Achat KYA": {
        "before_save": "kya_hr.chef_routing.populate_chef",
        "validate": "kya_hr.auto_calc_logic.compute_demande_achat",
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Bon Commande KYA": {
        "validate": "kya_hr.auto_calc_logic.compute_bon_commande",
    },
    "Permission Sortie Employe": {
        "before_save": "kya_hr.chef_routing.populate_chef",
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Permission Sortie Stagiaire": {
        "before_save": "kya_hr.chef_routing.populate_chef",
        "validate": "kya_hr.auto_calc_logic.compute_permission_sortie_stagiaire",
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Planning Conge": {
        "before_save": [
            "kya_hr.chef_routing.populate_chef",
            "kya_hr.planning_conge_logic.compute",
        ],
        "validate": "kya_hr.planning_conge_logic.compute",
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": [
            "kya_hr.email_notifications.send_workflow_update",
            "kya_hr.leave_bridge.create_leave_from_planning",
            "kya_hr.planning_conge_logic.sync_statut",
        ],
        "on_update_after_submit": [
            "kya_hr.email_notifications.send_workflow_update",
            "kya_hr.leave_bridge.create_leave_from_planning",
            "kya_hr.planning_conge_logic.sync_statut",
        ],
    },
    # PV et Bilan : pas de chef_routing (employee_field suffit)
    "PV Sortie Materiel": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Bilan Fin de Stage": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    # Tache Equipe : statut auto depuis taux_effectif (custom:1 -> controller Python inactif)
    "Tache Equipe": {
        "validate": "kya_hr.auto_calc_logic.compute_tache_equipe",
    },
}

# Permission Query Conditions : restreindre la visibilité Employee aux non-RH
permission_query_conditions = {
    "Employee": "kya_hr.employee_permissions.employee_query",
}

has_permission = {
    "Employee": "kya_hr.employee_permissions.employee_has_permission",
}

# Rappels quotidiens (anniversaires naissance & ancienneté)
scheduler_events = {
    "daily": [
        "kya_hr.reminders.send_kya_birthday_reminders",
        "kya_hr.reminders.send_kya_anniversary_reminders",
        "kya_hr.kya_hr.doctype.document_vehicule.document_vehicule.send_expiry_reminders",
    ],
    # Vendredi 17h00 : point hebdomadaire caisse au DG + DGA
    "cron": {
        "0 17 * * 5": [
            "kya_hr.kya_hr.doctype.brouillard_caisse.brouillard_caisse.send_weekly_dg_summary",
        ],
    },
}

# Post-migration: nettoyage workspaces obsolètes + branding KYA
after_migrate = [
    "kya_hr.setup_locale.execute",
    "kya_hr.setup_leave_types.execute",
    "kya_hr.force_sync_workspaces.execute",
    "kya_hr.force_publish_webforms.execute",
    "kya_hr.notification_fixes.execute",
    "kya_hr.setup_branding.execute",
    "kya_hr.fix_all_workspaces.execute",
    "kya_hr.setup_fleet.run",
    "kya_hr.setup_fleet_workspace.run",
    "kya_hr.setup_fleet_dashboard.run",
    "kya_hr.setup_pv_extensions.run",
    "kya_hr.setup_inventaire_dashboard.run",
    "kya_hr.desktop_icons.execute",
    "kya_hr.coherence_fixes.execute",
    "kya_hr.ensure_visibility.execute",
]

# Post-install: create desktop icons + ensure all KYA / HRMS workspaces are
# visible to Administrator (workaround for Frappe v16 core bug
# "'list' object is not callable" in create_desktop_icons_from_workspace,
# plus block_module / for_user / parent_page hiding rules).
after_install = [
    "kya_hr.desktop_icons.execute",
    "kya_hr.coherence_fixes.execute",
    "kya_hr.ensure_visibility.execute",
]

# Translations
# Note: translations are automatically picked up from the translations folder

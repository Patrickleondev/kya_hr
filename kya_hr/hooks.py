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
    "/assets/kya_hr/js/kya_view_to_webform.js",
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
    {"dt": "KYA Contract Template"},
    # Supplier Groups/Suppliers KYA are seeded by
    # kya_hr.setup_retour_materiel.run during after_migrate. Importing them as
    # fixtures can run before ERPNext creates "All Supplier Groups" on a fresh
    # install, which breaks NestedSet during sync_fixtures.
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
        "kya_hr.utils.nombre_en_lettres",
    ],
}

override_whitelisted_methods = {
    "frappe.utils.print_format.download_pdf": "kya_hr.api.print_format.download_pdf",
}

# Redirects pour les routes Frappe legacy (v13/v14) qui 404 en v16.
# - /desk/people : ancien lien Frappe HR ; en v16 c'est /app/hr
# - /desk/hrms   : tentative SPA HRMS ; redirige vers le workspace HR
website_redirects = [
    {"source": r"/desk/people", "target": "/app/hr", "redirect_http_status": 301},
    {"source": r"/desk/hrms", "target": "/app/hr", "redirect_http_status": 301},
    {"source": r"/desk/people/(.*)", "target": "/app/hr", "redirect_http_status": 301, "match_with_query_string": False},
]

# Auto-lien Employee <-> User a chaque connexion (self-healing du user_id).
# Evite que la RH doive saisir manuellement le 'ID Utilisateur' sur chaque
# fiche Employee. Voir kya_hr.link_employees_users.on_session_creation.
on_session_creation = "kya_hr.link_employees_users.on_session_creation"

# Grille indiciaire : calcul automatique de la valeur indiciaire (Employee)
doc_events = {
    "Employee": {
        "before_save": "kya_hr.grille_indiciaire.calculer_indice_employee",
        "after_insert": [
            "kya_hr.dashboard_realtime.notify_dashboard_change",
            "kya_hr.role_sync.sync_employee_role",
            "kya_hr.equipe_member_sync.sync_on_employee_change",
        ],
        "on_update": [
            "kya_hr.dashboard_realtime.notify_dashboard_change",
            "kya_hr.role_sync.sync_employee_role",
            "kya_hr.equipe_member_sync.sync_on_employee_change",
        ],
    },
    "Attendance": {
        "after_insert": "kya_hr.dashboard_realtime.notify_dashboard_change",
        "on_update": "kya_hr.dashboard_realtime.notify_dashboard_change",
    },
    # Tache Equipe : notification des attributaires (creation + ajout d'un membre)
    "Tache Equipe": {
        "after_insert": "kya_hr.email_notifications.send_task_assignment_email",
        "on_update": "kya_hr.email_notifications.send_task_assignment_email",
    },
    # Chef routing + notifications demandeur (confirmation soumission + mises à jour état)
    "Demande Achat KYA": {
        "before_save": "kya_hr.chef_routing.populate_chef",
        "validate": "kya_hr.auto_calc_logic.compute_demande_achat",
        "after_insert": [
            "kya_hr.email_notifications.send_submission_recap",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
        "on_update": [
            "kya_hr.email_notifications.send_workflow_update",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
    },
    "Bon Commande KYA": {
        "validate": "kya_hr.auto_calc_logic.compute_bon_commande",
    },
    "Permission Sortie Employe": {
        "before_save": "kya_hr.chef_routing.populate_chef",
        "after_insert": [
            "kya_hr.email_notifications.send_submission_recap",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
        "on_update": [
            "kya_hr.email_notifications.send_workflow_update",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
    },
    "Permission Sortie Stagiaire": {
        "before_save": "kya_hr.chef_routing.populate_chef",
        "validate": "kya_hr.auto_calc_logic.compute_permission_sortie_stagiaire",
        "after_insert": [
            "kya_hr.email_notifications.send_submission_recap",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
        "on_update": [
            "kya_hr.email_notifications.send_workflow_update",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
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
        "after_insert": [
            "kya_hr.email_notifications.send_submission_recap",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
        "on_update": [
            "kya_hr.email_notifications.send_workflow_update",
            "kya_hr.dashboard_realtime.notify_dashboard_change",
        ],
    },
    "PV Entree Materiel": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Retour Materiel KYA": {
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

# Permission Query Conditions : restreindre la visibilité Employee + scope
# Chef d'Équipe sur ses propres équipes / tâches.
permission_query_conditions = {
    "Employee": "kya_hr.employee_permissions.employee_query",
    "Equipe KYA": "kya_hr.equipe_permissions.equipe_kya_query",
    "Tache Equipe": "kya_hr.equipe_permissions.tache_equipe_query",
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

# Post-migration : la liste exacte des étapes est dans
# kya_hr/safe_migrations.py:AFTER_MIGRATE. Le wrapper attrape les exceptions
# par étape (un script qui plante n'avorte plus la migration globale)
# et logge dans Error Log. Pour rejouer manuellement :
#    bench --site <site> execute kya_hr.safe_migrations.retry_failed
after_migrate = "kya_hr.safe_migrations.after_migrate"

# Boot session : monkey-patch ERPNext setup_demo (timeout CI/preprod).
# Cf. kya_hr/runtime_overrides.py pour le contexte complet.
boot_session = "kya_hr.runtime_overrides.boot_session"

# Post-install : idem, géré par safe_migrations.after_install.
# (Frappe v16 core bug "'list' object is not callable" dans
# create_desktop_icons_from_workspace + block_module / for_user / parent_page
# sont traités défensivement dans kya_hr.desktop_icons.)
after_install = "kya_hr.safe_migrations.after_install"

# Translations
# Note: translations are automatically picked up from the translations folder

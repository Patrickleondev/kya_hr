app_name = "kya_hr"
app_title = "KYA HR"
app_publisher = "KYA-Energy Group"
app_description = "Personnalisations RH et traductions pour KYA-Energy Group"
app_email = "info@kya-energy.com"
app_license = "mit"

# Branding KYA — logo utilisé sur la navbar, page de connexion et emails
app_logo_url = "/assets/kya_hr/images/kya_logo.png"

# CSS + JS pour les web forms publics
web_include_css = ["/assets/kya_hr/css/kya_webform.css"]
web_include_js = ["/assets/kya_hr/js/kya_webform.js"]

# CSS sur le desk (branding, sidebar, logo)
app_include_css = ["/assets/kya_hr/css/kya_webform.css"]
app_include_js = [
    "/assets/kya_hr/js/employee_list.js",
    "/assets/kya_hr/js/kya_desktop_fix.js",
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
    {"dt": "Employment Type", "filters": [["name", "in", ["CDI", "CDD", "Stage", "Prestataire"]]]},
    {"dt": "Letter Head", "filters": [["name", "=", "KYA-Energy Group"]]},
]

# DocType client scripts
doctype_js = {
    "Employee": "public/js/employee.js",
    "Permission Sortie Stagiaire": "doctype/permission_sortie_stagiaire/permission_sortie_stagiaire.js",
    "Permission Sortie Employe": "doctype/permission_sortie_employe/permission_sortie_employe.js",
    "Bilan Fin de Stage": "doctype/bilan_fin_de_stage/bilan_fin_de_stage.js",
    "PV Sortie Materiel": "doctype/pv_sortie_materiel/pv_sortie_materiel.js",
    "Planning Conge": "doctype/planning_conge/planning_conge.js",
    "Demande Achat KYA": "doctype/demande_achat_kya/demande_achat_kya.js",
}

# Jinja environment
jinja = {
    "methods": [
        "kya_hr.utils.get_kya_email_footer",
    ],
}

# Grille indiciaire : calcul automatique de la valeur indiciaire (Employee)
# + Email récap à la soumission de web forms + suivi workflow
doc_events = {
    "Employee": {
        "before_save": [
            "kya_hr.grille_indiciaire.calculer_indice_employee",
            "kya_hr.matricule.auto_generate_matricule",
        ],
    },
    "Permission Sortie Employe": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Permission Sortie Stagiaire": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "PV Sortie Materiel": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Demande Achat KYA": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Planning Conge": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": [
            "kya_hr.email_notifications.send_workflow_update",
            "kya_hr.leave_bridge.create_leave_from_planning",
        ],
    },
    "Leave Application": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Bilan Fin de Stage": {
        "after_insert": "kya_hr.email_notifications.send_submission_recap",
        "on_update": "kya_hr.email_notifications.send_workflow_update",
    },
    "Tache Equipe": {
        "after_insert": "kya_hr.email_notifications.send_task_assignment_email",
    },
}

# Rappels quotidiens (anniversaires naissance & ancienneté)
scheduler_events = {
    "daily": [
        "kya_hr.reminders.send_kya_birthday_reminders",
        "kya_hr.reminders.send_kya_anniversary_reminders",
    ],
}

# Filtrage par équipe — Chef Service ne voit que les plans/tâches de son équipe
# Filtre Employee — Stagiaire ne voit que sa propre fiche
permission_query_conditions = {
    "Plan Trimestriel": "kya_hr.team_permissions.plan_trimestriel_query",
    "Tache Equipe": "kya_hr.team_permissions.tache_equipe_query",
    "Employee": "kya_hr.permissions.employee_query_condition",
}

has_permission = {
    "Plan Trimestriel": "kya_hr.team_permissions.plan_trimestriel_has_permission",
    "Tache Equipe": "kya_hr.team_permissions.tache_equipe_has_permission",
}

# Post-migration: nettoyage workspaces obsolètes + branding KYA
after_migrate = [
    "kya_hr.force_sync_workspaces.execute",
    "kya_hr.setup_branding.execute",
    "kya_hr.fix_all_workspaces.execute",
]

# Translations
# Note: translations are automatically picked up from the translations folder

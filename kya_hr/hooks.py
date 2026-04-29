app_name = "kya_hr"
app_title = "KYA HR"
app_publisher = "KYA-Energy Group"
app_description = "Personnalisations RH et traductions pour KYA-Energy Group"
app_email = "info@kya-energy.com"
app_license = "mit"

# CSS + JS pour les web forms publics
web_include_css = ["/assets/kya_hr/css/kya_webform.css"]
web_include_js = ["/assets/kya_hr/js/kya_webform.js"]

# CSS sur le desk (branding, sidebar, logo)
app_include_css = ["/assets/kya_hr/css/kya_webform.css"]
app_include_js = ["/assets/kya_hr/js/employee_list.js"]

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
    "KYA Contrat": "doctype/kya_contrat/kya_contrat.js",
}

# Jinja environment
jinja = {
    "methods": [
        "kya_hr.utils.get_kya_email_footer",
    ],
}

# Grille indiciaire : calcul automatique de la valeur indiciaire (Employee)
doc_events = {
    "Employee": {
        "before_save": "kya_hr.grille_indiciaire.calculer_indice_employee",
    },
    # Auto-rempli report_to_user pour notifications "En attente Chef"
    "Demande Achat KYA": {
        "before_save": "kya_hr.chef_routing.populate_chef",
    },
    "Permission Sortie Employe": {
        "before_save": "kya_hr.chef_routing.populate_chef",
    },
    "Permission Sortie Stagiaire": {
        "before_save": "kya_hr.chef_routing.populate_chef",
    },
    "Planning Conge": {
        "before_save": "kya_hr.chef_routing.populate_chef",
    },
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
    "kya_hr.setup_branding.execute",
    "kya_hr.fix_all_workspaces.execute",
    "kya_hr.setup_fleet.run",
    "kya_hr.setup_fleet_workspace.run",
    "kya_hr.setup_fleet_dashboard.run",
    "kya_hr.setup_pv_extensions.run",
    "kya_hr.setup_inventaire_dashboard.run",
    "kya_hr.desktop_icons.execute",
]

# Translations
# Note: translations are automatically picked up from the translations folder

app_name = "kya_hr"
app_title = "KYA HR"
app_publisher = "KYA-Energy Group"
app_description = "Personnalisations RH et traductions pour KYA-Energy Group"
app_email = "info@kya-energy.com"
app_license = "mit"

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
    {"dt": "Workspace"},
]

# DocType client scripts
doctype_js = {
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

# Translations
# Note: translations are automatically picked up from the translations folder

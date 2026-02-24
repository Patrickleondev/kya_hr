import csv
import os

def clean_value(val):
    if not val:
        return ""
    # Strip trailing commas and whitespace
    val = val.rstrip(',').strip()
    
    # Fix common encoding artifacts inherited from corrupted source files
    # Order by length descending to catch longer sequences first
    replacements = {
        "Atre": "être",
        "Acgal": "égal",
        "supAcrieur": "supérieur",
        "entrAce": "entrée",
        "cochAc": "coché",
        "Ac": "é",
        "A¨": "è",
        "Aª": "ê",
        "A´": "ô",
        "A»": "û",
        "A¹": "ù",
        "A®": "î",
        "A«": "ï",
        "A§": "ç",
        "A ": "à ",
        "A0": "à",
        "A©": "é",
        "A?": "à",
        "A": "à", 
        "&quot;": '"',
        "&apos;": "'",
    }
    # Sort keys by length descending
    sorted_repl = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)
    
    for old, new in sorted_repl:
        val = val.replace(old, new)
        
    return val

def repair_ultra():
    # Detect if we are in Docker or local
    if os.path.exists('/home/frappe/frappe-bench'):
        base_path = '/home/frappe/frappe-bench/apps/kya_hr/kya_hr'
    else:
        base_path = r'd:\Stage_KYA_Energie\ERPNext_v16_Port8084\kya_hr\kya_hr'
    
    trans_path = os.path.join(base_path, 'translations')
    
    fr_csv = os.path.join(trans_path, 'fr.csv')
    hrms_csv = os.path.join(trans_path, 'hrms_fr.csv')
    erpnext_csv = os.path.join(trans_path, 'erpnext_fr.csv')
    
    # Target dictionary
    translations = {}
    
    # 1. Load ERPNext and HRMS as clean baselines
    # Use utf-8-sig to handle potential BOM correctly
    for src_file in [erpnext_csv, hrms_csv]:
        if os.path.exists(src_file):
            print(f"Loading {os.path.basename(src_file)}...")
            with open(src_file, 'r', encoding='utf-8-sig') as f:
                # Some files might have inconsistent quoting, use a lenient reader
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        key = row[0].strip()
                        val = clean_value(row[1])
                        if key and val:
                            translations[key] = val

    # 2. Add/Override specific missing UI terms and solve common "corruption"
    overrides = {
        "Add row": "Ajouter une ligne",
        "Add Row": "Ajouter une ligne",
        "Insert Row": "Insérer une ligne",
        "Delete": "Supprimer",
        "People": "Personnes",
        "Tenure": "Ancienneté",
        "Joining": "Embauche",
        "Profile": "Profil",
        "Employee Exit": "Sortie de l'employé",
        "Overview": "Aperçu",
        "Personal Details": "Détails Personnels",
        "Grade": "Échelon",
        "Grades": "Échelons",
        "Category": "Catégorie",
        "Categories": "Catégories",
        "Classification": "Classification",
        "Classification Professionnelle": "Classification Professionnelle",
        "Resignation Letter Date": "Date de la lettre de démission",
        "Relieving Date": "Date de départ",
        "Health Insurance": "Assurance Santé",
        "Health Insurance Provider": "Fournisseur d'assurance santé",
        "Health Insurance No": "N° d'Assurance Santé",
        "Employee Health Insurance": "Assurance Santé des Employés",
        "Filter by Shift": "Filtrer par quart de travail",
        "Select Employees": "Sélectionner les Employés",
        "Unmarked Employees": "Employés non marqués",
        "Encash Leave?": "Laisser Encaissé ?",
        "New Workplace": "Nouveau Lieu de Travail",
        "Exit Interview Held On": "Entretien de sortie tenu le",
        "Feedback": "Commentaires",
        "Reason for Leaving": "Raison du départ",
        "Leaves": "Congés",
        "Payroll": "Paie",
        "Recruitment": "Recrutement",
        "Performance": "Performances",
        "Shift and Attendance": "Quart et présence",
        "Taxes and Benefits": "Impôts et avantages",
        "Expenses": "Dépenses",
        
        # Dashboard labels from screenshots
        "Employees Relieving (This Quarter)": "Employés sur le départ (ce trimestre)",
        "Hiring vs Attrition Count": "Nombre d'embauches vs départs",
        "Employees by Age": "Employés par âge",
        "Hiring Count": "Nombre d'embauches",
        "Attrition Count": "Nombre de départs",
        "New Hires (This Month)": "Nouvelles embauches (ce mois-ci)",
        "Exits (This Month)": "Départs (ce mois-ci)",
        "Trainings (This Week)": "Formations (cette semaine)",
        "Trainings (This Month)": "Formations (ce mois-ci)",
        "Onboardings (This Month)": "Intégrations (ce mois-ci)",
        "Separations (This Month)": "Séparations (ce mois-ci)",
        "Promotions (This Month)": "Promotions (ce mois-ci)",
        "Transfers (This Month)": "Transferts (ce mois-ci)",
        "Grievance Type": "Type de grief",
        "Training Type": "Type de formation",
        "Y-O-Y Transfers": "Transferts d'une année sur l'autre",
        "Y-O-Y Promotions": "Promotions d'une année sur l'autre",
        "No Data...": "Aucune donnée...",
        
        # Core Frappe buttons and Nav from screenshots
        "List View": "Vue de liste",
        "Saved Filters": "Filtres enregistrés",
        "Add Employee": "Ajouter un employé",
        "Add {0}": "Ajouter {0}",
        "Select...": "Sélectionner...",
        "Events": "Événements",
        "What's New": "Quoi de neuf",
        "No New notifications": "Aucune nouvelle notification",
        "Looks like you haven't received any notifications.": "Il semble que vous n'ayez reçu aucune notification.",
        
        # Tabs and Headers
        "Employee Attendance": "Présence de l'employé",
        "Salary Slips": "Fiches de paie",
        "Address & Contacts": "Adresse & Contacts",
        "Leave and Attendance": "Congés et présence",
        "Tax and Benefits": "Impôts et avantages",
        "Exit": "Départ",
        
        # Missing terms from previous check
        "Joined": "Embauché",
        "Active": "Actif",
        "Inactive": "Inactif",
        "Resigned": "Démissionné",
        "Retired": "Retraité",
        "Terminated": "Licencié",
        "Current Employee Status": "Statut actuel de l'employé",
        "Date of Joining": "Date d'embauche",
        "Date of Birth": "Date de naissance",
        "Workplace": "Lieu de travail",
        
        # Empty State patterns from new screenshots
        "You haven't created a {0} yet": "Vous n'avez pas encore créé de {0}",
        "Create your first {0}": "Créez votre premier {0}",
        "No {0} found": "Aucun {0} trouvé",
        "No matching records found": "Aucun enregistrement correspondant trouvé",
        "No {0} found with matching filters. Clear filters to see all {0}.": "Aucun {0} trouvé avec les filtres correspondants. Effacez les filtres pour voir tous les {0}.",
        "Clear filters to see all {0}.": "Effacez les filtres pour voir tous les {0}.",
        "Create a new {0}": "Créer un(e) nouveau(elle) {0}",
        
        # More Workspace / Dashboard missing terms
        "Employee Attendance Tool": "Outil de présence des employés",
        "Mark Attendance": "Marquer la présence",
        "Upload Attendance": "Télécharger la présence",
        "Shift Management": "Gestion des quarts de travail",
        "Roster": "Tableau de service",
        "Holiday List": "Liste des jours fériés",
        "Insurance Details": "Détails de l'assurance",
        
        # Sidebar/Metadata and Misc Title fixes
        "Created By You": "Créé par vous",
        "Last Edited by You": "Modifié par vous pour la dernière fois",
        "Settings": "Paramètres",
        "Branch": "Branche",
        "Department": "Département",
        "Designation": "Désignation",
        "Grade": "Grade",
        "Search or type a command": "Rechercher ou taper une commande",
        "Search": "Rechercher",
        "Notification": "Notification",
        "Notifications": "Notifications",
        "Home": "Accueil",
        "Employee": "Employé",
        "Graphique organisationnel": "Organigramme",
        "Configuration": "Configuration",

        # ── HRMS PWA Mobile Interface (urgent) ──────────────────────────
        # Menu principal /hrms
        "Request Attendance": "Demander une attestation de présence",
        "Request a Shift": "Demander un créneau horaire",
        "Request Leave": "Demander un congé",
        "Claim an Expense": "Déclarer une dépense",
        "Request an Advance": "Demander une avance sur salaire",
        "View Salary Slips": "Voir mes fiches de paie",

        # Onglets / tabs PWA
        "My Requests": "Mes Demandes",
        "Team Requests": "Demandes de l'équipe",
        "You have no requests": "Vous n'avez aucune demande en cours",
        "No requests found": "Aucune demande trouvée",

        # Barre navigation inférieure HRMS
        "Attendance": "Présence",
        "Leaves": "Congés",
        "Expenses": "Dépenses",
        "Salary": "Salaire",

        # Header HRMS
        "Frappe HR": "KYA RH",
        "HRMS": "Système RH",

        # Statuts des demandes
        "Open": "En cours",
        "Approved": "Approuvé",
        "Rejected": "Rejeté",
        "Pending": "En attente",
        "Cancelled": "Annulé",
        "Draft": "Brouillon",

        # Formulaires congés PWA
        "Leave Application": "Demande de Congé",
        "Leave Type": "Type de Congé",
        "From Date": "Date de début",
        "To Date": "Date de fin",
        "Half Day": "Demi-journée",
        "Reason": "Motif",
        "Leave Balance": "Solde de Congés",
        "Available Leaves": "Congés disponibles",
        "Total Leave Days": "Nombre de jours",
        "Leave Approver": "Approbateur de congé",
        "Follow Through": "Suivi",
        "Apply": "Valider",
        "Submit": "Soumettre",
        "Cancel": "Annuler",

        # Formulaire présence PWA
        "Attendance Request": "Demande de présence",
        "Explanation": "Explication",
        "Shift": "Créneau",
        "Work From Home": "Télétravail",
        "On Duty": "En service",

        # Formulaire avance / dépenses PWA
        "Expense Claim": "Note de frais",
        "Expense Type": "Type de dépense",
        "Amount": "Montant",
        "Total Claimed Amount": "Montant total réclamé",
        "Total Sanctioned Amount": "Montant total approuvé",
        "Employee Advance": "Avance employé",
        "Purpose": "Objet",
        "Advance Amount": "Montant de l'avance",
        "Mode of Payment": "Mode de paiement",
        "Repay Unclaimed Amount from Salary": "Déduire le montant non réclamé du salaire",

        # Fiches de paie PWA
        "Salary Slip": "Fiche de Paie",
        "Gross Pay": "Salaire brut",
        "Net Pay": "Salaire net",
        "Total Deduction": "Total des déductions",
        "Month": "Mois",
        "Year": "Année",
        "Earnings": "Revenus",
        "Deductions": "Déductions",
        "Download": "Télécharger",

        # Messages d'état généraux PWA
        "Loading...": "Chargement...",
        "Save": "Enregistrer",
        "Edit": "Modifier",
        "Delete": "Supprimer",
        "Back": "Retour",
        "Close": "Fermer",
        "Confirm": "Confirmer",
        "Are you sure?": "Êtes-vous sûr(e) ?",
        "Success": "Succès",
        "Error": "Erreur",
        "Warning": "Avertissement",
        "Update": "Mettre à jour",
        "New": "Nouveau",
        "View All": "Voir tout",
        "See All": "Voir tout",
        "Show More": "Afficher plus",
        "No Data": "Aucune donnée",
        "Today": "Aujourd'hui",
        "This Week": "Cette semaine",
        "This Month": "Ce mois-ci",

        # Additional MISSING PWA strings from user feedback
        "Expense Claim Summary": "Résumé des notes de frais",
        "Recent Expenses": "Dépenses récentes",
        "Employee Advance Balance": "Solde d'avance de l'employé",
        "You have no advances": "Vous n'avez pas d'avances",
        "Congés et jours non travaillés": "Congés et jours non travaillés", # Already FR but for completeness
        "Solde de Congés": "Solde de Congés", # Already FR
        "View Leave History": "Voir l'historique des congés",
        "Recent Leaves": "Congés récents",
        "Upcoming Holidays": "Congés à venir",
        "You have no upcoming holidays": "Vous n'avez pas de congés à venir",
        "Total Amount Claimed": "Montant total réclamé",
        "Wait": "En attente",
        "Approved": "Approuvé",
        "Rejected": "Rejeté",
        "Request a Leave": "Demander un congé",
        "Declaring a expense": "Déclarer une dépense",
        "Claim an Expense": "Déclarer une dépense",
        "See the List": "Voir la liste",
        "Voir La Liste": "Voir la liste",
    }
    
    for k, v in overrides.items():
        translations[k] = v

    # 3. Sort for consistency
    sorted_keys = sorted(translations.keys())
    
    # 4. Write back to fr.csv in PURE UTF-8
    try:
        print(f"Writing {len(translations)} translations to {os.path.basename(fr_csv)}...")
        with open(fr_csv, 'w', encoding='utf-8', newline='') as f:
            # Frappe likes all fields quoted
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            for key in sorted_keys:
                writer.writerow([key, translations[key]])
        print("File write complete!")
    except PermissionError:
        print(f"⚠️ Permission denied for {fr_csv}. Skipping file write (database sync will proceed).")
    except Exception as e:
        print(f"⚠️ Error writing file: {e}")

    print("Repair logic execution finished!")

    # Write to database if in frappe environment
    try:
        import frappe
        if frappe.db:
            print("Syncing translations to database...")
            for key, val in translations.items():
                if key and val:
                    # Update or insert into tabTranslation
                    if not frappe.db.exists("Translation", {"source_text": key, "language": "fr"}):
                        frappe.get_doc({
                            "doctype": "Translation",
                            "language": "fr",
                            "source_text": key,
                            "translated_text": val
                        }).insert(ignore_permissions=True)
                    else:
                        frappe.db.set_value("Translation", {"source_text": key, "language": "fr"}, "translated_text", val)
            
            # Translate specific Notifications
            notifications_to_fix = {
                "Exit Interview Scheduled": ("Entretien de sortie planifi\u00e9", "Entretien de sortie planifi\u00e9: {{ doc.name }}"),
                "Material Request Receipt Notification": ("Notification de r\u00e9ception de mat\u00e9riel", "{{ doc.name }} a \u00e9t\u00e9 re\u00e7u"),
                "Retention Bonus": ("Prime de fid\u00e9lisation", "Alerte de prime de fid\u00e9lisation pour {{ doc.employee }}"),
                "Notification for new fiscal year": ("Nouvelle ann\u00e9e fiscale", "Notification pour la nouvelle ann\u00e9e fiscale {{ doc.name }}"),
                "Training Feedback": ("Commentaires sur la formation", "Merci de partager vos commentaires sur {{ doc.training_event }}"),
                "Training Scheduled": ("Formation planifi\u00e9e", "Formation planifi\u00e9e: {{ doc.name }}")
            }
            
            for notif_name, (new_subject, new_msg_prefix) in notifications_to_fix.items():
                if frappe.db.exists("Notification", notif_name):
                    frappe.db.set_value("Notification", notif_name, "subject", new_subject)
                    # We only update subject to keep it simple and avoid breaking complex message templates
            
            frappe.db.commit()
            print("✅ Database sync complete")
    except ImportError:
        pass

def execute():
    repair_ultra()

if __name__ == "__main__":
    repair_ultra()

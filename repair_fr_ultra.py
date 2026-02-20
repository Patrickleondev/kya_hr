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
        
        # Core Frappe buttons from screenshots
        "List View": "Vue de liste",
        "Saved Filters": "Filtres enregistrés",
        "Add Employee": "Ajouter un employé",
        "Add Employee": "Ajouter un Employé",
        "Add {0}": "Ajouter {0}",
        "Select...": "Sélectionner...",
        
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
    }
    
    for k, v in overrides.items():
        translations[k] = v

    # 3. Sort for consistency
    sorted_keys = sorted(translations.keys())
    
    # 4. Write back to fr.csv in PURE UTF-8
    print(f"Writing {len(translations)} translations to {os.path.basename(fr_csv)}...")
    with open(fr_csv, 'w', encoding='utf-8', newline='') as f:
        # Frappe likes all fields quoted
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        for key in sorted_keys:
            writer.writerow([key, translations[key]])

    print("Repair complete!")

if __name__ == "__main__":
    repair_ultra()

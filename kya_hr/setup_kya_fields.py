import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_fields():
    """
    Ajoute les champs de classification professionnelle KYA-Energy Group
    au DocType 'Employee' selon les images fournies.
    """
    fields = {
        "Employee": [
            {
                "fieldname": "custom_kya_section",
                "label": "Classification Professionnelle",
                "fieldtype": "Section Break",
                "insert_after": "designation"
            },
            {
                "fieldname": "custom_kya_categorie",
                "label": "Catégorie",
                "fieldtype": "Select",
                "options": "\nAgents d'exécution (AE)\nAgents de maîtrise\nCadres\nHauts Cadres (HC)",
                "insert_after": "custom_kya_section"
            },
            {
                "fieldname": "custom_kya_classe",
                "label": "Classe",
                "fieldtype": "Select",
                "options": "\nA\nB\nC\nD\nH\nI\nJ\nK\nL\nM\nN\nO\nP",
                "insert_after": "custom_kya_categorie"
            },
            {
                "fieldname": "custom_kya_echelon",
                "label": "Échelon",
                "fieldtype": "Select",
                "options": "\n1\n2\n3",
                "insert_after": "custom_kya_classe",
                "description": "Nombre de bonification d'échelons (max 3)"
            },
            {
                "fieldname": "custom_kya_indice",
                "label": "Valeur Indicielle",
                "fieldtype": "Int",
                "insert_after": "custom_kya_echelon",
                "description": "Indice issu de la grille salariale"
            }
        ]
    }
    
    create_custom_fields(fields)
    frappe.db.commit()
    print("Personnalisations KYA appliquées avec succès à la fiche Employé !")

if __name__ == "__main__":
    setup_fields()

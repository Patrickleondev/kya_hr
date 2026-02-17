import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_insurance_fields():
    """
    Ajoute les champs d'Assurance Santé à la fiche Employé.
    """
    fields = {
        "Employee": [
            {
                "fieldname": "custom_assurance_section",
                "label": "Assurances et Santé",
                "fieldtype": "Section Break",
                "insert_after": "custom_kya_indice"
            },
            {
                "fieldname": "custom_assurance_type",
                "label": "Type d'Assurance Santé",
                "fieldtype": "Select",
                "options": "\nAucune\nAssurance Maladie Universelle (AMU)\nAssurance Privée\nConvention Entreprise",
                "insert_after": "custom_assurance_section"
            },
            {
                "fieldname": "custom_assurance_numero",
                "label": "Numéro d'Affiliation Assurance",
                "fieldtype": "Data",
                "insert_after": "custom_assurance_type"
            },
            {
                "fieldname": "custom_assurance_compagnie",
                "label": "Compagnie d'Assurance",
                "fieldtype": "Data",
                "insert_after": "custom_assurance_numero",
                "depends_on": "eval:doc.custom_assurance_type == 'Assurance Privée'"
            }
        ]
    }
    
    create_custom_fields(fields)
    frappe.db.commit()
    print("Champs d'Assurance Santé ajoutés avec succès !")

if __name__ == "__main__":
    setup_insurance_fields()

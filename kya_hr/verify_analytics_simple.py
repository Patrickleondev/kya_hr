
import frappe
import json

def verify():
    targets = {
        "Charts": [
            "Répartition par Statut Stagiaire", 
            "Permissions par Mois", 
            "Consommation Carburant par Véhicule", 
            "Utilisation des Véhicules (Sorties)"
        ],
        "NumberCards": [
            "Stagiaires Actifs", 
            "Permissions en Attente", 
            "Tickets de Sortie du Jour"
        ]
    }
    
    results = {
        "Charts": [c for c in targets["Charts"] if frappe.db.exists("Dashboard Chart", c)],
        "NumberCards": [c for c in targets["NumberCards"] if frappe.db.exists("Number Card", c)]
    }
    
    print("---ANALYTICS_VERIF---")
    print(json.dumps(results, indent=2))
    print("---END_ANALYTICS_VERIF---")

if __name__ == "__main__":
    verify()

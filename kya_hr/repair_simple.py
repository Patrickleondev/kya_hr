
import frappe

def main():
    overrides = {
        "Home": "Accueil",
        "Employee": "Employé",
        "ccueil": "Accueil",
        "àccueil": "Accueil",
        "ànalyse": "Analyse",
        "àutres": "Autres",
        "ànniversaire": "Anniversaire",
        "Analyse": "Analyse",
        "Anniversaire": "Anniversaire",
        "Autres rapports": "Autres rapports",
        "Analyse de recrutement": "Analyse de recrutement",
        "Analyse des employés": "Analyse des employés",
        "Anniversaire de l'employé": "Anniversaire de l'employé",
        "Reports": "Rapports",
        "Key Reports": "Rapports clés",
        "other reports": "autres rapports"
    }

    print("Syncing translations...")
    for key, val in overrides.items():
        if frappe.db.exists("Translation", {"source_text": key, "language": "fr"}):
            frappe.db.set_value("Translation", {"source_text": key, "language": "fr"}, "translated_text", val)
            print(f"Updated: {key} -> {val}")
        else:
            frappe.get_doc({
                "doctype": "Translation",
                "language": "fr",
                "source_text": key,
                "translated_text": val
            }).insert(ignore_permissions=True)
            print(f"Inserted: {key} -> {val}")
    
    frappe.db.commit()
    print("✅ Sync complete")

if __name__ == "__main__":
    main()

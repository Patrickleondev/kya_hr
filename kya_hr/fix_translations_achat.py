import frappe

def main():
    overrides = {
        "éhat": "Achat",
        "éhats": "Achats",
        "étifs - Immo.": "Actifs - Immo.",
        "étif": "Actif",
        "étifs": "Actifs",
        "Achat": "Achat",
        "Achats": "Achats",
        "Actif": "Actif",
        "Actifs": "Actifs",
        "Actifs - Immo.": "Actifs - Immo."
    }

    print("Fixing translations...")
    for key, val in overrides.items():
        frappe.db.sql("UPDATE tabTranslation SET translated_text = %s WHERE translated_text = %s", (val, key))
        if not frappe.db.exists("Translation", {"source_text": val, "language": "fr"}):
            frappe.get_doc({"doctype": "Translation", "language": "fr", "source_text": val, "translated_text": val}).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Translation", {"source_text": val, "language": "fr"}, "translated_text", val)

    workspaces = frappe.get_all("Workspace", filters={"label": ("like", "é%")}, fields=["name", "label"])
    for ws in workspaces:
        new_label = ws.label.replace("éhat", "Achat").replace("étif", "Actif")
        if new_label != ws.label:
            frappe.db.set_value("Workspace", ws.name, "label", new_label)
            print(f"Fixed Workspace: {ws.label} -> {new_label}")

    frappe.db.commit()
    print("✅ Translation fix complete.")

if __name__ == "__main__":
    main()

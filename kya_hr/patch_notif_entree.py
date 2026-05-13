"""Fix notification for PV Entree — replace Magasin condition with Achats & Stock."""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "fixtures", "notification.json")

with open(PATH, encoding="utf-8") as f:
    notifs = json.load(f)

changes = 0
for n in notifs:
    if n.get("name") == "KYA - PV Entrée Matériel: En attente Magasin":
        n["name"] = "KYA - PV Réception Matériel: En attente Achats & Stock"
        n["subject"] = "PV Réception {{ doc.name }} — Validation Achats & Stock requise"
        n["condition"] = "doc.workflow_state == 'En attente Achats & Stock'"
        n["recipients"] = [
            {"receiver_by_role": "Chargé des Stocks"},
            {"receiver_by_role": "Responsable Achats"},
        ]
        # Update message body
        n["message"] = n["message"].replace(
            "nÃ©cessite la validation du magasin",
            "nécessite la validation Achats &amp; Stock"
        ).replace(
            "nécessite la validation du magasin",
            "nécessite la validation Achats &amp; Stock"
        ).replace(
            "Contrôler et signer",
            "Valider Réception Stock"
        )
        changes += 1
    # Also fix the "Approuvé" notification label
    if n.get("name") == "KYA - PV Entrée Matériel: Approuvé":
        n["name"] = "KYA - PV Réception Matériel: Approuvé"
        n["subject"] = "PV Réception {{ doc.name }} — Stock mis à jour ✓"
        changes += 1
    if n.get("name") == "KYA - PV Entrée Matériel: Rejeté":
        n["name"] = "KYA - PV Réception Matériel: Rejeté"
        changes += 1
    # Rename Comptable/Audit notifications too
    if n.get("name") == "KYA - PV Entrée Matériel: En attente Comptable":
        n["name"] = "KYA - PV Réception Matériel: En attente Comptable"
        changes += 1
    if n.get("name") == "KYA - PV Entrée Matériel: En attente Audit":
        n["name"] = "KYA - PV Réception Matériel: En attente Audit"
        changes += 1

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(notifs, f, ensure_ascii=False, indent=1)
print(f"Updated {changes} notification(s). Total: {len(notifs)}")

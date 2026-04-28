"""Force publication des Web Forms KYA après migration.

Problème : les web forms ont `is_standard: 1` (nécessaire pour fixtures Git),
ce qui rend le bouton "Publier" inactif en UI. Cette tâche after_migrate
force `published=1` directement en DB pour tous les webforms KYA et clear le
cache.

Hook : `after_migrate` dans hooks.py
"""
import frappe


# Liste blanche des webforms KYA à toujours garder publiés
KYA_WEB_FORMS = [
    "permission-sortie-employe",
    "permission-sortie-stagiaire",
    "pv-sortie-materiel",
    "pv-entree-materiel",
    "demande-achat",
    "appel-offre",
    "bon-commande",
    "inventaire-kya",
    "brouillard-caisse",
    "etat-recap",
    "demande-conge",
    "planning-conge",
]

# Webforms à dépublier (obsolètes ou désactivés)
KYA_WEB_FORMS_UNPUBLISH = [
    "bilan-fin-de-stage",
]


def execute():
    """Force publication/dépublication des webforms KYA."""
    if not frappe.db.has_table("Web Form"):
        return

    published = []
    unpublished = []
    not_found = []

    for route in KYA_WEB_FORMS:
        # Webform name == route in our fixtures
        names = frappe.db.get_all(
            "Web Form",
            filters={"route": route},
            fields=["name", "published"],
        )
        if not names:
            # Try by name match
            if frappe.db.exists("Web Form", route):
                names = [{"name": route, "published": frappe.db.get_value("Web Form", route, "published")}]
        if not names:
            not_found.append(route)
            continue
        for n in names:
            if not n.get("published"):
                frappe.db.set_value("Web Form", n["name"], "published", 1, update_modified=False)
                published.append(n["name"])

    for route in KYA_WEB_FORMS_UNPUBLISH:
        names = frappe.db.get_all(
            "Web Form",
            filters={"route": route},
            fields=["name", "published"],
        )
        for n in names:
            if n.get("published"):
                frappe.db.set_value("Web Form", n["name"], "published", 0, update_modified=False)
                unpublished.append(n["name"])

    frappe.db.commit()
    frappe.clear_cache()

    print(f"[kya_hr.force_publish_webforms] Publiés: {len(published)} - {published}")
    if unpublished:
        print(f"[kya_hr.force_publish_webforms] Dépubliés: {unpublished}")
    if not_found:
        print(f"[kya_hr.force_publish_webforms] ⚠️ Introuvables: {not_found}")

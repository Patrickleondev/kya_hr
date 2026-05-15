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
    "comptabilite-import",
    "demande-conge",
    "planning-conge",
    "bilan-fin-de-stage",
]

# Webforms à dépublier (obsolètes ou désactivés)
KYA_WEB_FORMS_UNPUBLISH = []


def execute():
    """Force publication/dépublication des webforms KYA + reload des fields.

    Frappe v16 ne re-sync pas automatiquement les `Web Form Field` enfants
    lorsqu'on modifie le JSON source — `bench migrate` ignore les changements
    de child tables sur les fixtures `is_standard:1`. On force donc un
    `reload_doc` explicite pour chaque web form KYA, ce qui réimporte
    le JSON et reconstruit la table `Web Form Field`.
    """
    if not frappe.db.has_table("Web Form"):
        return

    published = []
    unpublished = []
    not_found = []
    reloaded = []
    reload_errors = []

    # Mapping route (= name BDD avec tirets) → nom de dossier (underscores)
    # Pour la majorité, c'est juste route.replace('-', '_')
    for route in KYA_WEB_FORMS:
        folder_name = route.replace("-", "_")
        try:
            frappe.reload_doc("kya_hr", "web_form", folder_name)
            reloaded.append(route)
        except Exception as exc:  # pylint: disable=broad-except
            reload_errors.append((route, str(exc)))

    for route in KYA_WEB_FORMS:
        names = frappe.db.get_all(
            "Web Form",
            filters={"route": route},
            fields=["name", "published"],
        )
        if not names:
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

    print(f"[kya_hr.force_publish_webforms] Reloaded: {len(reloaded)} web forms")
    if reload_errors:
        print(f"[kya_hr.force_publish_webforms] ⚠️ Reload errors: {reload_errors}")
    print(f"[kya_hr.force_publish_webforms] Publiés: {len(published)} - {published}")
    if unpublished:
        print(f"[kya_hr.force_publish_webforms] Dépubliés: {unpublished}")
    if not_found:
        print(f"[kya_hr.force_publish_webforms] ⚠️ Introuvables: {not_found}")

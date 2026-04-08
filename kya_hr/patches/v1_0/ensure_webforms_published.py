"""
Patch: ensure_webforms_published
Garantit que tous les web forms KYA sont published=1 et login_required=1.
Corrige tout reset accidentel lors des migrations.
"""

import frappe

KYA_WEBFORMS = [
    "permission-sortie-employe",
    "permission-sortie-stagiaire",
    "pv-sortie-materiel",
    "demande-achat",
    "planning-conge",
    "bilan-fin-de-stage",
]


def execute():
    for route in KYA_WEBFORMS:
        if frappe.db.exists("Web Form", route):
            frappe.db.sql(
                "UPDATE `tabWeb Form` SET published=1, login_required=1, modified=NOW() WHERE name=%s",
                (route,),
            )
    frappe.db.commit()
    frappe.logger().info("[kya_hr] Web Forms KYA — published=1 forcé sur %d formulaires" % len(KYA_WEBFORMS))

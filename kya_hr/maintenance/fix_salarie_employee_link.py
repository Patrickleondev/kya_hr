# Copyright (c) 2026, KYA-Energy Group
"""Récupère l'ancien champ `employee` de Salarie KYA vers `employee_link`.

`Salarie KYA` a porté un moment DEUX liens vers la fiche Employee : le champ
historique `employee_link` (« Fiche Employé liée (ERPNext) », visible dans la
section Divers) et un champ `employee` ajouté par erreur avec la
synchronisation Employee → Salarié. Résultat : la synchronisation remplissait
un champ, et la RH en voyait un autre, resté vide.

Le champ en double a été retiré du DocType. Sa colonne, elle, survit en base
tant qu'on ne la supprime pas : ce script recopie les valeurs vers le bon
champ avant qu'elles ne deviennent inaccessibles. Idempotent — une fois la
colonne disparue, il ne fait plus rien.
"""
import frappe


def execute():
    table = "tabSalarie KYA"
    colonnes = {c["Field"] if isinstance(c, dict) else c[0]
                for c in frappe.db.sql("DESC `%s`" % table, as_dict=True)}
    if "employee" not in colonnes or "employee_link" not in colonnes:
        return {"recuperes": 0, "raison": "colonne absente"}

    # On ne remplace jamais un lien déjà posé : l'ancien champ ne sert que de
    # source de secours pour les fiches où le bon champ est resté vide.
    a_reprendre = frappe.db.sql("""
        SELECT name, employee FROM `tabSalarie KYA`
         WHERE IFNULL(employee, '') != '' AND IFNULL(employee_link, '') = ''
    """, as_dict=True)
    for row in a_reprendre:
        frappe.db.set_value("Salarie KYA", row["name"], "employee_link",
                            row["employee"], update_modified=False)
    frappe.db.commit()
    return {"recuperes": len(a_reprendre)}

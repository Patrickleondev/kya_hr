# -*- coding: utf-8 -*-
"""Supprime les Custom Fields qui font DOUBLON avec un champ standard.

Contexte (juillet 2026) : sans déploiement possible, des champs ont été créés
en prod en tant que Custom Fields via l'API (Fiche de Poste KYA :
identification + signatures ; Contrat Stage Immersion KYA : circuit digital).
Ces mêmes champs existent comme champs STANDARDS dans le JSON des DocTypes du
repo. Au premier vrai `bench migrate`, le champ arriverait en double dans le
meta (standard + custom) → formulaire cassé / champ affiché deux fois.

Cette étape s'exécute en before_migrate (AVANT le sync des DocTypes) : pour
chaque DocType custom=0 de kya_hr, tout Custom Field dont le fieldname est
déjà un champ standard du JSON source est supprimé. La COLONNE en base n'est
pas touchée (Frappe ne droppe pas les colonnes à la suppression d'un Custom
Field) : les données saisies (ex. les 33 fiches de poste) sont préservées et
récupérées telles quelles par le champ standard.

No-op sur une installation fraîche (aucun Custom Field préexistant).
Ne lève JAMAIS : un échec est loggé et la migration continue.
"""
from __future__ import annotations

import json
import os

import frappe


def execute() -> None:
    try:
        _execute()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "remove_shadowing_custom_fields: échec global (non bloquant)",
        )
        print("[remove_shadowing_custom_fields] FAILED (voir Error Log), migration poursuivie.")


def _execute() -> None:
    base = frappe.get_app_path("kya_hr", "doctype")
    if not os.path.isdir(base):
        return

    removed = []
    for d in sorted(os.listdir(base)):
        json_path = os.path.join(base, d, d + ".json")
        if not os.path.exists(json_path):
            continue
        try:
            with open(json_path, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue
        if meta.get("custom"):
            # custom=1 : les champs vivent en base, pas dans le JSON — hors sujet.
            continue
        dt = meta.get("name")
        standard = {fld.get("fieldname") for fld in meta.get("fields", []) if fld.get("fieldname")}
        if not dt or not standard:
            continue

        for cf in frappe.get_all(
            "Custom Field", filters={"dt": dt}, fields=["name", "fieldname"]
        ):
            if cf.fieldname in standard:
                frappe.delete_doc(
                    "Custom Field", cf.name,
                    ignore_permissions=True, force=True, ignore_missing=True,
                )
                removed.append(f"{dt}.{cf.fieldname}")

    if removed:
        frappe.db.commit()
        frappe.clear_cache()
        print(
            "[remove_shadowing_custom_fields] %d Custom Field(s) en doublon d'un champ "
            "standard supprimé(s) (colonnes/données conservées) : %s"
            % (len(removed), ", ".join(removed))
        )

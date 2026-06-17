# -*- coding: utf-8 -*-
"""Formation v2 — alignement sur le modèle RH réel (fichiers PROPOSITIONS_FORMATIONS).

Les DocTypes (custom=0) se synchronisent depuis leur JSON au migrate : nouveaux
champs côté chef (besoin_exprime, objectif), côté plan compilé (nature_action,
objectifs_vises, resultats_attendus, source_deploiement, modalite, cout_direct,
cout_accessoire) et la nouvelle table `beneficiaires` (Plan Formation Beneficiaire)
pour le SUIVI PAR EMPLOYÉ.

Ce script idempotent se contente de RÉCONCILIER les données existantes après
sync : coût total des lignes = direct + accessoire, et compteurs de bénéficiaires
sur les plans déjà présents. Branché dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe
from frappe.utils import flt


def execute() -> dict:
    out = {"plans": 0, "lignes_cout": 0, "beneficiaires": 0, "warn": []}

    if not frappe.db.exists("DocType", "Plan Formation Beneficiaire"):
        out["warn"].append("Plan Formation Beneficiaire absent (sync migrate non joué ?)")

    if not frappe.db.exists("DocType", "Plan de Formation"):
        return out

    for name in frappe.get_all("Plan de Formation", pluck="name"):
        try:
            changed = False
            # coût total ligne = direct + accessoire (sans réécrire si déjà bon)
            for li in frappe.get_all("Plan Formation Item",
                                     filters={"parent": name},
                                     fields=["name", "cout_direct", "cout_accessoire", "cout"]):
                total = flt(li.cout_direct) + flt(li.cout_accessoire)
                # si le chiffrage v1 n'avait qu'un coût unique, on le préserve comme direct
                if total == 0 and flt(li.cout) > 0:
                    frappe.db.set_value("Plan Formation Item", li.name,
                                        {"cout_direct": flt(li.cout)}, update_modified=False)
                    out["lignes_cout"] += 1
                    changed = True
                elif flt(li.cout) != total:
                    frappe.db.set_value("Plan Formation Item", li.name,
                                        {"cout": total}, update_modified=False)
                    out["lignes_cout"] += 1
                    changed = True

            nb = frappe.db.count("Plan Formation Beneficiaire", {"parent": name}) \
                if frappe.db.exists("DocType", "Plan Formation Beneficiaire") else 0
            nb_t = frappe.db.count("Plan Formation Beneficiaire",
                                   {"parent": name, "statut": "Terminé"}) if nb else 0
            cur = frappe.db.get_value("Plan de Formation", name,
                                      ["nb_beneficiaires", "nb_beneficiaires_termines"], as_dict=True)
            if cur and (cur.nb_beneficiaires != nb or cur.nb_beneficiaires_termines != nb_t):
                frappe.db.set_value("Plan de Formation", name,
                                    {"nb_beneficiaires": nb, "nb_beneficiaires_termines": nb_t},
                                    update_modified=False)
                out["beneficiaires"] += 1
                changed = True
            if changed:
                out["plans"] += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"ensure_formation_v2: {name}")

    frappe.db.commit()
    print(f"[ensure_formation_v2] plans_maj={out['plans']} couts={out['lignes_cout']} "
          f"benef_counts={out['beneficiaires']} warn={out['warn']}")
    return out

# -*- coding: utf-8 -*-
"""Installe/synchronise les DocTypes comptables MAISON KYA (custom=1) + leurs
formats d'impression, et pose un barème de paie par défaut si la config est vide.

Contexte : Frappe ne resynchronise PAS depuis le disque les DocTypes marqués
`custom: 1` lors d'un `bench migrate` (contrairement aux DocTypes standard).
Sans cette étape, un déploiement prod (git merge + migrate) laisserait ces
tables absentes → la Facturation, le Grand Livre et la Paie ne fonctionneraient
pas. On force donc l'import depuis les JSON du repo (repo = source de vérité),
de façon idempotente.

Couvre :
- Facturation : Facture KYA (+ Facture KYA Item) + PF « Facture KYA Officiel »
- Grand Livre : Ecriture Comptable KYA
- Paie        : Parametres Paie KYA + tables (Tranche IRPP / Retenue / Prime /
                Ligne Prime Bulletin) + Bulletin Paie KYA
                + PF « Bulletin Paie KYA Officiel »
"""
from __future__ import annotations

import os

import frappe
from frappe.modules.import_file import import_file_by_path

# Ordre = dépendances d'abord (tables enfants avant parents).
_DOCTYPES = [
    ("facture_kya_item", "Facture KYA Item"),
    ("facture_kya", "Facture KYA"),
    ("ecriture_comptable_kya", "Ecriture Comptable KYA"),
    ("tranche_irpp_kya", "Tranche IRPP KYA"),
    ("retenue_paie_kya", "Retenue Paie KYA"),
    ("prime_paie_kya", "Prime Paie KYA"),
    ("ligne_prime_bulletin_kya", "Ligne Prime Bulletin KYA"),
    ("parametres_paie_kya", "Parametres Paie KYA"),
    ("bulletin_paie_kya", "Bulletin Paie KYA"),
]

_PRINT_FORMATS = [
    ("facture_kya_officiel", "Facture KYA Officiel"),
    ("bulletin_paie_kya_officiel", "Bulletin Paie KYA Officiel"),
]

# Barème IRPP mensuel par défaut (indicatif Togo) — le Comptable l'ajuste dans
# « Parametres Paie KYA ». Posé UNIQUEMENT si le barème est vide.
_BAREME_DEFAUT = [
    (0, 60000, 0), (60000, 150000, 7), (150000, 300000, 15),
    (300000, 500000, 25), (500000, 800000, 30), (800000, 0, 35),
]


# Racine du module kya_hr (…/apps/kya_hr/kya_hr), déduite de ce fichier
# (…/kya_hr/maintenance/setup_compta_maison.py) — robuste, indépendant de
# frappe.get_app_path.
_KYA_HR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _import(rel_parts, name, kind):
    path = os.path.join(_KYA_HR, *rel_parts)
    if not os.path.exists(path):
        return "absent"
    try:
        import_file_by_path(path, force=True, ignore_version=True)
        return "ok"
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"setup_compta_maison: import {kind} {name}")
        return "erreur"


def execute() -> dict:
    out = {"doctypes": 0, "print_formats": 0, "bareme": "inchangé", "erreurs": []}

    for folder, name in _DOCTYPES:
        st = _import(["doctype", folder, folder + ".json"], name, "doctype")
        if st == "ok":
            out["doctypes"] += 1
        elif st == "erreur":
            out["erreurs"].append(name)

    for folder, name in _PRINT_FORMATS:
        st = _import(["print_format", folder, folder + ".json"], name, "print_format")
        if st == "ok":
            out["print_formats"] += 1
        elif st == "erreur":
            out["erreurs"].append(name)

    # Barème de paie par défaut (seulement si vide → n'écrase jamais la config
    # saisie par le Comptable).
    try:
        if frappe.db.exists("DocType", "Parametres Paie KYA"):
            cfg = frappe.get_single("Parametres Paie KYA")
            if not cfg.get("irpp_bareme"):
                for lo, hi, tx in _BAREME_DEFAUT:
                    cfg.append("irpp_bareme",
                               {"tranche_min": lo, "tranche_max": hi, "taux": tx})
                cfg.flags.ignore_permissions = True
                cfg.save(ignore_permissions=True)
                out["bareme"] = "barème par défaut posé"
    except Exception:
        frappe.log_error(frappe.get_traceback(), "setup_compta_maison: barème")

    frappe.db.commit()
    print("[setup_compta_maison] %s" % out)
    return out

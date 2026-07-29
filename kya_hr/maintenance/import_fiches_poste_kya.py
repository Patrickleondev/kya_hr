# -*- coding: utf-8 -*-
"""Importe le contenu officiel du catalogue KYA-ORG-CIBLE-01 (33 fiches de
poste FP-01..FP-33, fourni par la RH — cf. kya_hr/data/fiches_poste_kya_catalogue.json)
dans le DocType « Fiche de Poste KYA ».

Contexte : ~61 Fiche de Poste KYA existent déjà en base (une par employé,
créées en masse le 26/07/2026), quasiment toutes VIDES (mission/attributions/
indicateurs/profil non renseignés) — c'est cette absence de contenu que la
RH a remontée comme « fiches incomplètes ». Le catalogue RH ne couvre que les
postes d'encadrement (DG, Directeurs, Chefs de Service…) : seule une minorité
des 61 employés y correspond.

Deux cas traités :
  1. CONFIDENT_MATCHES — un employé actuel occupe déjà, sans ambiguïté, l'un
     des 33 postes du catalogue (même intitulé). On enrichit SA fiche
     existante avec le contenu (mission/attributions/autorité/indicateurs/
     profil/interfaces), sans jamais écraser un champ déjà rempli par
     quelqu'un (idempotent, non destructif).
  2. Les 29 autres postes du catalogue n'ont pas encore de titulaire réel —
     la réorganisation (décision 2026-010/011) qui leur donnerait un nom n'est
     PAS encore exécutée (cf. reorg_juillet_2026.py, en attente). On les crée
     comme MODÈLES DE POSTE (champ « employee » vide), prêts à être assignés
     plus tard. `employee` n'est plus obligatoire sur ce DocType depuis ce
     correctif (Property Setter en attendant le déploiement, cf. JSON).

Le champ « Identification » du catalogue (Classification, Plafond
d'engagement, Instances, Encadrement direct, Effectif sous responsabilité,
Suppléance) n'est écrit QUE si les champs correspondants existent sur le site
cible (ajoutés au JSON du DocType le 28/07/2026 ; absents en prod tant que le
déploiement n'a pas eu lieu — cf. import_identification()).

Appelé par safe_migrations.AFTER_MIGRATE. Idempotent : ne recrée jamais un
modèle déjà présent (matché par intitule_poste sans employé), n'écrase jamais
une fiche employé dont la mission est déjà renseignée.
"""
from __future__ import annotations

import json

import frappe

_DATA = "data/fiches_poste_kya_catalogue.json"

# code_fp du catalogue -> employé actuel occupant sans ambiguïté ce poste
# (même intitulé/désignation). Vérifié manuellement le 28/07/2026.
CONFIDENT_MATCHES = {
    "FP-01": "HR-EMP-00001",  # AZOUMAH, DIRECTEUR GENERAL
    "FP-02": "HR-EMP-00066",  # LAWSON, DIRECTEUR G. ADJOINT
    "FP-13": "HR-EMP-00002",  # MESSAN, RESP. INFO & LOGICIEL
    "FP-25": "HR-EMP-00059",  # AMEOGNO Akossiwa, RESP. ACHAT & APPROV
}

_IDENT_FIELDS = {
    "Classification": "classification",
    "Effectif sous responsabilité": "effectif_responsabilite",
    "Plafond d'engagement": "plafond_engagement",
    "Suppléance": "suppleance",
    "Encadrement direct": "encadrement_direct",
    "Instances": "instances",
}


def _load_catalogue():
    path = frappe.get_app_path("kya_hr", _DATA)
    with open(path, encoding="utf-8") as f:
        return {d["code_fp"]: d for d in json.load(f)}


def _content_fields(entry: dict) -> dict:
    p = entry.get("profil") or {}
    out = {
        "mission": entry.get("mission") or "",
        "autorite": entry.get("autorite") or "",
        "formation": p.get("formation") or "",
        "experience": p.get("experience") or "",
        "competences_techniques": p.get("competences_techniques") or "",
        "competences_comportementales": p.get("competences_comportementales") or "",
        "langues": p.get("langues") or "",
        "interfaces": entry.get("interfaces") or "",
        "attributions": [
            {"domaine": a.get("domaine") or "", "activites": a.get("activites") or ""}
            for a in entry.get("attributions") or []
        ],
        "indicateurs": [
            {
                "indicateur": i.get("indicateur") or "",
                "cible": i.get("cible") or "",
                "frequence": i.get("frequence") or "",
                "poids": i.get("poids") or "",
            }
            for i in entry.get("indicateurs") or []
        ],
    }
    ident = entry.get("identification") or {}
    meta_fields = {f.fieldname for f in frappe.get_meta("Fiche de Poste KYA").fields}
    for label, fieldname in _IDENT_FIELDS.items():
        if fieldname in meta_fields and ident.get(label):
            out[fieldname] = ident[label]
    return out


def execute() -> dict:
    frappe.set_user("Administrator")
    report = {"enrichis": [], "crees": [], "ignores_deja_rempli": [], "ignores_deja_cree": [], "erreurs": []}
    try:
        catalogue = _load_catalogue()
    except Exception as e:
        report["erreurs"].append(f"chargement catalogue: {e}")
        return report

    # 1) Fiches employé existantes -> enrichissement (jamais d'écrasement).
    for code, employee in CONFIDENT_MATCHES.items():
        entry = catalogue.get(code)
        if not entry:
            continue
        name = frappe.db.get_value("Fiche de Poste KYA", {"employee": employee})
        if not name:
            continue
        try:
            doc = frappe.get_doc("Fiche de Poste KYA", name)
            if (doc.mission or "").strip():
                report["ignores_deja_rempli"].append(f"{code} ({name}) : mission déjà renseignée")
                continue
            doc.update(_content_fields(entry))
            doc.save(ignore_permissions=True)
            report["enrichis"].append(f"{code} -> {name}")
        except Exception as e:
            report["erreurs"].append(f"{code} ({name}): {e}")
    frappe.db.commit()

    # 2) Postes sans titulaire -> modèles (employee vide), un par intitulé.
    for code, entry in catalogue.items():
        if code in CONFIDENT_MATCHES:
            continue
        titre = entry.get("intitule_poste") or ""
        if not titre:
            continue
        existing = frappe.db.get_value(
            "Fiche de Poste KYA", {"intitule_poste": titre, "employee": ["in", ["", None]]})
        if existing:
            report["ignores_deja_cree"].append(f"{code} : modèle déjà présent ({existing})")
            continue
        try:
            doc = frappe.new_doc("Fiche de Poste KYA")
            doc.intitule_poste = titre
            doc.update(_content_fields(entry))
            doc.insert(ignore_permissions=True)
            report["crees"].append(f"{code} -> {doc.name} ({titre})")
        except Exception as e:
            report["erreurs"].append(f"{code} ({titre}): {e}")
    frappe.db.commit()

    return report

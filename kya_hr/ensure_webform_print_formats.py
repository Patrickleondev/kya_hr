"""Associe chaque Web Form KYA à son Print Format OFFICIEL.

PROBLEME (retour terrain) : à l'impression d'un web form, "ça n'affiche pas
bien toutes les infos, y compris la liste (table)". Cause : les 15 web forms
ont allow_print=1 mais print_format=NULL -> Frappe imprime le format
AUTO par defaut, qui rend mal les champs et surtout les tables enfant.

Or il existe des Print Formats officiels (fideles aux modeles papier, qui
ITERENT les lignes de table via {% for ... %}). Ce module pointe chaque
web form vers le sien -> le bouton "Imprimer" affiche le document complet,
lignes de table incluses.

Idempotent. Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


# web form (route) -> Print Format officiel.
WEBFORM_PRINT_FORMATS = {
    "bon-commande": "Bon Commande KYA Officiel",
    "brouillard-caisse": "Brouillard Caisse KYA Officiel",
    "demande-achat": "Demande Achat KYA Officiel",
    "bilan-fin-de-stage": "Bilan de Stage KYA",
    "inventaire-kya": "Fiche Inventaire KYA",
    "permission-sortie-employe": "Ticket Sortie Employe",
    "permission-sortie-stagiaire": "Ticket Sortie Stagiaire",
    "planning-conge": "Demande Conge KYA",
    "pv-entree-materiel": "Ticket Entrée Matériel KYA",
    "pv-sortie-materiel": "PV Sortie Matériel Officiel",
    "etat-recap": "Etat Recap Cheques Officiel",
    "retour-materiel": "Retour Materiel KYA Officiel",
}


def execute() -> dict:
    summary = {"set": [], "skipped": [], "unchanged": 0}
    for webform, pf in WEBFORM_PRINT_FORMATS.items():
        if not frappe.db.exists("Web Form", webform):
            summary["skipped"].append(f"{webform} (web form absent)")
            continue
        if not frappe.db.exists("Print Format", pf):
            summary["skipped"].append(f"{webform} (print format '{pf}' absent)")
            continue
        # Coherence : le print format doit cibler le meme DocType que le web form
        wf_dt = frappe.db.get_value("Web Form", webform, "doc_type")
        pf_dt = frappe.db.get_value("Print Format", pf, "doc_type")
        if wf_dt != pf_dt:
            summary["skipped"].append(f"{webform} (doctype mismatch {wf_dt}!={pf_dt})")
            continue

        current = frappe.db.get_value("Web Form", webform, "print_format")
        if current == pf:
            summary["unchanged"] += 1
            continue
        try:
            frappe.db.set_value("Web Form", webform,
                                {"allow_print": 1, "print_format": pf},
                                update_modified=False)
            summary["set"].append(f"{webform} -> {pf}")
        except Exception:
            try:
                frappe.log_error(frappe.get_traceback(),
                                 f"ensure_webform_print_formats: {webform}")
            except Exception:
                pass
            summary["skipped"].append(f"{webform} (erreur set)")

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[ensure_webform_print_formats] set={len(summary['set'])} "
          f"unchanged={summary['unchanged']} skipped={len(summary['skipped'])}")
    if summary["set"]:
        print("  " + " | ".join(summary["set"]))
    if summary["skipped"]:
        print("  SKIP: " + " | ".join(summary["skipped"]))
    return summary

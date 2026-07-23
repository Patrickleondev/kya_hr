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


# DocType -> Print Format par défaut : le bouton Imprimer du DESK (et toute
# génération PDF sans format explicite) doit sortir le format officiel, pas le
# « Standard » (retour terrain : PDF Brouillard Caisse illisible en prod).
# Pour les doctypes custom=0 le JSON du doctype porte aussi default_print_format ;
# pour les custom=1 (non resyncés par migrate) ce set DB est la seule source.
DOCTYPE_DEFAULT_PRINT_FORMATS = {
    "Brouillard Caisse": "Brouillard Caisse KYA Officiel",
    "Etat Recap Cheques": "Etat Recap Cheques Officiel",
    "Demande Achat KYA": "Demande Achat KYA Officiel",
    "Bon Commande KYA": "Bon Commande KYA Officiel",
    "PV Sortie Materiel": "PV Sortie Matériel Officiel",
    "PV Entree Materiel": "Ticket Entrée Matériel KYA",
    "Retour Materiel KYA": "Retour Materiel KYA Officiel",
    "Inventaire KYA": "Fiche Inventaire KYA",
    "KYA Contrat": "KYA Contrat PDF",
    "Document RH KYA": "Document RH KYA",
    "Avenant Contrat KYA": "Avenant Contrat KYA",
    "Contrat Stage Immersion KYA": "Contrat Stage Immersion KYA",
}


def ensure_doctype_defaults() -> dict:
    out = {"set": [], "unchanged": 0, "skipped": []}
    for dt, pf in DOCTYPE_DEFAULT_PRINT_FORMATS.items():
        if not frappe.db.exists("DocType", dt) or not frappe.db.exists("Print Format", pf):
            out["skipped"].append(dt)
            continue
        if frappe.db.get_value("DocType", dt, "default_print_format") == pf:
            out["unchanged"] += 1
            continue
        frappe.db.set_value("DocType", dt, "default_print_format", pf,
                            update_modified=False)
        out["set"].append(f"{dt} -> {pf}")
    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass
    print(f"[ensure_doctype_defaults] set={len(out['set'])} unchanged={out['unchanged']} "
          f"skipped={len(out['skipped'])}")
    if out["set"]:
        print("  " + " | ".join(out["set"]))
    return out


def sync_print_format_html() -> dict:
    """Recharge le HTML de chaque Print Format depuis son fichier du repo.

    Piège v16 : nos formats sont custom_format=1 (HTML dans le champ `html`),
    mais migrate ne recharge PAS le .html du dossier -> champ parfois vide
    (rendu = TemplateNotFoundError car repli disque sur un chemin ACCENTUÉ
    inexistant), et surtout les retouches UI faites en prod divergent du repo.
    Ici : LE FICHIER DU REPO EST LA SOURCE DE VÉRITÉ, rechargée à chaque
    migrate. Toute évolution de design passe par le repo, jamais par l'UI.
    """
    import os
    out = {"set": [], "unchanged": 0, "skipped": []}
    base = frappe.get_app_path("kya_hr", "print_format")
    for folder in sorted(os.listdir(base)):
        d = os.path.join(base, folder)
        jpath = os.path.join(d, folder + ".json")
        hpath = os.path.join(d, folder + ".html")
        if not (os.path.isdir(d) and os.path.exists(jpath) and os.path.exists(hpath)):
            continue
        import json as _json
        try:
            name = _json.load(open(jpath, encoding="utf-8")).get("name")
            if not name or not frappe.db.exists("Print Format", name):
                out["skipped"].append(folder)
                continue
            html = open(hpath, encoding="utf-8").read()
            if (frappe.db.get_value("Print Format", name, "html") or "") == html:
                out["unchanged"] += 1
                continue
            frappe.db.set_value("Print Format", name, "html", html,
                                update_modified=False)
            out["set"].append(name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"sync_print_format_html: {folder}")
            out["skipped"].append(folder)
    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass
    print(f"[sync_print_format_html] set={len(out['set'])} unchanged={out['unchanged']} "
          f"skipped={out['skipped'] or 0}")
    if out["set"]:
        print("  " + " | ".join(out["set"]))
    return out


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
    summary["doctype_defaults"] = ensure_doctype_defaults()
    summary["html_sync"] = sync_print_format_html()
    return summary

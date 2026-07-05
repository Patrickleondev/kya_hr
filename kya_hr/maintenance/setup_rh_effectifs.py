"""Socle du module RH « Effectifs » (base personnel + parcours + barèmes).

Idempotent. Sème :
  - les départements du classeur (DST/DSS/DSC), libellés éditables par la RH ;
  - les Paramètres RH KYA (barèmes Convention Collective) SI vides — la RH peut
    tout reconfigurer ensuite (aucun calcul via la paie ERPNext).

Branché dans safe_migrations.
"""
from __future__ import annotations

import frappe

# Départements du classeur (libellés = meilleure estimation, éditables ensuite).
_DEPARTEMENTS = [
    ("DST", "Département Scientifique et Technique"),
    ("DSS", "Département Support et Services"),
    ("DSC", "Département Commercial"),
]

# Barème des permissions exceptionnelles (Convention Collective, Art. 50).
_PERMISSIONS = [
    ("Décès d'un conjoint, d'un ascendant ou d'un descendant en ligne directe", 4),
    ("Décès d'un frère ou d'une sœur", 2),
    ("Décès d'un beau-père ou d'une belle-mère", 3),
    ("Mariage du travailleur", 3),
    ("Mariage d'un enfant, d'un frère ou d'une sœur", 1),
    ("Naissance au foyer", 2),
    ("Baptême", 1),
    ("Déménagement", 2),
]


# Raccourcis (cartes) à poser dans l'Espace RH pour le module Effectifs.
_SHORTCUTS = [
    {"type": "URL", "label": "👥 Effectifs (Tableau de bord)", "url": "/rh-effectifs", "color": "Green"},
    {"type": "URL", "label": "🧭 Parcours Salarié", "url": "/parcours-salarie", "color": "Blue"},
    {"type": "DocType", "label": "Registre du Personnel", "link_to": "Salarie KYA"},
    {"type": "DocType", "label": "Évolution de Carrière", "link_to": "Evolution Carriere KYA"},
    {"type": "DocType", "label": "Solde de Tout Compte", "link_to": "Solde Tout Compte KYA"},
    {"type": "DocType", "label": "⚙️ Paramètres RH (barèmes)", "link_to": "Parametres RH KYA"},
]
# Liens de la barre latérale (sous une nouvelle rubrique).
_LINKS = [
    {"type": "Card Break", "label": "Effectifs & Carrière"},
    {"type": "Link", "label": "Registre du Personnel", "link_type": "DocType", "link_to": "Salarie KYA"},
    {"type": "Link", "label": "Évolution de Carrière", "link_type": "DocType", "link_to": "Evolution Carriere KYA"},
    {"type": "Link", "label": "Solde de Tout Compte", "link_type": "DocType", "link_to": "Solde Tout Compte KYA"},
    {"type": "Link", "label": "Département KYA", "link_type": "DocType", "link_to": "Departement KYA"},
    {"type": "Link", "label": "Paramètres RH (barèmes)", "link_type": "DocType", "link_to": "Parametres RH KYA"},
]


def _setup_workspace(out):
    """Ajoute (idempotent) les raccourcis + liens du module Effectifs à l'Espace RH."""
    if not frappe.db.exists("Workspace", "Espace RH"):
        out["workspace"] = "Espace RH absent"
        return
    ws = frappe.get_doc("Workspace", "Espace RH")
    changed = False

    # Nettoyage : d'anciens liens de type URL (invalides sous le schéma actuel :
    # Link Type ∈ DocType/Page/Report) bloquent toute sauvegarde. On les retire
    # (ils sont déjà couverts par des raccourcis URL).
    valides = ("DocType", "Page", "Report")
    gardes = [l for l in ws.links if l.type != "Link" or (l.link_type or "") in valides]
    if len(gardes) != len(ws.links):
        removed = len(ws.links) - len(gardes)
        ws.set("links", gardes)
        changed = True
        out["liens_url_nettoyes"] = removed

    have_sc = {(s.type, s.label) for s in ws.shortcuts}
    for sc in _SHORTCUTS:
        if (sc["type"], sc["label"]) not in have_sc:
            ws.append("shortcuts", sc)
            changed = True
            out["shortcuts"] += 1

    have_ln = {(l.type, l.label) for l in ws.links}
    for ln in _LINKS:
        if (ln["type"], ln["label"]) not in have_ln:
            ws.append("links", ln)
            changed = True
            out["links"] += 1

    if changed:
        ws.flags.ignore_permissions = True
        # Les raccourcis/liens de type URL font échouer la validation Dynamic Link
        # (get_meta("URL")) ; ces valeurs sont valides → on saute cette validation.
        ws.flags.ignore_links = True
        ws.save(ignore_permissions=True)
        # Rendre les raccourcis visibles (bug v16 : content JSON).
        try:
            from kya_hr.kya_hr.maintenance import sync_workspace_shortcuts
            sync_workspace_shortcuts.execute()
        except Exception:
            pass


def execute() -> dict:
    out = {"departements": 0, "parametres": "inchangé", "permissions": 0,
           "shortcuts": 0, "links": 0}

    # 1) Départements
    for code, libelle in _DEPARTEMENTS:
        if not frappe.db.exists("Departement KYA", code):
            frappe.get_doc({
                "doctype": "Departement KYA", "code": code,
                "libelle": libelle, "actif": 1,
            }).insert(ignore_permissions=True)
            out["departements"] += 1

    # 2) Paramètres RH (barèmes) — ne remplit que si le barème des permissions est vide.
    par = frappe.get_single("Parametres RH KYA")
    if not par.get("permissions"):
        for evenement, jours in _PERMISSIONS:
            par.append("permissions", {"evenement": evenement, "jours": jours})
        par.flags.ignore_permissions = True
        par.save(ignore_permissions=True)
        out["parametres"] = "barèmes par défaut posés"
        out["permissions"] = len(_PERMISSIONS)

    _setup_workspace(out)

    frappe.db.commit()
    print("[setup_rh_effectifs] %s" % out)
    return out

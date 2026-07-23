# -*- coding: utf-8 -*-
"""Accessibilité : garantit que CHAQUE fonctionnalité récente est atteignable par
un raccourci dans l'espace de travail du bon métier — jamais par une URL à taper.

Principe « le système survit à son auteur » : cette table déclarative est la
source de vérité de la découvrabilité. Pour rendre une nouvelle page/tableau de
bord accessible, il suffit d'ajouter une ligne ici — rien d'autre. Purement
ADDITIF (jamais de suppression), idempotent par (type, label). Rend ensuite les
raccourcis visibles via sync_workspace_shortcuts (bug v16 : content JSON).

Câblé en AFTER_MIGRATE, APRÈS les autres scripts qui posent des raccourcis.
"""
from __future__ import annotations

import frappe

# {Workspace : [ {type, label, url|link_to, color?}, ... ]}
FEATURE_SHORTCUTS = {
    # ── RH : documents dynamiques + effectifs d'équipe ────────────────────────
    "Espace RH": [
        {"type": "URL", "label": "📄 Documents RH (certificats/attestations)", "url": "/documents-rh", "color": "Green"},
        {"type": "URL", "label": "📝 Avenants au contrat", "url": "/avenants-rh", "color": "Blue"},
        {"type": "URL", "label": "🎓 Contrats de stage d'immersion", "url": "/contrats-immersion", "color": "Blue"},
        {"type": "URL", "label": "👥 Effectifs des équipes (détail)", "url": "/equipe-effectifs", "color": "Green"},
        {"type": "DocType", "label": "🗂️ Journal des modifications (fiches)", "link_to": "Modification Info Employe KYA"},
    ],
    # ── Chef d'équipe : édite les infos de ses membres ────────────────────────
    "Gestion Equipe": [
        {"type": "URL", "label": "👥 Effectifs de mon équipe (modifier)", "url": "/equipe-effectifs", "color": "Green"},
    ],
    # ── Direction : signe les documents + tableaux de bord ────────────────────
    "Direction Generale": [
        {"type": "URL", "label": "🧭 Synthèse Direction", "url": "/direction-dashboard", "color": "Blue"},
        {"type": "URL", "label": "📊 Tableau de bord global", "url": "/kya-tableau-de-bord", "color": "Blue"},
        {"type": "URL", "label": "📄 Documents RH (à signer)", "url": "/documents-rh", "color": "Green"},
        {"type": "URL", "label": "📝 Avenants au contrat (à signer)", "url": "/avenants-rh", "color": "Green"},
        {"type": "URL", "label": "🎓 Contrats de stage d'immersion (à signer)", "url": "/contrats-immersion", "color": "Green"},
        {"type": "URL", "label": "👥 Effectifs des équipes", "url": "/equipe-effectifs", "color": "Blue"},
    ],
    # ── Employés : catalogue pour demander une sortie de matériel ─────────────
    "Espace Employes": [
        {"type": "URL", "label": "🛒 Catalogue des articles (demande de sortie)", "url": "/stock-catalogue", "color": "Orange"},
    ],
    # ── Stock : catalogue + rapport ───────────────────────────────────────────
    "Espace Stock": [
        {"type": "URL", "label": "🛒 Catalogue des articles", "url": "/stock-catalogue", "color": "Orange"},
        {"type": "URL", "label": "📊 Rapport de stock (période/équipe)", "url": "/rapport-stock", "color": "Blue"},
    ],
}


_VALID_LINK_TYPES = ("DocType", "Page", "Report")


def _add_to_workspace(ws_name, shortcuts, out):
    if not frappe.db.exists("Workspace", ws_name):
        out["absents"].append(ws_name)
        return
    ws = frappe.get_doc("Workspace", ws_name)

    # Certains espaces contiennent d'anciens LIENS de sidebar de type « URL »,
    # invalides sous le schéma actuel (Link Type ∈ DocType/Page/Report) : ils font
    # ÉCHOUER toute sauvegarde du workspace. On les retire (ils sont de toute façon
    # couverts par des raccourcis URL, seuls habilités à porter une URL).
    valides = [l for l in ws.links
               if l.type != "Link" or (l.link_type or "") in _VALID_LINK_TYPES]
    nettoyes = len(ws.links) - len(valides)
    if nettoyes:
        ws.set("links", valides)
        out["liens_url_nettoyes"][ws_name] = nettoyes

    have = {(s.type, s.label) for s in ws.shortcuts}
    added = 0
    for sc in shortcuts:
        if (sc["type"], sc["label"]) not in have:
            ws.append("shortcuts", sc)
            added += 1
    if added or nettoyes:
        ws.flags.ignore_permissions = True
        ws.flags.ignore_links = True  # raccourcis URL : sauter la validation Dynamic Link
        ws.save(ignore_permissions=True)
        if added:
            out["ajoutes"][ws_name] = added


def execute():
    frappe.set_user("Administrator")
    out = {"ajoutes": {}, "absents": [], "liens_url_nettoyes": {}}
    for ws_name, shortcuts in FEATURE_SHORTCUTS.items():
        try:
            _add_to_workspace(ws_name, shortcuts, out)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"ensure_kya_feature_shortcuts: {ws_name}")
    frappe.db.commit()
    # Rendre les raccourcis VISIBLES dans le content JSON (v16).
    try:
        from kya_hr.kya_hr.maintenance import sync_workspace_shortcuts
        sync_workspace_shortcuts.execute()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ensure_kya_feature_shortcuts: sync")
    print("[ensure_kya_feature_shortcuts] ajoutés=%s absents=%s" % (out["ajoutes"], out["absents"]))
    return out


run = execute

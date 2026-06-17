# -*- coding: utf-8 -*-
"""Garantit qu'AUCUN lien d'un espace KYA ne reste sans raccourci.

Retour terrain (user) : « faut pas qu'il y ait un lien qui n'a pas de raccourci
dans son espace ». En Frappe v16, un Workspace a deux listes :
- les **Links** (liste latérale sous les Card Break)
- les **Shortcuts** (cartes d'accès rapide en haut, seules vraiment visibles)

Plusieurs DocTypes/Reports figuraient en Link mais n'avaient AUCUN raccourci
(Department, Designation, Besoin/Plan de Formation, Equipe KYA, Templates,
Imports RH…). Ce module crée le raccourci manquant pour chaque Link.

Anti-doublon : un Link DocType est considéré « déjà couvert » s'il existe
- un Shortcut DocType pointant dessus, OU
- un Shortcut URL pointant vers le web form de ce DocType (ex. le raccourci
  URL /permission-sortie-employe couvre le DocType « Permission Sortie Employe »).

Ajoute aussi les raccourcis dashboards explicitement demandés (RH surtout).
Idempotent. Enchaîne sur sync_workspace_shortcuts pour rendre tout visible.
"""
from __future__ import annotations

import frappe

from kya_hr.maintenance import sync_workspace_shortcuts

KYA_WORKSPACES = [
    "Gestion Equipe", "Espace RH", "Espace Achats",
    "Espace Stock", "Logistique", "Espace Comptabilite", "Espace Employes",
    "Espace Stagiaires", "Inventaire Sorties Materiel",
]

# Espaces qui ne doivent montrer QUE des dashboards (pas de raccourcis DocType /
# Report bruts). La Direction navigue par tableaux de bord, pas par listes.
DASHBOARDS_ONLY = ["Direction Generale"]

# Raccourcis dashboards à garantir en plus des liens (label, url).
EXTRA_URL_SHORTCUTS: dict[str, list[tuple[str, str]]] = {
    "Espace RH": [
        ("👥 Dashboard RH (détaillé)", "/kya-rh-dashboard"),
        ("🕒 Présences (Dashboard)", "/presence-rh"),
        ("🎓 Formation", "/formation-dashboard"),
    ],
    "Gestion Equipe": [
        ("📊 Dashboard Équipe", "/kya-dashboard-equipe"),
    ],
    "Espace Stock": [
        ("📦 Dashboard Stocks", "/kya-stocks-dashboard"),
    ],
    "Espace Achats": [
        ("🛒 Dashboard Achats", "/achats-dashboard"),
    ],
    "Espace Comptabilite": [
        ("🏦 Dashboard Comptabilité", "/comptabilite-dashboard"),
    ],
    "Logistique": [
        ("🚚 Dashboard Logistique", "/kya-logistique-dashboard"),
    ],
}


def _norm_url(u: str) -> str:
    return (u or "").strip().rstrip("/").lower()


def _webform_doctype_map() -> dict[str, str]:
    """route (sans slash) -> doctype, pour reconnaître qu'un raccourci URL
    /<route> couvre le DocType correspondant."""
    out = {}
    for w in frappe.get_all("Web Form", fields=["route", "doc_type"]):
        if w.route and w.doc_type:
            out[_norm_url("/" + w.route)] = w.doc_type
    return out


def _insert_shortcut(ws: str, idx: int, payload: dict) -> None:
    """Insère un Workspace Shortcut directement en base (db_insert) pour ne PAS
    revalider le parent Workspace, dont des Links pré-existants ont un link_type
    'URL' invalide (insérés en direct par d'anciens scripts)."""
    child = frappe.get_doc({
        "doctype": "Workspace Shortcut",
        "parent": ws, "parenttype": "Workspace", "parentfield": "shortcuts",
        "idx": idx, **payload,
    })
    child.name = frappe.generate_hash(length=10)
    child.db_insert()


def ensure_ws(ws: str, wf_map: dict[str, str]) -> list[str]:
    shortcuts = frappe.get_all("Workspace Shortcut", filters={"parent": ws},
                               fields=["type", "link_to", "url", "label", "idx"])
    links = frappe.get_all("Workspace Link", filters={"parent": ws},
                           fields=["type", "link_type", "link_to", "label"], order_by="idx")

    covered_doctypes: set[str] = set()
    covered_reports: set[str] = set()
    covered_urls: set[str] = set()
    existing_labels: set[str] = set()
    max_idx = 0

    for s in shortcuts:
        max_idx = max(max_idx, s.idx or 0)
        if s.label:
            existing_labels.add(s.label)
        if s.type == "DocType" and s.link_to:
            covered_doctypes.add(s.link_to)
        elif s.type == "Report" and s.link_to:
            covered_reports.add(s.link_to)
        elif s.type == "URL" and s.url:
            nu = _norm_url(s.url)
            covered_urls.add(nu)
            # un raccourci URL vers /<route> d'un web form couvre son DocType
            if nu in wf_map:
                covered_doctypes.add(wf_map[nu])

    created: list[str] = []

    def add(payload, tag):
        nonlocal max_idx
        max_idx += 1
        _insert_shortcut(ws, max_idx, payload)
        created.append(tag)

    for l in links:
        if l.type != "Link" or not l.link_to:
            continue
        lt = l.link_type or "DocType"
        if lt == "DocType":
            if l.link_to in covered_doctypes:
                continue
            add({"type": "DocType", "link_to": l.link_to,
                 "label": l.label or l.link_to, "color": "Grey"}, f"DocType:{l.label}")
            covered_doctypes.add(l.link_to)
        elif lt == "Report":
            if l.link_to in covered_reports:
                continue
            add({"type": "Report", "link_to": l.link_to,
                 "report_ref_doctype": frappe.db.get_value("Report", l.link_to, "ref_doctype"),
                 "label": l.label or l.link_to, "color": "Grey"}, f"Report:{l.label}")
            covered_reports.add(l.link_to)
        else:  # URL / Page traité comme URL
            if _norm_url(l.link_to) in covered_urls:
                continue
            add({"type": "URL", "url": l.link_to,
                 "label": l.label or l.link_to, "color": "Grey"}, f"URL:{l.label}")
            covered_urls.add(_norm_url(l.link_to))

    # Raccourcis dashboards explicites
    for label, url in EXTRA_URL_SHORTCUTS.get(ws, []):
        if _norm_url(url) in covered_urls or label in existing_labels:
            continue
        add({"type": "URL", "url": url, "label": label, "color": "Blue"}, f"URL:{label}")
        covered_urls.add(_norm_url(url))

    return created


def purge_to_dashboards_only(ws: str) -> int:
    """Direction : ne garder QUE les raccourcis de type URL (dashboards) ;
    supprimer les raccourcis DocType/Report (listes brutes) et reconstruire le
    content JSON avec les seuls dashboards restants."""
    import json
    removed = frappe.get_all("Workspace Shortcut",
                             filters={"parent": ws, "type": ["in", ["DocType", "Report"]]},
                             pluck="name")
    for n in removed:
        frappe.delete_doc("Workspace Shortcut", n, ignore_permissions=True, force=True)
    # reconstruire le content : header + uniquement les shortcuts URL restants
    remaining = frappe.get_all("Workspace Shortcut", filters={"parent": ws},
                               fields=["label"], order_by="idx")
    content = frappe.db.get_value("Workspace", ws, "content") or "[]"
    try:
        blocks = json.loads(content)
    except Exception:
        blocks = []
    # garder tout sauf les blocs shortcut (on les re-pose proprement)
    blocks = [b for b in blocks if b.get("type") != "shortcut"]
    for s in remaining:
        if s.label:
            blocks.append({"id": frappe.generate_hash(length=10), "type": "shortcut",
                           "data": {"shortcut_name": s.label, "col": 3}})
    frappe.db.set_value("Workspace", ws, "content", json.dumps(blocks), update_modified=False)
    return len(removed)


def execute() -> dict:
    wf_map = _webform_doctype_map()
    out = {}
    total = 0
    for ws in KYA_WORKSPACES:
        if not frappe.db.exists("Workspace", ws):
            continue
        created = ensure_ws(ws, wf_map)
        if created:
            out[ws] = created
            total += len(created)
    for ws in DASHBOARDS_ONLY:
        if frappe.db.exists("Workspace", ws):
            n = purge_to_dashboards_only(ws)
            if n:
                out[ws] = f"-{n} raccourcis DocType/Report (dashboards only)"
    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass
    print(f"[ensure_link_shortcuts] +{total} raccourcis créés")
    for ws, items in out.items():
        print(f"  {ws}: {items}")
    # rend tous les raccourcis visibles dans le content JSON
    sync_workspace_shortcuts.execute()
    return {"created": out, "total": total}

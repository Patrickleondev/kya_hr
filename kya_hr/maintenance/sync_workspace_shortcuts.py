# -*- coding: utf-8 -*-
"""Rend VISIBLES tous les raccourcis (et donc la navigation) des espaces KYA.

BUG navigation détecté : en Frappe v16, un Workspace Shortcut n'apparaît sur la
page QUE s'il est référencé dans le JSON `content` du workspace (bloc
`{"type":"shortcut","data":{"shortcut_name": ...}}`). Or plusieurs scripts
(ensure_workspace_roles, ensure_direction_oversight…) ajoutaient les raccourcis
dans la table enfant SANS toucher au `content` → ils existaient en base mais
n'étaient PAS affichés. Conséquence concrète : le DG ne voyait PAS, sur l'Espace
Direction, les raccourcis vers les dashboards Compta/RH/Stocks/Achats/Logistique
ni vers les récaps — « full rights mais pas accessible ».

Ce module garantit que CHAQUE raccourci de la table enfant est référencé dans le
`content` (sinon il est ajouté sous une section « Accès rapides »). Idempotent.
Wrappé dans safe_migrations.AFTER_MIGRATE, APRÈS les scripts qui posent des
raccourcis.
"""
from __future__ import annotations

import json

import frappe

KYA_WORKSPACES = [
    "Direction Generale", "Gestion Equipe", "Espace RH", "Espace Achats",
    "Espace Stock", "Logistique", "Espace Comptabilite", "Espace Employes",
    "Espace Stagiaires", "Inventaire Sorties Materiel",
]

_HEADER_TEXT = "<b>📌 Accès rapides</b>"


def _nid():
    return frappe.generate_hash(length=10)


def sync_ws(ws: str) -> int:
    content = frappe.db.get_value("Workspace", ws, "content") or "[]"
    try:
        blocks = json.loads(content)
    except Exception:
        blocks = []

    referenced = {
        b.get("data", {}).get("shortcut_name")
        for b in blocks if b.get("type") == "shortcut"
    }
    shortcuts = frappe.get_all("Workspace Shortcut", filters={"parent": ws},
                               fields=["label"], order_by="idx")
    missing = [s.label for s in shortcuts if s.label and s.label not in referenced]
    if not missing:
        return 0

    has_header = any(
        b.get("type") == "header" and b.get("data", {}).get("text") == _HEADER_TEXT
        for b in blocks
    )
    if not has_header:
        blocks.append({"id": _nid(), "type": "header",
                       "data": {"text": _HEADER_TEXT, "level": 4, "col": 12}})
    for label in missing:
        blocks.append({"id": _nid(), "type": "shortcut",
                       "data": {"shortcut_name": label, "col": 3}})

    frappe.db.set_value("Workspace", ws, "content", json.dumps(blocks),
                        update_modified=False)
    return len(missing)


def execute() -> dict:
    out = {}
    total = 0
    for ws in KYA_WORKSPACES:
        if frappe.db.exists("Workspace", ws):
            n = sync_ws(ws)
            if n:
                out[ws] = n
                total += n
    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass
    print("[sync_workspace_shortcuts] +%d raccourcis rendus visibles : %s" % (total, out))
    return {"added": out, "total": total}

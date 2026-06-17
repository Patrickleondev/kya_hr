# -*- coding: utf-8 -*-
"""Corrige les anomalies de workspaces qui font « planter au clic » certaines icônes.

Symptômes terrain : les icônes Gestion Équipe / Direction Générale / Espace
Employé apparaissent (parfois grisées, icône « G ») mais cliquer donne une
erreur. Causes trouvées :

1. `parent_page = NULL` (au lieu de '') sur certains workspaces top-level
   → l'arbre de la sidebar v16 ne les résout pas correctement.
2. `Gestion Equipe` : label/title sans accent + `icon` = "users" (un NOM d'icône,
   pas un emoji) → rendu en lettre « G » grise dans le lanceur, incohérent avec
   les autres espaces (emoji).

Ce script idempotent normalise ces points. Il NE touche PAS au `name` (clé) des
workspaces (référencé par les Desktop Icons). Branché dans safe_migrations.
NB : la VISIBILITÉ par rôle reste gérée par ensure_workspace_roles ; une icône
role-gated vue par un compte sans le rôle se grise — c'est voulu (RBAC).
"""
from __future__ import annotations

import frappe

# workspace name -> emoji icon cohérent (aligné sur desktop_icons.py)
ICON_FIXUP = {
    "Gestion Equipe": "🤝",
}

# Le clic « plante » quand un compte VOIT l'icône mais n'a pas le rôle exigé par
# le workspace (RBAC). Cas avéré : « Gestion Équipe » n'autorisait que
# "Chef d'Équipe"/"Chef Service" alors qu'il existe aussi le rôle DOUBLON
# "Chef Equipe" (sans accent) + variantes DST. On élargit donc l'accès du
# workspace à TOUTES les variantes de chef qui doivent piloter une équipe.
WORKSPACE_EXTRA_ROLES = {
    "Gestion Equipe": [
        "Chef Equipe", "Chef d'Equipe", "Chef d'Équipe", "Chef Service",
        "DST - Chef Equipe Offres et Formations", "DST - Chef Equipe Installation",
        "DST - Chef Equipe Audit Interne", "Responsable RH", "Directeur Général", "DGA",
    ],
}


def _ensure_workspace_roles(ws: str, roles: list[str]) -> list[str]:
    """Ajoute les rôles manquants à un Workspace (s'ils existent comme Role)."""
    if not frappe.db.exists("Workspace", ws):
        return []
    doc = frappe.get_doc("Workspace", ws)
    have = {r.role for r in (doc.roles or [])}
    added = []
    for r in roles:
        if r in have or not frappe.db.exists("Role", r):
            continue
        doc.append("roles", {"role": r})
        added.append(r)
    if added:
        doc.flags.ignore_permissions = True
        doc.save()
    return added


def execute() -> dict:
    out = {"parent_fixed": [], "icon_fixed": [], "accent_fixed": [], "roles_added": {}}

    # 1) parent_page NULL -> '' sur tous les workspaces publics
    for w in frappe.get_all("Workspace", filters={"public": 1}, fields=["name", "parent_page"]):
        if w.parent_page is None:
            frappe.db.set_value("Workspace", w.name, "parent_page", "", update_modified=False)
            out["parent_fixed"].append(w.name)

    # 2) Gestion Equipe : accent label/title + emoji
    if frappe.db.exists("Workspace", "Gestion Equipe"):
        cur = frappe.db.get_value("Workspace", "Gestion Equipe",
                                  ["label", "title", "icon"], as_dict=True)
        if cur.label != "Gestion Équipe" or cur.title != "Gestion Équipe":
            frappe.db.set_value("Workspace", "Gestion Equipe",
                                {"label": "Gestion Équipe", "title": "Gestion Équipe"},
                                update_modified=False)
            out["accent_fixed"].append("Gestion Equipe")

    # 3) icônes emoji cohérentes
    for ws, emoji in ICON_FIXUP.items():
        if frappe.db.exists("Workspace", ws):
            if frappe.db.get_value("Workspace", ws, "icon") != emoji:
                frappe.db.set_value("Workspace", ws, "icon", emoji, update_modified=False)
                out["icon_fixed"].append(ws)

    # 4) élargir l'accès des workspaces aux rôles doublons (fix « plante au clic »)
    for ws, roles in WORKSPACE_EXTRA_ROLES.items():
        added = _ensure_workspace_roles(ws, roles)
        if added:
            out["roles_added"][ws] = added

    if any(v for v in out.values()):
        frappe.db.commit()
        frappe.clear_cache()
    print(f"[fix_workspace_anomalies] parent={out['parent_fixed']} "
          f"accent={out['accent_fixed']} icon={out['icon_fixed']} roles={out['roles_added']}")
    return out

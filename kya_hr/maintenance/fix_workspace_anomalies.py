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

import json
import unicodedata

import frappe

# --- Icônes « mortes au clic » / 404 : alignement label <-> Sidebar.name <-> Workspace.name ---
# Le frontend résout une Desktop Icon en DEUX temps :
#  1) trouver le sidebar : boot.workspace_sidebar_item[ icon.label.toLowerCase() ]
#     où la clé est `Workspace Sidebar.name.lower()` -> il faut label==sidebar.name ;
#  2) construire la route : "/desk/" + slug(workspace.name) (et certains chemins
#     slugifient le label/sidebar) -> la route DOIT être celle du workspace.
# Conséquence : si on met un ACCENT dans le label, on doit aussi accentuer le
# name du sidebar (étape 1), ce qui accentue la route (étape 2) -> /desk/gestion-équipe
# alors que le workspace est `Gestion Equipe` (route gestion-equipe) -> 404.
#
# L'invariant des icônes qui marchent (Espace RH, Logistique...) :
#     icon.label == Workspace Sidebar.name == Workspace.name   (tout en ASCII)
# On l'impose donc aux 3 espaces KYA dont le name de workspace est sans accent.
# L'accent à l'AFFICHAGE est rendu par la traduction __(label) (cf. fr.csv) ;
# en prod (langue française) « Gestion Equipe » s'affiche « Gestion Équipe ».
#
# Précautions prod : SQL binaire (la collation MariaDB est accent-insensible donc
# rename_doc refuse en croyant la cible déjà là), aucune FK sur Sidebar.name
# (vérifié), idempotent, + vérification finale tracée.
SIDEBAR_ASCII_CANONICAL = [
    "Direction Generale",
    "Gestion Equipe",
    "Espace Employes",
]

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


def _enforce_sidebar_ascii() -> dict:
    """Force le `name` des Workspace Sidebar KYA en ASCII (= Workspace.name = label),
    et le `label` des Desktop Icons en ASCII, pour clic ET route valides.
    Idempotent et binaire-sûr."""
    res = {"sidebar_renamed": [], "label_fixed": [], "verified_ok": [], "verify_warn": []}
    for canonical in SIDEBAR_ASCII_CANONICAL:
        canonical = unicodedata.normalize("NFC", canonical)  # ASCII -> inchangé
        # collation accent-insensible : matche la ligne quelle que soit sa forme
        rows = frappe.db.sql(
            "SELECT name FROM `tabWorkspace Sidebar` WHERE name=%s", (canonical,)
        )
        if len(rows) == 1:
            current = rows[0][0]
            if current != canonical:  # encore accentué -> on remet en ASCII (binaire)
                frappe.db.sql(
                    "UPDATE `tabWorkspace Sidebar` SET name=%s WHERE name=%s",
                    (canonical, canonical),
                )
                frappe.db.sql(
                    "UPDATE `tabWorkspace Sidebar Item` SET parent=%s WHERE parent=%s",
                    (canonical, canonical),
                )
                res["sidebar_renamed"].append(f"{current!r} -> {canonical!r}")
        elif len(rows) > 1:
            res["verify_warn"].append(f"{canonical}: {len(rows)} sidebars ambigus")

        # Desktop Icon : label en ASCII (collation matche l'accentué existant)
        for di in frappe.db.sql(
            "SELECT name, label FROM `tabDesktop Icon` WHERE label=%s", (canonical,), as_dict=True
        ):
            if di.label != canonical:
                frappe.db.sql(
                    "UPDATE `tabDesktop Icon` SET label=%s WHERE name=%s", (canonical, di.name)
                )
                res["label_fixed"].append(f"{di.label!r} -> {canonical!r}")

        # Workspace : title ET label en ASCII (= name). CRUCIAL : la route desk est
        # /desk/slug(workspace.title). Un title accentué -> /desk/...-é... -> 404.
        # L'accent d'affichage passe par la traduction __(title)/__(label) (fr).
        if frappe.db.exists("Workspace", canonical):
            cur = frappe.db.get_value("Workspace", canonical, ["title", "label"], as_dict=True)
            upd = {}
            if cur.title != canonical:
                upd["title"] = canonical
            if cur.label != canonical:
                upd["label"] = canonical
            if upd:
                frappe.db.set_value("Workspace", canonical, upd, update_modified=False)
                res["label_fixed"].append(f"Workspace {canonical}: {upd}")

    # Vérification finale : label.lower() doit être une clé sidebar.lower()
    sidebar_names = {n.lower() for n in frappe.get_all("Workspace Sidebar", pluck="name")}
    for canonical in SIDEBAR_ASCII_CANONICAL:
        if canonical.lower() in sidebar_names:
            res["verified_ok"].append(canonical)
        else:
            res["verify_warn"].append(f"{canonical}: clé {canonical.lower()!r} introuvable")
    return res


def _clean_team_sidebar() -> list:
    """Nettoie le sidebar Gestion Equipe : retire les liens Workspace en double
    (self-link dupliqué) et répare l'item « Dashboard Equipe » dont l'URL était
    vide (-> /kya-dashboard-equipe). Idempotent."""
    fixed = []
    if not frappe.db.exists("Workspace Sidebar", "Gestion Equipe"):
        return fixed
    doc = frappe.get_doc("Workspace Sidebar", "Gestion Equipe")
    seen, keep, changed = set(), [], False
    for it in doc.items:
        # réparer l'URL du dashboard équipe
        if it.link_type == "URL" and (it.label or "").strip().lower().startswith("dashboard") and not (it.url or "").strip():
            it.url = "/kya-dashboard-equipe"
            changed = True
            fixed.append("Dashboard Equipe URL -> /kya-dashboard-equipe")
        # dédoublonner les liens (par type/cible)
        key = (it.type, it.link_type, it.link_to, it.url, it.label)
        if it.type == "Link" and key in seen:
            changed = True
            fixed.append(f"doublon retiré: {it.label}")
            continue
        seen.add(key)
        keep.append(it)
    if changed:
        doc.items = keep
        for i, it in enumerate(doc.items, 1):
            it.idx = i
        doc.flags.ignore_permissions = True
        doc.save()
    return fixed


def _ensure_people_landing() -> str:
    """HRMS définit `app_home = "/desk/people"` mais aucun workspace « People »
    n'existe dans cette version -> clic sur l'app Frappe HR = 404 (SPA, le redirect
    serveur ne s'applique pas). On crée un workspace « People » CACHÉ (routable par
    URL `/desk/people`, absent du nav) qui pointe vers l'espace RH. Idempotent."""
    # Hub RH affiché quand on clique l'app « Frappe HR » (app_home=/desk/people).
    # On le veut RICHE (plusieurs raccourcis = les « sous-icônes » RH attendues).
    # (label, /desk/<slug>, couleur) — uniquement les workspaces qui existent.
    # (label affiché, nom du workspace cible, couleur). On ÉVITE les workspaces
    # dont le name contient un '&' (slug fragile -> 404), cf. invariant routing.
    HUB = [
        ("Espace RH", "Espace RH", "Blue"),
        ("Congés", "Leaves", "Green"),
        ("Paie", "Payroll", "Orange"),
        ("Recrutement", "Recruitment", "Purple"),
        ("Performance", "Performance", "Pink"),
        ("Notes de frais", "Expenses", "Yellow"),
        ("Frappe HR", "Frappe HR", "Grey"),
    ]
    avail = []
    for label, ws_name, color in HUB:
        if "&" in ws_name:
            continue
        if frappe.db.exists("Workspace", ws_name):
            url = "/desk/" + ws_name.lower().replace(" ", "-")
            avail.append((label, url, color))

    blocks = [{"id": "people-hdr", "type": "header",
               "data": {"text": "<span style='font-size:20px;font-weight:700'>Ressources Humaines</span>", "col": 12}}]
    for i, (label, _url, _c) in enumerate(avail):
        blocks.append({"id": f"sc-{i}", "type": "shortcut",
                       "data": {"shortcut_name": label, "col": 3}})
    content = json.dumps(blocks)

    if frappe.db.exists("Workspace", "People"):
        # enrichir : recréer les raccourcis si le hub a moins d'items que prévu
        doc = frappe.get_doc("Workspace", "People")
        if len(doc.shortcuts or []) >= len(avail):
            return ""  # déjà à jour
        doc.shortcuts = []
        for label, url, color in avail:
            doc.append("shortcuts", {"type": "URL", "label": label, "url": url, "color": color})
        doc.content = content
        doc.flags.ignore_permissions = True
        doc.save()
        return f"Hub People enrichi ({len(avail)} raccourcis)"

    doc = frappe.new_doc("Workspace")
    doc.update({
        "name": "People", "title": "People", "label": "People",
        "public": 1, "is_hidden": 1, "module": "KYA HR",
        "icon": "users", "content": content, "sequence_id": 99,
    })
    for label, url, color in avail:
        doc.append("shortcuts", {"type": "URL", "label": label, "url": url, "color": color})
    doc.flags.ignore_permissions = True
    doc.insert()
    return f"Workspace People (caché) créé -> /desk/people OK ({len(avail)} raccourcis)"


def execute() -> dict:
    out = {"parent_fixed": [], "icon_fixed": [], "accent_fixed": [], "roles_added": {}}

    # 0) alignement label == sidebar.name == workspace.name en ASCII (fix clic + route 404)
    out["sidebar_ascii"] = _enforce_sidebar_ascii()
    out["team_sidebar"] = _clean_team_sidebar()
    out["people_landing"] = _ensure_people_landing()

    # 1) parent_page NULL -> '' sur tous les workspaces publics
    for w in frappe.get_all("Workspace", filters={"public": 1}, fields=["name", "parent_page"]):
        if w.parent_page is None:
            frappe.db.set_value("Workspace", w.name, "parent_page", "", update_modified=False)
            out["parent_fixed"].append(w.name)

    # 2) (supprimé) — NE PAS accentuer title/label de Gestion Equipe : le title
    #    pilote la route /desk/slug(title) ; un accent y crée un 404. L'alignement
    #    ASCII title/label est fait par _enforce_sidebar_ascii (étape 0).

    # 3) icônes emoji cohérentes
    for ws, emoji in ICON_FIXUP.items():
        if frappe.db.exists("Workspace", ws):
            if frappe.db.get_value("Workspace", ws, "icon") != emoji:
                frappe.db.set_value("Workspace", ws, "icon", emoji, update_modified=False)
                out["icon_fixed"].append(ws)

    # 3b) Desktop Icon Gestion Équipe : emoji (était 'users' -> tuile « G » grise)
    for di in frappe.get_all("Desktop Icon", filters={"label": "Gestion Équipe"}, pluck="name"):
        if frappe.db.get_value("Desktop Icon", di, "icon") != "🤝":
            frappe.db.set_value("Desktop Icon", di, "icon", "🤝", update_modified=False)
            out["icon_fixed"].append("Desktop Icon Gestion Équipe")

    # 3c) « Inventaire & Sorties Matériel » : retirer l'icône (route 404 via '&',
    #     redondant avec Espace Stock) + masquer le workspace.
    for di in frappe.get_all("Desktop Icon", filters={"label": ["like", "Inventaire%"]}, pluck="name"):
        frappe.delete_doc("Desktop Icon", di, force=1, ignore_permissions=True)
        out.setdefault("removed", []).append(di)
    if frappe.db.exists("Workspace", "Inventaire Sorties Materiel"):
        if not frappe.db.get_value("Workspace", "Inventaire Sorties Materiel", "is_hidden"):
            frappe.db.set_value("Workspace", "Inventaire Sorties Materiel", "is_hidden", 1, update_modified=False)
            out.setdefault("removed", []).append("Workspace Inventaire masqué")

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

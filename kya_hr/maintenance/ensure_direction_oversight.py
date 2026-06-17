# -*- coding: utf-8 -*-
"""Donne à la Direction (DG/DGA) la MAIN COMPLÈTE sur les récaps & fiches que
les dashboards Direction exposent (compta, marchés, clients SoP).

Demande explicite : le DG (et le DGA) doivent pouvoir consulter ET agir sur
les récapitulatifs comptables / marchés / SoP depuis l'Espace Direction, pas
seulement en lecture. Sans ça, le DG ouvre un brouillard/état/marché et ne
peut rien faire (read=1, write=0).

Idempotent — wrappé dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe

DIRECTION_ROLES = ["Directeur Général", "DGA"]

OVERSIGHT_DOCTYPES = [
    "Brouillard Caisse",
    "Etat Recap Cheques",
    "Marche KYA",
    "KYA SoP Client",
]

# droits "intégralité" (sans toucher au gating workflow : pas de submit/cancel
# automatique — la Direction garde la main via write/create/delete + export).
RIGHTS = ["read", "write", "create", "delete", "print", "email", "export", "report", "share"]

# Raccourcis de NAVIGATION : full rights ne suffit pas, il faut que la Direction
# atteigne concrètement ces récaps depuis l'Espace Direction. (label, type, cible, couleur)
DIRECTION_SHORTCUTS = [
    ("Brouillards de Caisse", "DocType", "Brouillard Caisse", "#6a1b9a"),
    ("Etats Recap Cheques", "DocType", "Etat Recap Cheques", "#4a148c"),
    ("Recap Hebdo Caisse (DG)", "URL", "/recap-brouillards", "#1565c0"),
    ("Marches KYA", "DocType", "Marche KYA", "#e65100"),
    ("Clients SoP KYA", "DocType", "KYA SoP Client", "#1565c0"),
]

# Chef d'équipe : assignation pratique depuis l'Espace Gestion Equipe.
EQUIPE_SHORTCUTS = [
    ("➕ Assigner une Tache", "URL", "/app/tache-equipe/new", "#0d7377"),
    ("➕ Nouveau Plan Trimestriel", "URL", "/app/plan-trimestriel/new", "#0d7377"),
]


def _ensure_shortcut(ws, label, stype, target, color):
    if not frappe.db.exists("Workspace", ws):
        return False
    filt = {"parent": ws, "label": label}
    if frappe.db.exists("Workspace Shortcut", filt):
        return False
    # éviter aussi un doublon par cible
    dup = {"parent": ws, ("link_to" if stype == "DocType" else "url"): target}
    if frappe.db.exists("Workspace Shortcut", dup):
        return False
    mx = frappe.db.sql("SELECT COALESCE(MAX(idx),0) FROM `tabWorkspace Shortcut` WHERE parent=%s", (ws,))[0][0] or 0
    sc = frappe.new_doc("Workspace Shortcut")
    sc.parent = ws
    sc.parenttype = "Workspace"
    sc.parentfield = "shortcuts"
    sc.idx = mx + 1
    sc.type = stype
    sc.label = label
    sc.color = color
    if stype == "DocType":
        sc.link_to = target
    else:
        sc.url = target
    sc.insert(ignore_permissions=True)
    return True


def execute() -> dict:
    from frappe.permissions import add_permission, update_permission_property
    granted = []
    for dt in OVERSIGHT_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue
        for role in DIRECTION_ROLES:
            if not frappe.db.exists("Role", role):
                continue
            existing = frappe.db.get_value(
                "Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0}, "name") \
                or frappe.db.get_value(
                "DocPerm", {"parent": dt, "role": role, "permlevel": 0}, "name")
            try:
                if not frappe.db.get_value("Custom DocPerm",
                                           {"parent": dt, "role": role, "permlevel": 0}, "name") \
                   and not frappe.db.get_value("DocPerm",
                                               {"parent": dt, "role": role, "permlevel": 0}, "name"):
                    add_permission(dt, role, 0)
                for r in RIGHTS:
                    update_permission_property(dt, role, 0, r, "1")
                granted.append("%s <- %s" % (dt, role))
            except Exception:
                try:
                    frappe.log_error(frappe.get_traceback(),
                                     "ensure_direction_oversight: %s/%s" % (dt, role))
                except Exception:
                    pass

    # Navigation : raccourcis pratiques (accès concret, pas seulement les droits)
    shortcuts = []
    for label, stype, target, color in DIRECTION_SHORTCUTS:
        if _ensure_shortcut("Direction Generale", label, stype, target, color):
            shortcuts.append("Direction Generale / " + label)
    for label, stype, target, color in EQUIPE_SHORTCUTS:
        if _ensure_shortcut("Gestion Equipe", label, stype, target, color):
            shortcuts.append("Gestion Equipe / " + label)

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass
    print("[ensure_direction_oversight] %d perms + %d raccourcis" % (len(granted), len(shortcuts)))
    return {"granted": granted, "shortcuts": shortcuts}

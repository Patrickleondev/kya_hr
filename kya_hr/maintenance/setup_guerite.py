# -*- coding: utf-8 -*-
"""Poste de garde (Guérite) : rôle + accès + espace.

Sur le terrain, l'agent de guérite recueillait les fiches papier signées avant
de laisser sortir un employé/stagiaire. On lui donne :
  • le DROIT DE LECTURE sur les permissions de sortie (pour télécharger le PDF
    officiel signé depuis /guerite) — en Custom DocPerm car ces DocTypes sont
    custom=1 (les DocPerm standard du JSON ne sont pas resynchronisés) ;
  • un ESPACE « Guérite » avec un raccourci vers /guerite.

Lecture seule : la guérite ne fait que contrôler, aucun droit d'écriture.
Idempotent — appelé par safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import json

import frappe

ROLE = "Guérite"
DOCTYPES = ["Permission Sortie Employe", "Permission Sortie Stagiaire"]
WS = "Guérite"
MODULE = "KYA HR"


def _ensure_role():
    if not frappe.db.exists("Role", ROLE):
        r = frappe.new_doc("Role")
        r.role_name = ROLE
        r.desk_access = 1
        r.insert(ignore_permissions=True)
        return "role créé"
    return "role présent"


def _ensure_read_perms():
    """Lecture seule (read + print + report) sur les permissions de sortie."""
    from frappe.permissions import add_permission, update_permission_property
    done = []
    for dt in DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue
        has = frappe.db.get_value("Custom DocPerm",
                                  {"parent": dt, "role": ROLE, "permlevel": 0}, "name") \
            or frappe.db.get_value("DocPerm",
                                   {"parent": dt, "role": ROLE, "permlevel": 0}, "name")
        try:
            if not has:
                add_permission(dt, ROLE, 0)
            for right, val in (("read", "1"), ("print", "1"), ("report", "1"),
                               ("write", "0"), ("create", "0"), ("delete", "0")):
                update_permission_property(dt, ROLE, 0, right, val)
            done.append(dt)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "setup_guerite: perms " + dt)
    return done


def _ensure_workspace():
    """Espace « Guérite » minimal avec un raccourci vers la page /guerite."""
    if not frappe.db.exists("Workspace", WS):
        ws = frappe.new_doc("Workspace")
        ws.name = WS
        ws.title = WS
        ws.label = WS
        ws.module = MODULE
        ws.icon = "shield"
        ws.public = 1
        ws.is_hidden = 0
        ws.append("shortcuts", {
            "idx": 1, "type": "URL", "label": "Registre des sorties",
            "url": "/guerite", "color": "#0E7C4A",
        })
        ws.content = json.dumps([
            {"id": "gh", "type": "header",
             "data": {"text": "🛡️ Poste de garde — Guérite", "level": 3, "col": 12}},
            {"id": "gs", "type": "shortcut",
             "data": {"shortcut_name": "Registre des sorties", "col": 4}},
        ], ensure_ascii=False)
        try:
            ws.insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "setup_guerite: workspace")
            return "workspace KO"
        return "workspace créé"
    # existe déjà : garantir le raccourci
    if not frappe.db.exists("Workspace Shortcut", {"parent": WS, "url": "/guerite"}):
        mx = frappe.db.sql("SELECT COALESCE(MAX(idx),0) FROM `tabWorkspace Shortcut` WHERE parent=%s",
                           (WS,))[0][0] or 0
        sc = frappe.new_doc("Workspace Shortcut")
        sc.parent = WS
        sc.parenttype = "Workspace"
        sc.parentfield = "shortcuts"
        sc.idx = mx + 1
        sc.type = "URL"
        sc.label = "Registre des sorties"
        sc.url = "/guerite"
        sc.color = "#0E7C4A"
        sc.insert(ignore_permissions=True)
        return "raccourci ajouté"
    return "workspace présent"


def _ensure_workspace_role():
    """Rend l'espace visible AU rôle Guérite (Has Role sur le Workspace).
    ensure_workspace_roles (via WORKSPACE_ROLES) le ré-applique aussi à chaque
    migrate ; on le pose ici pour que ce soit effectif immédiatement."""
    if not frappe.db.exists("Workspace", WS):
        return "—"
    exists = frappe.db.exists("Has Role", {"parent": WS, "parenttype": "Workspace", "role": ROLE})
    if exists:
        return "role espace présent"
    ws = frappe.get_doc("Workspace", WS)
    ws.append("roles", {"role": ROLE})
    ws.save(ignore_permissions=True)
    return "role espace ajouté"


def execute():
    frappe.set_user("Administrator")
    steps = {
        "role": _ensure_role(),
        "perms": _ensure_read_perms(),
        "workspace": _ensure_workspace(),
        "ws_role": _ensure_workspace_role(),
    }
    frappe.db.commit()
    frappe.clear_cache()
    print("[setup_guerite]", steps)
    return steps


# alias
run = execute

# -*- coding: utf-8 -*-
"""Nettoyage des espaces de travail (Workspace) RH / Employés.

Ces workspaces vivent UNIQUEMENT en base (créés via Desk) — ce script rend les
corrections reproductibles. On édite directement la base (champ `content` +
table enfant `Workspace Shortcut`) car `doc.save()` bute sur des valeurs Select
héritées invalides dans d'autres lignes du même workspace.

Espace RH (centre de pilotage RH) :
  • retire les tuiles PERSONNELLES déplacées par erreur :
      - « Mon Espace (Chef Service) » (/mon-espace) → Espace Employés
      - « Mes Demandes » (/mes-demandes)            → Espace Employés
  • retire la tuile cassée « HRMS Dashboard » (→ /app/hrms : route inexistante
    en HRMS v16). « Rapports HRMS » (rapport Employee Information) est conservé.

Espace Employés :
  • ajoute « Mes Demandes » (/mes-demandes) à côté de « Mon Espace ».

Usage : bench --site frontend execute kya_hr.maintenance.fix_rh_workspace.run
"""
import json
import frappe

RH_REMOVE = {"Mon Espace (Chef Service)", "Mes Demandes", "HRMS Dashboard"}


def _content_without(ws_name, labels):
    content = json.loads(frappe.db.get_value("Workspace", ws_name, "content") or "[]")
    return [b for b in content
            if not (b.get("type") == "shortcut"
                    and b.get("data", {}).get("shortcut_name") in labels)]


def _remove_shortcuts(ws_name, labels):
    new_content = _content_without(ws_name, labels)
    frappe.db.set_value("Workspace", ws_name, "content", json.dumps(new_content),
                        update_modified=False)
    frappe.db.delete("Workspace Shortcut", {"parent": ws_name, "label": ["in", list(labels)]})
    remaining = frappe.get_all("Workspace Shortcut", filters={"parent": ws_name},
                               pluck="label", order_by="idx")
    return remaining


def _add_shortcut(ws_name, label, url, after_label=None):
    if frappe.db.exists("Workspace Shortcut", {"parent": ws_name, "label": label}):
        return "déjà présent"
    # nouvelle ligne enfant
    max_idx = frappe.db.sql(
        "select coalesce(max(idx),0) from `tabWorkspace Shortcut` where parent=%s",
        ws_name)[0][0]
    row = frappe.get_doc({
        "doctype": "Workspace Shortcut",
        "type": "URL", "label": label, "url": url,
        "parent": ws_name, "parenttype": "Workspace", "parentfield": "shortcuts",
        "idx": int(max_idx) + 1,
    })
    row.flags.ignore_permissions = True
    row.insert(ignore_permissions=True)

    # bloc content
    content = json.loads(frappe.db.get_value("Workspace", ws_name, "content") or "[]")
    block = {"type": "shortcut", "data": {"shortcut_name": label, "col": 4}}
    idx = None
    if after_label:
        for i, b in enumerate(content):
            if b.get("type") == "shortcut" and b.get("data", {}).get("shortcut_name") == after_label:
                idx = i + 1
                break
    if idx is None:
        idx = len(content)
        for i in range(len(content) - 1, -1, -1):
            if content[i].get("type") == "spacer":
                idx = i
                break
    content.insert(idx, block)
    frappe.db.set_value("Workspace", ws_name, "content", json.dumps(content),
                        update_modified=False)
    return "ajouté"


def run():
    kept = _remove_shortcuts("Espace RH", RH_REMOVE)
    print("Espace RH — tuiles restantes:", kept)
    res = _add_shortcut("Espace Employes", "Mes Demandes", "/mes-demandes", after_label="Mon Espace")
    print("Espace Employes — Mes Demandes:", res)
    frappe.db.commit()
    frappe.clear_cache()
    print("OK")

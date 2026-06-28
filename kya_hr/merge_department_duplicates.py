"""Fusion ONE-SHOT des départements doublons dans leur macro-groupe canonique.

⚠️ À lancer MANUELLEMENT (jamais au migrate — opération destructive) :
    bench --site <site> execute kya_hr.merge_department_duplicates.execute \
        --kwargs "{'dry_run': True}"
puis, après revue du rapport, relancer avec `{'dry_run': False}`.

Mécanique : `frappe.rename_doc(src, target, merge=True)` repointe TOUTES les
références (Employee.department, Equipe KYA.departement, congés, présences, etc.)
vers le macro-groupe cible PUIS supprime le doublon. Le doublon disparaît donc
partout (arbre Department, filtres, dashboards).

Tolérant : ignore une paire si le doublon n'existe pas (déjà fusionné / autre
site, ex. local). Idempotent (2e passage = tout skippé).
"""
from __future__ import annotations

import frappe

# (département doublon -> macro-groupe canonique). Spécifique prod KYA.
DUPLICATES = [
    ("Département Services Commerciaux - KYA", "Services Commerciaux - KYA"),
    ("Département des services techniques - KYA", "Services Technique - KYA"),
]

# Doctypes connus référençant un département (pour le rapport dry_run).
_REFERENCES = [("Employee", "department"), ("Equipe KYA", "departement")]


def _count_refs(dept: str) -> dict:
    out = {}
    for dt, field in _REFERENCES:
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            n = frappe.db.count(dt, {field: dept})
            if n:
                out[dt] = n
        except Exception:
            pass
    return out


def execute(dry_run: bool = True) -> dict:
    report = {"dry_run": bool(dry_run), "merged": [], "skipped": [], "errors": []}

    for src, target in DUPLICATES:
        if not frappe.db.exists("Department", src):
            report["skipped"].append(f"{src} (absent)")
            continue
        if not frappe.db.exists("Department", target):
            report["errors"].append(f"cible absente : {target}")
            continue
        if src == target:
            report["skipped"].append(f"{src} (src == cible)")
            continue
        refs = _count_refs(src)
        if dry_run:
            report["merged"].append({"src": src, "target": target,
                                     "refs_a_deplacer": refs, "simule": True})
            continue
        try:
            frappe.rename_doc("Department", src, target, merge=True)
            report["merged"].append({"src": src, "target": target,
                                     "refs_deplacees": refs})
        except Exception as e:
            report["errors"].append(f"{src} -> {target} : {str(e)[:160]}")
            frappe.log_error(frappe.get_traceback(), f"merge_dept {src}")

    if not dry_run and report["merged"]:
        try:
            from frappe.utils.nestedset import rebuild_tree
            rebuild_tree("Department", "parent_department")
            frappe.db.commit()
            frappe.clear_cache(doctype="Department")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "merge_dept: rebuild_tree")

    print(f"[merge_department_duplicates] dry_run={dry_run} "
          f"merged={len(report['merged'])} skipped={len(report['skipped'])} "
          f"errors={len(report['errors'])}")
    return report

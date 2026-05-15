# -*- coding: utf-8 -*-
"""Wrapper robuste pour after_migrate / after_install.

Problème historique : un script de migration qui plante (DocType manquant
sur une fresh install, bug Frappe v16 "'list' object is not callable", etc.)
faisait avorter toute la suite, laissant l'instance dans un état partiel
(icônes manquantes, workspaces non publiés, branding non posé).

Solution : on appelle chaque script dans son propre try/except. L'échec
d'un script est loggé via frappe.log_error mais N'INTERROMPT PAS les
suivants. La migration globale réussit toujours ; les erreurs sont
visibles dans Desk > Settings > Error Log.

Pour un re-run ciblé : `bench --site <site> execute
kya_hr.safe_migrations.retry_failed`.
"""
from __future__ import annotations

import traceback

import frappe


# Ordre exact des migrations historiques (cf. hooks.py:after_migrate).
# Une entrée = (chemin d'attribut, label humain pour le log).
AFTER_MIGRATE: list[tuple[str, str]] = [
    ("kya_hr.setup_locale.execute", "Setup locale (timezone, fuseau)"),
    ("kya_hr.setup_leave_types.execute", "Setup leave types HRMS"),
    ("kya_hr.force_sync_workspaces.execute", "Force sync workspaces"),
    ("kya_hr.force_publish_webforms.execute", "Force publish web forms"),
    ("kya_hr.force_resync_webform_fields.execute", "Force resync web form fields (Frappe v16 bug workaround)"),
    ("kya_hr.notification_fixes.execute", "Notification fixes"),
    ("kya_hr.setup_branding.execute", "Branding KYA (logos, couleurs)"),
    ("kya_hr.fix_all_workspaces.execute", "Fix all workspaces"),
    ("kya_hr.setup_fleet.run", "Setup fleet (DocType véhicule, etc.)"),
    ("kya_hr.setup_fleet_workspace.run", "Setup fleet workspace"),
    ("kya_hr.setup_fleet_dashboard.run", "Setup fleet dashboard"),
    ("kya_hr.setup_pv_extensions.run", "Setup PV extensions"),
    ("kya_hr.setup_retour_materiel.run", "Setup Retour Matériel + fournisseurs KYA"),
    ("kya_hr.setup_inventaire_dashboard.run", "Setup inventaire dashboard"),
    ("kya_hr.desktop_icons.execute", "Desktop icons (workaround Frappe v16)"),
    ("kya_hr.coherence_fixes.execute", "Coherence fixes (champs orphelins)"),
    ("kya_hr.ensure_visibility.execute", "Ensure workspaces visibility"),
]

AFTER_INSTALL: list[tuple[str, str]] = [
    ("kya_hr.desktop_icons.execute", "Desktop icons (install)"),
    ("kya_hr.coherence_fixes.execute", "Coherence fixes (install)"),
    ("kya_hr.ensure_visibility.execute", "Ensure visibility (install)"),
]


def _run_one(path: str, label: str) -> dict:
    """Exécute une migration, attrape toute exception, retourne un résumé."""
    result = {"label": label, "path": path, "ok": False, "error": None}
    try:
        fn = frappe.get_attr(path)
    except Exception as exc:
        result["error"] = f"Cannot import {path}: {exc}"
        _log(label, result["error"])
        return result

    if not callable(fn):
        result["error"] = f"{path} is not callable (type={type(fn).__name__})"
        _log(label, result["error"])
        return result

    try:
        fn()
        result["ok"] = True
    except Exception:
        tb = traceback.format_exc()
        result["error"] = tb
        _log(label, tb)
    return result


def _log(label: str, message: str) -> None:
    """Logue dans Error Log + console pour visibilité immédiate au bench migrate."""
    try:
        frappe.log_error(title=f"[safe_migrations] {label}", message=message[:140000])
    except Exception:
        pass
    # Affiche aussi dans le shell pour que le devops voie l'erreur dans le run de migrate.
    print(f"[kya_hr.safe_migrations] FAILED : {label}\n{message}")


def _run_all(table: list[tuple[str, str]], phase: str) -> dict:
    print(f"[kya_hr.safe_migrations] === {phase} : {len(table)} étapes ===")
    results = []
    ok_count = 0
    failed = []
    for path, label in table:
        res = _run_one(path, label)
        results.append(res)
        if res["ok"]:
            ok_count += 1
            print(f"  OK   {label}")
        else:
            failed.append(label)
            print(f"  FAIL {label} (voir Error Log)")
    print(
        f"[kya_hr.safe_migrations] {phase} terminé : "
        f"{ok_count}/{len(table)} OK, {len(failed)} en erreur."
    )
    try:
        frappe.db.commit()
    except Exception:
        pass
    return {"phase": phase, "ok": ok_count, "failed": failed, "details": results}


def after_migrate() -> dict:
    """Entrypoint pour hooks.after_migrate. Toujours retourne, ne lève jamais."""
    return _run_all(AFTER_MIGRATE, "after_migrate")


def after_install() -> dict:
    """Entrypoint pour hooks.after_install."""
    return _run_all(AFTER_INSTALL, "after_install")


@frappe.whitelist()
def retry_failed() -> dict:
    """Permet à un admin de re-rejouer la suite after_migrate à la main
    depuis le desk ou un bench execute. Utile après avoir corrigé un bug
    dans un script."""
    return after_migrate()

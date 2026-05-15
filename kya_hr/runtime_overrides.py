"""Overrides applied at runtime to prevent issues in CI / preprod / prod.

Fixes deux problèmes connus :

1. **ERPNext `setup_demo` timeout** : sur une fresh install via CI, le
   create-site script appelle l'API `setup_wizard.setup_complete` avec
   `setup_demo: True`. ERPNext enqueue alors `setup_demo_data` qui crée
   une "Demo Company" + import récursif du Chart of Accounts. Cette
   opération dépasse le timeout gunicorn par défaut (30s) → worker tué,
   la table `Supplier Group` reste avec un état NestedSet incohérent
   (cf. logs preprod du 14/05).

   Solution : monkey-patch `erpnext.setup.setup_wizard.setup_wizard.setup_demo`
   pour qu'il devienne **no-op**. Aucun risque côté KYA — on n'a jamais
   voulu de demo data, c'est juste un artefact du wizard.

2. **Timeout gunicorn trop court** : 30s c'est court même pour des
   migrations légitimes (Chart of Accounts initial, fixtures volumineux).
   On bumpe à 120s via `common_site_config.json` (lu par le runtime
   gunicorn à chaque démarrage de worker).

Idempotent. Sûr à appeler 1000 fois — chaque opération vérifie l'état
existant avant d'agir.
"""
from __future__ import annotations

import json
import os

import frappe


GUNICORN_TIMEOUT_SECONDS = 120


# --------------------------------------------------------------------------- #
# 1. ERPNext setup_demo → no-op
# --------------------------------------------------------------------------- #
def disable_erpnext_demo_setup(*_args, **_kwargs):
    """Monkey-patch `erpnext.setup.setup_wizard.setup_wizard.setup_demo`
    pour neutraliser le déclenchement automatique du demo data.

    Appelée par `boot_session` (= à chaque session). Idempotent : si déjà
    patché, on ne le refait pas.
    """
    try:
        from erpnext.setup.setup_wizard import setup_wizard as _wiz
    except Exception:  # erpnext absent (devrait pas arriver, mais safe)
        return

    if getattr(_wiz, "_kya_demo_disabled", False):
        return

    def _noop(args):  # même signature que l'original
        return None

    _wiz._kya_original_setup_demo = _wiz.setup_demo
    _wiz.setup_demo = _noop
    _wiz._kya_demo_disabled = True

    # Bonus : on patch aussi `setup_demo_data` au cas où il serait appelé
    # directement (ex. par un script CI custom).
    try:
        from erpnext.setup import demo as _demo
        if not getattr(_demo, "_kya_demo_disabled", False):
            _demo._kya_original_setup_demo_data = _demo.setup_demo_data
            _demo.setup_demo_data = lambda *_a, **_kw: None
            _demo._kya_demo_disabled = True
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# 2. Gunicorn worker timeout → 120s dans common_site_config.json
# --------------------------------------------------------------------------- #
def ensure_runtime_config():
    """Écrit dans `common_site_config.json` les overrides runtime qui doivent
    s'appliquer au prochain reboot du conteneur backend.

    Idempotent : ne touche le fichier que si la valeur diffère.
    """
    cfg_path = _common_site_config_path()
    if not cfg_path or not os.path.isfile(cfg_path):
        return

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        frappe.log_error(title="runtime_overrides: lecture common_site_config échouée",
                         message=frappe.get_traceback())
        return

    changed = False

    # gunicorn timeout — Frappe v16 lit `gunicorn_workers_timeout` au démarrage
    if cfg.get("gunicorn_workers_timeout") != GUNICORN_TIMEOUT_SECONDS:
        cfg["gunicorn_workers_timeout"] = GUNICORN_TIMEOUT_SECONDS
        changed = True

    # Désactive le wizard demo au niveau config aussi (ceinture + bretelles)
    if cfg.get("disable_demo_setup") is not True:
        cfg["disable_demo_setup"] = True
        changed = True

    if not changed:
        return

    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"[runtime_overrides] common_site_config.json mis à jour : "
              f"gunicorn_workers_timeout={GUNICORN_TIMEOUT_SECONDS}, disable_demo_setup=True. "
              f"Effet au prochain restart du conteneur backend.")
    except Exception:
        frappe.log_error(title="runtime_overrides: écriture common_site_config échouée",
                         message=frappe.get_traceback())


def _common_site_config_path():
    """Localise common_site_config.json (à côté des sites, racine bench).

    Sur Frappe Docker : /home/frappe/frappe-bench/sites/common_site_config.json
    """
    candidates = [
        os.path.join(frappe.utils.get_bench_path(), "sites", "common_site_config.json"),
        "/home/frappe/frappe-bench/sites/common_site_config.json",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


# --------------------------------------------------------------------------- #
# Entrypoint multi-purpose (utilisé par safe_migrations + boot_session)
# --------------------------------------------------------------------------- #
def execute():
    """Appliqué dans `after_install` / `after_migrate`.

    - Monkey-patch setup_demo (déclencheur principal du bug NestedSet)
    - Persiste la config runtime (timeout gunicorn + disable_demo_setup)
    """
    disable_erpnext_demo_setup()
    ensure_runtime_config()


def boot_session(bootinfo=None):  # signature attendue par Frappe
    """Hook `boot_session` : monkey-patch à chaque création de session.

    Garantit que même si le worker gunicorn redémarre, le patch est
    réappliqué avant tout traitement de la requête HTTP `setup_complete`.
    """
    disable_erpnext_demo_setup()

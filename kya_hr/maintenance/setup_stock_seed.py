# -*- coding: utf-8 -*-
"""SEED INITIAL DU STOCK — à partir du classeur fourni par l'équipe stock
(« Nouveau stock.xlsx », figé dans kya_hr/data/seed_stock_initial.json).

Objectif : au tout premier déploiement (image test / prod), le stock arrive
déjà peuplé ET correctement classé, SANS que quiconque ait à importer un
fichier à la main. Les équipes suivront ensuite le nouveau modèle via l'import
UI (même moteur, même classification → cohérence garantie).

Sûretés (« zéro bug au déploiement ») :
  • IDEMPOTENT : un drapeau (frappe defaults) empêche tout re-seed. En plus, si
    le grand livre stock contient DÉJÀ des mouvements, on NE seed PAS (on ne
    clobbère jamais un stock réel) — on se contente de poser le drapeau.
  • MÊME PIPELINE que l'import UI : _inject_sections (classification par section
    type_stock/famille/groupe + désambiguïsation Type-1/2/3) puis
    importer_stock_initial (résolution magasin, création article, ouverture
    idempotente par (article, magasin)).
  • MAPPING MAGASIN explicite vers les noms de la cible (prod/test « - KYA ») :
    le classeur mélange « Magasin KYA - KYA » et « SOGBOSSITO - D ».
  • Tout magasin non résolu est SIGNALÉ (console + Error Log), jamais silencieux.

Appelé par safe_migrations.AFTER_MIGRATE. N'échoue jamais le migrate.
"""
from __future__ import annotations

import json
import os

import frappe

_FLAG = "kya_stock_seed_initial"          # drapeau idempotence (frappe defaults)
_DATA = "data/seed_stock_initial.json"    # classeur figé (repo)

# Le classeur fourni mélange les suffixes société. La cible (prod/test) est en
# « - KYA ». On mappe explicitement ce qui diffère (identité sinon).
MAGASIN_MAP = {
    "SOGBOSSITO - D": "Magasin SOGBOSSITO - KYA",
    # « Magasin KYA - KYA » : déjà au nom prod → identité.
}


def _ledger_has_movements() -> bool:
    try:
        return bool(frappe.db.count("Mouvement Stock KYA"))
    except Exception:
        return False


def _load_rows():
    path = frappe.get_app_path("kya_hr", _DATA)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def execute() -> dict:
    frappe.set_user("Administrator")

    # 1) déjà seedé → ne rien faire
    if frappe.db.get_default(_FLAG):
        print("[setup_stock_seed] déjà appliqué (drapeau posé) — skip.")
        return {"status": "skip-flag"}

    # 2) un stock existe déjà → on ne clobbère jamais ; on pose juste le drapeau
    if _ledger_has_movements():
        frappe.db.set_default(_FLAG, "1")
        print("[setup_stock_seed] grand livre déjà peuplé — seed ignoré, drapeau posé.")
        return {"status": "skip-ledger-not-empty"}

    # 3) charge le classeur figé
    raw = _load_rows()
    if not raw:
        print("[setup_stock_seed] fichier data/seed_stock_initial.json absent — skip.")
        return {"status": "skip-no-file"}

    # 4) mapping magasin vers les noms de la cible
    for r in raw:
        mg = (r.get("magasin") or "").strip()
        if mg in MAGASIN_MAP:
            r["magasin"] = MAGASIN_MAP[mg]

    # 5) MÊME pipeline que l'import UI (section-aware) puis import idempotent
    from kya_hr.api.stock_kya import _inject_sections, importer_stock_initial

    # _inject_sections attend des dicts {en-tête minuscule: valeur} ORDONNÉS.
    rows = _inject_sections(raw)
    if not rows:
        print("[setup_stock_seed] aucune ligne article après classification — skip.")
        return {"status": "skip-no-rows"}

    res = importer_stock_initial(rows)

    # 6) trace explicite (surtout les magasins non résolus)
    intr = res.get("magasins_introuvables") or []
    msg = ("[setup_stock_seed] seed OK : %d article(s) créé(s), %d ligne(s) de "
           "stock, %d source(s), %d erreur(s)."
           % (res.get("articles_crees", 0), res.get("lignes_stock", 0),
              res.get("total", 0), len(res.get("erreurs") or [])))
    print(msg)
    if intr:
        warn = "[setup_stock_seed] ⚠ MAGASINS NON RÉSOLUS (aucune quantité posée) : " \
               + ", ".join("%s (%d lignes)" % (x["magasin"], x["lignes"]) for x in intr)
        print(warn)
        try:
            frappe.log_error(warn, "setup_stock_seed: magasins introuvables")
        except Exception:
            pass

    # 7) drapeau + commit
    frappe.db.set_default(_FLAG, "1")
    frappe.db.commit()
    return {"status": "seeded", **res}


# alias
run = execute

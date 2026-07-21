# -*- coding: utf-8 -*-
"""Répare les modèles de contrat éteints par la règle d'unicité trop large.

CONTEXTE (retour RH 07/2026 : « on voit Monsieur … Lawson-Body Phébée »)
`KYAContractTemplate.validate()` n'incluait pas `genre_cible` dans sa règle
« un seul template actif par type » : au sync des fixtures, l'insertion de
« CDD — Masculin » éteignait « CDD — Féminin ». Il ne restait donc AUCUN
template féminin actif, et `KYAContrat._select_template()` retombait sur le
masculin → contrats de femmes rédigés au masculin.

Le correctif de fond est dans validate() (le genre entre dans la clé). Ce
module répare l'existant : il rallume le template le plus récent de chaque
couple (type, genre) qui n'en a plus aucun d'actif. Idempotent.
"""
from __future__ import annotations

import frappe


def execute() -> dict:
    res = {"reactives": [], "deja_ok": 0}
    try:
        # On ne traite QUE les genres explicites : un couple (type, « Tous »)
        # sans actif correspond à d'anciens modèles volontairement retirés
        # (« Contrat CDD »…) — les rallumer réintroduirait des doublons.
        couples = frappe.db.sql(
            """SELECT DISTINCT contract_type, genre_cible
               FROM `tabKYA Contract Template`
               WHERE IFNULL(contract_type, '') != ''
                 AND genre_cible IN ('Masculin', 'Féminin')""",
            as_dict=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "fix_contract_templates_genre")
        return res

    for c in couples:
        actifs = frappe.db.count("KYA Contract Template", {
            "contract_type": c.contract_type,
            "genre_cible": c.genre_cible,
            "is_active": 1,
        })
        if actifs:
            res["deja_ok"] += 1
            continue

        # Aucun template actif pour ce couple → rallumer le plus récent.
        candidat = frappe.db.get_value(
            "KYA Contract Template",
            {"contract_type": c.contract_type, "genre_cible": c.genre_cible},
            "name",
            order_by="modified desc",
        )
        if not candidat:
            continue
        # db_set direct : passer par save() rejouerait validate() et pourrait
        # réélectroniser d'autres lignes ; ici on veut une réparation chirurgicale.
        frappe.db.set_value("KYA Contract Template", candidat, "is_active", 1,
                            update_modified=False)
        res["reactives"].append(candidat)

    frappe.db.commit()
    if res["reactives"]:
        print("[fix_contract_templates_genre] réactivés : %s" % res["reactives"])
    else:
        print("[fix_contract_templates_genre] rien à faire (%d couples OK)"
              % res["deja_ok"])
    return res

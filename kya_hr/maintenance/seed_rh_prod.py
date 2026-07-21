# Copyright (c) 2026, KYA-Energy Group
"""Amorçage du registre RH au déploiement (étape after_migrate).

But : au premier déploiement en prod, la RH ne doit pas découvrir un registre
vide et devoir tout ressaisir. Cette étape, lancée automatiquement par
`bench migrate`, fait deux choses SANS dépendre d'un fichier Excel (donc sans
mettre la moindre donnée personnelle dans le dépôt) :

1. **Backfill des Salariés** à partir des fiches Employee déjà présentes.
   Ainsi chaque personne déjà saisie côté HRMS existe aussi au registre, sans
   double saisie.
2. **Une étape « Embauche »** par salarié, déduite de sa date d'embauche, pour
   que la route de carrière s'affiche pour tout le monde dès le déploiement.

Le parcours détaillé (mutations, promotions) reste importé par la RH depuis son
classeur, en un clic sur /rh-effectifs : ces évènements ne sont pas déductibles
d'une fiche Employee, et le classeur (salaires, n° CNSS) n'a pas sa place dans
le code.

Garanties : non destructif (ne remplace jamais une saisie RH), idempotent
(rejouable à chaque migrate sans créer de doublon), ne lève jamais.
"""
import frappe


def _ensure_embauche_events() -> dict:
    """Crée une étape « Embauche » pour chaque salarié qui n'a AUCUN évènement.

    On ne touche pas aux salariés qui ont déjà un parcours (importé par la RH) :
    la condition « zéro évènement » garantit qu'on n'ajoute jamais une embauche
    en double, même après un import Excel ultérieur.
    """
    res = {"crees": 0, "sans_date": 0}
    sals = frappe.get_all(
        "Salarie KYA",
        fields=["name", "date_embauche", "type_contrat", "departement", "poste_occupe"],
        limit_page_length=0) or []
    for s in sals:
        if not s.get("date_embauche"):
            res["sans_date"] += 1
            continue
        if frappe.db.exists("Evolution Carriere KYA", {"salarie": s["name"]}):
            continue  # déjà un parcours -> on ne touche à rien
        try:
            champs = {"type_contrat": s.get("type_contrat") or None,
                      "departement": s.get("departement") or None,
                      "poste_occupe": s.get("poste_occupe") or None}
            doc = frappe.get_doc(dict(
                doctype="Evolution Carriere KYA", salarie=s["name"],
                date_debut=s["date_embauche"], nature_evolution="Embauche",
                motif_evolution="Recrutement initial",
                observation="Déduite de la date d'embauche du registre du personnel.",
                **{k: v for k, v in champs.items() if v not in (None, "")}))
            doc.flags.ignore_permissions = True
            doc.insert()
            res["crees"] += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), "seed_rh_prod._ensure_embauche_events")
    frappe.db.commit()
    return res


def execute() -> dict:
    """Entrypoint after_migrate : backfill Salariés + étape embauche."""
    res = {"salaries": {}, "embauches": {}}
    try:
        from kya_hr.api import rh_sync
        res["salaries"] = rh_sync.backfill_all(inclure_inactifs=1)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "seed_rh_prod: backfill salaries")
    try:
        res["embauches"] = _ensure_embauche_events()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "seed_rh_prod: embauche events")
    print("[seed_rh_prod] %s" % res)
    return res

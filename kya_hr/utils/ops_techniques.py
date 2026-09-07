"""Compteurs unifiés des opérations terrain (ancienne + nouvelle génération).

CONTEXTE MÉTIER
---------------
Chaque famille d'opération technique existe en DEUX doctypes en production, et
les deux sont alimentés EN PARALLÈLE tant que les équipes n'ont pas fini de
basculer sur les nouvelles fiches :

  * ancienne génération — module ``CRM``, web forms créés fév.–avr. 2026 ;
  * nouvelle génération — module ``KYA HR``, Web Pages du collègue technique
    (juin–juil. 2026), avec signature terrain.

Décision (07/09/2026) : tant que le personnel utilise encore l'ancienne fiche,
TOUTES les statistiques additionnent les deux sources, puis l'ancienne
s'éteindra d'elle-même quand plus personne ne la remplira. Il n'y a donc rien
à migrer ni à supprimer : on additionne, c'est tout.

POURQUOI CE MODULE
------------------
Avant, chaque tableau de bord recomptait les doctypes dans son coin, et le même
indicateur donnait trois réponses différentes selon la page ouverte :

  * ``direction_dashboard`` : 28 ordres de mission — un ``or`` s'arrêtait au
    premier doctype non vide, donc les 31 anciens étaient purement ignorés ;
  * ``services_techniques_dashboard`` : 31 — les anciens seulement, les
    nouveaux n'étaient même pas branchés ;
  * ``portail_pilotage`` : 59 — la somme, seul endroit juste.

Ce module est la SOURCE UNIQUE. Toute page qui compte une opération terrain
passe par ici et ne cite JAMAIS un nom de doctype en dur : ajouter une
troisième génération de fiches se fera à un seul endroit.

PIÈGES ENCODÉS ICI
------------------
* **Brouillons de test** : sur les nouveaux doctypes remplis depuis une Web
  Page, le collègue a laissé des enregistrements d'essai nommés au hasard
  (``jop9cduv43``, ``test 1``…) créés avant que la série de nommage ne soit
  branchée. On ne compte donc que les noms suivant la série (``FTB-%``…) quand
  une série existe.
* **Toutes les fiches n'ont PAS de série** : ``Ordre de mission2`` et
  ``fiche de mission`` sont nommés ``001/KEG/DG/2026``. Leur appliquer un
  filtre de préfixe renverrait 0 — d'où ``serie: None`` sur ces sources.
* **Le champ d'état change de nom d'une génération à l'autre**
  (``workflow_state`` sur l'ancienne fiche de mission, ``statut`` sur
  ``Ordre de mission2``) : la table fusionnée passe par une carte de champs.
* Tout est **défensif** : ces doctypes sont créés directement en production et
  sont absents des instances locales/préprod. Un doctype ou un champ manquant
  vaut 0 / valeur vide, jamais une exception.
"""

from __future__ import annotations

import frappe

# ── Familles d'opérations terrain ────────────────────────────────────────
# Ordre des sources : la NOUVELLE génération d'abord (celle qui doit rester),
# l'ancienne ensuite. `serie` = préfixe de naming series à exiger, ou None si
# le doctype n'en utilise pas. `champs` = carte {clé canonique: champ réel}
# pour fusionner les tableaux malgré les noms de champs divergents.
FAMILLES: dict[str, dict] = {
    "sav": {
        "label": "Interventions SAV",
        "sub": "maintenance curative",
        "sources": (
            {
                "doctype": "Fiche Compte Rendu Intervention",
                "generation": "nouvelle",
                "serie": "FCRI",
                "champs": {"client": "client_site", "ville": "ville",
                           "intervenant": "technicien_responsable",
                           "date": "date_intervention", "etat": "etat_final"},
            },
            {
                "doctype": "fiche technique curative",
                "generation": "ancienne",
                "serie": None,
                "champs": {"client": "clientsite", "intervenant": "techname",
                           "objet": "objinter", "date": "dateinter",
                           "etat": "etatsys"},
            },
        ),
    },
    "mission": {
        "label": "Ordres de mission",
        "sub": "déplacements terrain",
        "sources": (
            {
                "doctype": "Ordre de mission2",
                "generation": "nouvelle",
                "serie": None,  # nommage 001/KEG/DG/2026, pas de préfixe
                "champs": {"chef": "chef_mission", "destination": "destination",
                           "objet": "objet_mission", "date": "date_emission",
                           "etat": "statut"},
            },
            {
                "doctype": "fiche de mission",
                "generation": "ancienne",
                "serie": None,
                "champs": {"chef": "chef_mission", "destination": "destination",
                           "objet": "objet", "date": "date_emission",
                           "etat": "workflow_state"},
            },
        ),
    },
    "recep_batterie": {
        "label": "Fiches batteries",
        "sub": "contrôle qualité batterie",
        "sources": (
            {"doctype": "Fiche Technique Batterie", "generation": "nouvelle",
             "serie": "FTB", "champs": {}},
            {"doctype": "fiche de recpt de batt", "generation": "ancienne",
             "serie": None, "champs": {}},
        ),
    },
    "recep_lampadaire": {
        "label": "Fiches lampadaires",
        "sub": "contrôle qualité lampadaire",
        "sources": (
            {"doctype": "Fiche Technique Lampadaire", "generation": "nouvelle",
             "serie": "FTL", "champs": {}},
            {"doctype": "fiche_recep_tech_lampa", "generation": "ancienne",
             "serie": None, "champs": {}},
        ),
    },
}


# ── Helpers défensifs ────────────────────────────────────────────────────
def _dt_exists(dt: str) -> bool:
    try:
        return bool(frappe.db.exists("DocType", dt))
    except Exception:
        return False


def _champs_reels(dt: str, souhaites: list[str]) -> list[str]:
    """Ne garde que les champs réellement présents sur le doctype.

    Les fiches du collègue évoluent directement en production : demander un
    champ supprimé entre-temps ferait échouer toute la requête (et viderait le
    tableau) au lieu de dégrader proprement une seule colonne.
    """
    try:
        meta = frappe.get_meta(dt)
    except Exception:
        return ["name"]
    gardes = ["name"]
    for f in souhaites:
        if f and f != "name" and meta.has_field(f):
            gardes.append(f)
    return gardes


def _compter_source(source: dict, depuis: str | None = None) -> int:
    dt = source["doctype"]
    if not _dt_exists(dt):
        return 0
    filtres: dict = {}
    if source.get("serie"):
        filtres["name"] = ["like", f"{source['serie']}-%"]
    if depuis:
        filtres["creation"] = [">=", depuis]
    try:
        return frappe.db.count(dt, filtres)
    except Exception:
        return 0


# ── API publique ─────────────────────────────────────────────────────────
def compter(famille: str, depuis: str | None = None) -> int:
    """Total combiné ancienne + nouvelle génération pour une famille."""
    fam = FAMILLES.get(famille)
    if not fam:
        return 0
    return sum(_compter_source(s, depuis) for s in fam["sources"])


def detail(famille: str, depuis: str | None = None) -> dict:
    """Total + ventilation par génération, pour afficher un sous-titre honnête
    (« 77 nouvelles · 119 anciennes ») plutôt qu'un chiffre opaque."""
    fam = FAMILLES.get(famille)
    if not fam:
        return {"total": 0, "nouvelle": 0, "ancienne": 0, "label": famille, "sub": ""}
    par_gen = {"nouvelle": 0, "ancienne": 0}
    for s in fam["sources"]:
        par_gen[s["generation"]] = par_gen.get(s["generation"], 0) + _compter_source(s, depuis)
    return {
        "total": par_gen["nouvelle"] + par_gen["ancienne"],
        "nouvelle": par_gen["nouvelle"],
        "ancienne": par_gen["ancienne"],
        "label": fam["label"],
        "sub": fam["sub"],
    }


def sous_titre(famille: str, depuis: str | None = None) -> str:
    """Sous-titre prêt à afficher sur une carte de tableau de bord.

    Tant que l'ancienne fiche est encore alimentée, on rend la cohabitation
    VISIBLE (« 77 nouvelles · 119 anciennes ») : c'est ce qui permet à la
    Direction de voir la bascule progresser, puis de décider d'éteindre
    l'ancienne quand elle tombe à 0.
    """
    d = detail(famille, depuis)
    n, a = d["nouvelle"], d["ancienne"]
    if a and n:
        return f"{n} nouvelle{'s' if n > 1 else ''} · {a} ancienne{'s' if a > 1 else ''}"
    if a:
        return f"{a} ancienne{'s' if a > 1 else ''} fiche{'s' if a > 1 else ''}"
    return d["sub"]


def doctypes(famille: str) -> tuple[str, ...]:
    fam = FAMILLES.get(famille)
    return tuple(s["doctype"] for s in fam["sources"]) if fam else ()


def lignes(famille: str, limit: int = 8) -> list[dict]:
    """Dernières fiches des DEUX générations, fusionnées et triées par date.

    Chaque ligne porte sa `generation` pour que l'interface puisse marquer
    d'où vient l'enregistrement (utile pendant la cohabitation).
    """
    fam = FAMILLES.get(famille)
    if not fam:
        return []
    out: list[dict] = []
    for source in fam["sources"]:
        dt = source["doctype"]
        if not _dt_exists(dt):
            continue
        carte = source.get("champs") or {}
        demandes = _champs_reels(dt, list(carte.values()))
        filtres: dict = {}
        if source.get("serie"):
            filtres["name"] = ["like", f"{source['serie']}-%"]
        try:
            rows = frappe.get_all(dt, filters=filtres, fields=demandes + ["creation"],
                                  order_by="creation desc", limit_page_length=limit)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"ops_techniques: {dt}")
            continue
        for r in rows:
            ligne = {"ref": r.get("name"), "generation": source["generation"],
                     "doctype": dt, "creation": r.get("creation")}
            for cle, champ in carte.items():
                ligne[cle] = r.get(champ) if champ in demandes else None
            out.append(ligne)
    out.sort(key=lambda x: (x.get("date") or x.get("creation") or ""), reverse=True)
    return out[:limit]

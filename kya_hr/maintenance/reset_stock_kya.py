# -*- coding: utf-8 -*-
"""Remise à zéro / nettoyage du stock d'un magasin — SÛR et SIMULABLE.

Contexte : avant de démarrer les opérations réelles, la magasinière veut repartir
d'un magasin vide, puis ré-importer l'inventaire réel. Ce module offre des outils
prudents, chacun avec un mode `dry_run` (simulation) qui n'écrit RIEN et se
contente de dire ce qui SERAIT fait.

Deux « stocks » peuvent coexister :
- **Maison** : grand-livre `Mouvement Stock KYA` (ce que lit le cockpit /stock-kya).
- **Natif** : Bin/Stock Entry ERPNext (l'ancien système, encore rempli en prod).

Fonctions :
- `apercu(magasin)`            : état des deux stocks pour un magasin (lecture seule).
- `vider_maison(magasin)`      : supprime les mouvements maison du magasin.
- `zero_natif(magasin)`        : met à 0 le stock natif via une Stock Reconciliation
                                 (méthode propre ERPNext, auditable, réversible par annulation).
- `desactiver_articles_absents(codes_gardes)` : désactive (n'efface PAS) les Items hors
                                 d'une liste à garder — pour nettoyer le catalogue encombré.

TOUJOURS lancer d'abord avec dry_run=1, lire le rapport, puis relancer dry_run=0.
"""
from __future__ import annotations

import frappe
from frappe.utils import flt, today


def _as_bool(v) -> bool:
    return str(v) not in ("0", "false", "False", "", "None")


# ── Lecture seule : état des deux stocks ────────────────────────────────────
@frappe.whitelist()
def apercu(magasin: str) -> dict:
    """État complet d'un magasin (ne modifie rien)."""
    out: dict = {"magasin": magasin, "maison": {}, "natif": {}}

    if frappe.db.exists("DocType", "Mouvement Stock KYA"):
        rows = frappe.get_all("Mouvement Stock KYA", filters={"magasin": magasin},
                              fields=["name"], limit=0)
        out["maison"]["mouvements"] = len(rows)
    else:
        out["maison"]["mouvements"] = "doctype absent (pas encore déployé)"

    bins = frappe.get_all("Bin", filters={"warehouse": magasin, "actual_qty": ["!=", 0]},
                          fields=["item_code", "actual_qty"], limit=0)
    out["natif"]["bins_non_nuls"] = len(bins)
    out["natif"]["unites_totales"] = round(sum(flt(b.actual_qty) for b in bins), 2)
    out["natif"]["exemples"] = bins[:10]
    return out


# ── Vider le grand-livre maison d'un magasin ────────────────────────────────
@frappe.whitelist()
def vider_maison(magasin: str, dry_run=1) -> dict:
    """Supprime tous les mouvements maison du magasin (le cockpit repart à 0).
    Réimportable ensuite via l'import Excel. dry_run=1 => simulation."""
    dry = _as_bool(dry_run)
    if not frappe.db.exists("DocType", "Mouvement Stock KYA"):
        return {"magasin": magasin, "erreur": "Grand-livre maison absent (déployer d'abord)."}
    names = frappe.get_all("Mouvement Stock KYA", filters={"magasin": magasin}, pluck="name")
    if not dry:
        for nm in names:
            frappe.delete_doc("Mouvement Stock KYA", nm, ignore_permissions=True, force=True)
        frappe.db.commit()
    return {"magasin": magasin, "dry_run": dry,
            "mouvements_supprimes" if not dry else "mouvements_a_supprimer": len(names)}


# ── Mettre à 0 le stock natif (Stock Reconciliation) ────────────────────────
@frappe.whitelist()
def zero_natif(magasin: str, company: str | None = None, dry_run=1) -> dict:
    """Met à 0 toutes les quantités natives (Bin) du magasin via une
    Stock Reconciliation soumise (méthode ERPNext propre : traçable, annulable).
    dry_run=1 => on liste seulement ce qui serait remis à 0."""
    dry = _as_bool(dry_run)
    bins = frappe.get_all("Bin", filters={"warehouse": magasin, "actual_qty": ["!=", 0]},
                          fields=["item_code", "actual_qty"], limit=0)
    res = {"magasin": magasin, "dry_run": dry, "articles_concernes": len(bins),
           "unites_avant": round(sum(flt(b.actual_qty) for b in bins), 2)}
    if not bins:
        res["message"] = "Rien à faire : stock natif déjà vide."
        return res
    if dry:
        res["exemples"] = bins[:15]
        return res

    company = company or frappe.db.get_value("Warehouse", magasin, "company") \
        or frappe.defaults.get_global_default("company")
    sr = frappe.new_doc("Stock Reconciliation")
    sr.purpose = "Stock Reconciliation"
    sr.company = company
    sr.set_posting_time = 1
    sr.posting_date = today()
    for b in bins:
        sr.append("items", {"item_code": b.item_code, "warehouse": magasin,
                            "qty": 0, "valuation_rate": 0})
    sr.flags.ignore_permissions = True
    sr.insert()
    sr.submit()
    frappe.db.commit()
    res["stock_reconciliation"] = sr.name
    res["message"] = "Stock natif remis à 0 (annulable en annulant ce document)."
    return res


# ── Nettoyer le catalogue : désactiver les Items hors liste ─────────────────
@frappe.whitelist()
def desactiver_articles_absents(codes_gardes, dry_run=1) -> dict:
    """Désactive (disabled=1, NON supprimé, réversible) tout Item dont le code
    n'est PAS dans `codes_gardes`. Sert à masquer les centaines d'articles de test
    du catalogue sans rien perdre. `codes_gardes` = liste ou CSV de codes à garder.
    dry_run=1 => simulation."""
    dry = _as_bool(dry_run)
    if isinstance(codes_gardes, str):
        codes_gardes = [c.strip() for c in codes_gardes.replace("\n", ",").split(",") if c.strip()]
    garder = set(codes_gardes or [])
    # On ne touche QUE les articles de stock (pas les services / modèles / articles
    # de nomenclature), pour ne rien casser d'autre dans ERPNext.
    tous = frappe.get_all("Item", filters={"disabled": 0, "is_stock_item": 1},
                          fields=["name"], limit=0)
    a_desactiver = [it.name for it in tous if it.name not in garder]
    if not dry:
        for code in a_desactiver:
            frappe.db.set_value("Item", code, "disabled", 1, update_modified=False)
        frappe.db.commit()
    return {"dry_run": dry, "gardes": len(garder), "total_actifs": len(tous),
            ("desactives" if not dry else "a_desactiver"): len(a_desactiver),
            "exemples": a_desactiver[:20]}

"""Stock par état KYA — routage des retours matériel + vue consolidée.

Au retour d'un matériel sorti, chaque article revient dans un état :
  - Bon état  → reste/retourne dans son magasin normal (stock DISPONIBLE)
  - À réparer  → magasin « Atelier-Reparation »  (stock immobilisé, réparable)
  - Endommagé  → magasin « Materiel-Endommage »  (hors service, candidat rebut)

Trois magasins distincts ⇒ l'état est porté par le STOCK lui-même (pas seulement
sur le PV de retour) : un inventaire par magasin compte et distingue chaque état,
et la vue consolidée `get_stock_par_etat()` montre tout par article.

Module partagé : utilisé par le doctype Retour Materiel KYA (routage Stock Entry)
et par la page /stock-etat (vue Responsable Stock + Direction).
"""
from __future__ import annotations

import frappe
from frappe import _

# Noms de base des magasins spéciaux (le suffixe « - <abbr> » est ajouté par
# ERPNext). Ne JAMAIS renommer « Atelier-Reparation » : déjà créé sur les
# instances existantes (compat données).
REPAIR_WAREHOUSE_NAME = "Atelier-Reparation"     # À réparer
DAMAGED_WAREHOUSE_NAME = "Materiel-Endommage"     # Endommagé


def get_or_create_warehouse(company: str | None, base_name: str) -> str | None:
    """Renvoie le nom complet du magasin (le crée s'il manque pour la company)."""
    if not company:
        return None
    abbr = frappe.db.get_value("Company", company, "abbr")
    full_name = f"{base_name} - {abbr}" if abbr else base_name
    if frappe.db.exists("Warehouse", full_name):
        return full_name
    try:
        wh = frappe.new_doc("Warehouse")
        wh.warehouse_name = base_name
        wh.company = company
        wh.is_group = 0
        wh.insert(ignore_permissions=True)
        return wh.name
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"stock_etats: création warehouse {base_name}")
        return None


def warehouse_for_etat(company: str | None, etat: str | None) -> tuple[str, str | None]:
    """Renvoie (clé_etat, magasin_special|None) pour un état de retour.

    clé_etat ∈ {'disponible','a_reparer','endommage'}. Pour 'disponible',
    le magasin reste celui choisi par l'utilisateur (None ici).
    """
    e = _norm_etat(etat)
    if e == "a_reparer":
        return "a_reparer", get_or_create_warehouse(company, REPAIR_WAREHOUSE_NAME)
    if e == "endommage":
        return "endommage", get_or_create_warehouse(company, DAMAGED_WAREHOUSE_NAME)
    return "disponible", None


def _norm_etat(etat: str | None) -> str:
    """Normalise l'état (tolère accents/casse) -> clé technique."""
    e = (etat or "").strip().lower()
    if e.startswith("à répar") or e.startswith("a repar") or "répar" in e or "repar" in e:
        return "a_reparer"
    if "défect" in e or "defect" in e or "endommag" in e or "hors" in e or "rebut" in e:
        return "endommage"
    return "disponible"


def _classify_warehouse(name: str, warehouse_name: str | None) -> str:
    """Classe un magasin -> 'a_reparer' | 'endommage' | 'disponible'."""
    blob = f"{name or ''} {warehouse_name or ''}".lower()
    if REPAIR_WAREHOUSE_NAME.lower() in blob or "atelier-repar" in blob:
        return "a_reparer"
    if DAMAGED_WAREHOUSE_NAME.lower() in blob or "endommag" in blob:
        return "endommage"
    return "disponible"


# Mapping état du ledger maison -> clé de la vue consolidée. Vocabulaire unique
# = Bon état / À réparer / Défectueux (anciens libellés reconnus pour compat).
_ETAT_TO_KEY = {
    "Bon état": "disponible", "Neuf": "disponible",
    "À réparer": "a_reparer", "En réparation": "a_reparer",
    "Défectueux": "endommage", "Hors service": "endommage", "Endommagé": "endommage",
}


@frappe.whitelist()
def get_stock_par_etat(search: str | None = None) -> dict:
    """Vue consolidée du stock par état (disponible / à réparer / endommagé).

    Source = grand livre maison `Mouvement Stock KYA` (l'état est une COLONNE du
    stock, plus un magasin spécial). Quantités uniquement (pas de valorisation
    en maison → valeur = 0). Sert la page /stock-etat (Resp. Stock + Direction).
    """
    rows = frappe.db.sql(
        """
        SELECT m.item AS item_code, MAX(m.item_name) AS item_name,
               m.etat AS etat, SUM(m.quantite) AS qty
        FROM `tabMouvement Stock KYA` m
        GROUP BY m.item, m.etat
        """,
        as_dict=True,
    )
    unites = dict(frappe.get_all("Article KYA", fields=["name", "unite"],
                                 as_list=True)) if rows else {}

    items: dict[str, dict] = {}
    tot = {"disponible": 0.0, "a_reparer": 0.0, "endommage": 0.0,
           "val_disponible": 0.0, "val_a_reparer": 0.0, "val_endommage": 0.0}
    for r in rows:
        key = r.item_code
        it = items.get(key)
        if not it:
            it = {"item_code": r.item_code, "item_name": r.item_name or r.item_code,
                  "uom": unites.get(r.item_code, ""), "disponible": 0.0,
                  "a_reparer": 0.0, "endommage": 0.0, "valeur": 0.0}
            items[key] = it
        etat = _ETAT_TO_KEY.get((r.etat or "").strip(), "disponible")
        qty = float(r.qty or 0)
        it[etat] += qty
        tot[etat] += qty

    # On ne garde que les articles avec du stock (somme des états non nulle).
    data = [d for d in items.values()
            if abs(d["disponible"]) + abs(d["a_reparer"]) + abs(d["endommage"]) > 1e-9]
    if search:
        s = search.lower().strip()
        data = [d for d in data if s in (d["item_name"] or "").lower()
                or s in (d["item_code"] or "").lower()]
    # Priorité d'affichage : ce qui a du à-réparer / endommagé d'abord
    data.sort(key=lambda d: (-(d["a_reparer"] + d["endommage"]), d["item_name"].lower()))

    for k in ("disponible", "a_reparer", "endommage",
              "val_disponible", "val_a_reparer", "val_endommage"):
        tot[k] = round(tot[k], 2)

    return {
        "items": [{**d, "disponible": round(d["disponible"], 2),
                   "a_reparer": round(d["a_reparer"], 2),
                   "endommage": round(d["endommage"], 2),
                   "valeur": round(d["valeur"], 2)} for d in data],
        "totaux": tot,
        "nb_items": len(data),
        "nb_a_reparer": sum(1 for d in data if d["a_reparer"] > 0),
        "nb_endommage": sum(1 for d in data if d["endommage"] > 0),
    }

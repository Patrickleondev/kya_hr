# -*- coding: utf-8 -*-
"""API du stock KYA maison (grand livre `Mouvement Stock KYA`).

Le stock n'est PAS géré par ERPNext (pas de Stock Entry / Bin / valuation).
On tient notre propre grand livre signé et on calcule les soldes à la volée.

- enregistrer_mouvements / supprimer_mouvements : écrit/retire les lignes du
  ledger pour une fiche source (appelé par les on_submit / on_cancel des PV).
- soldes / solde_item_magasin : soldes calculés (total / bon état / réparation).
- etat_inventaire : soldes formatés comme la fiche « État d'inventaire » (par
  magasin), pour pré-remplir/afficher l'inventaire au format KYA.
- importer_articles : crée les Items depuis un import (Code/Groupe/UdM/Nom).
"""
import frappe
from frappe import _
from frappe.utils import flt, today

# États comptant comme stock « disponible » (bon état) vs « en réparation ».
_BON = ("Bon état", "Neuf")
_REPAR = ("En réparation",)

_STOCK_ROLES = {"System Manager", "Stock Manager", "Stock User",
                "Responsable Stock", "Chargé des Stocks",
                "Directeur Général", "DGA", "Auditeur Interne", "DAAF"}
_WRITE_ROLES = {"System Manager", "Stock Manager",
                "Responsable Stock", "Chargé des Stocks"}


def _guard(write=False):
    roles = set(frappe.get_roles(frappe.session.user))
    needed = _WRITE_ROLES if write else _STOCK_ROLES
    if not (needed & roles):
        frappe.throw(_("Accès réservé au magasin / stock."), frappe.PermissionError)


# ── Écriture du grand livre (appelé par les fiches) ────────────────────────
def enregistrer_mouvements(rows, type_mouvement, reference_doctype=None,
                           reference_name=None, date_mouvement=None, commit=False):
    """Écrit une liste de mouvements. `rows` = [{item, magasin, quantite, etat,
    remarque}]. La quantité est déjà signée par l'appelant (ou on applique le
    signe selon type_mouvement si positive). Retourne le nombre de lignes."""
    n = 0
    dt = date_mouvement or today()
    for r in rows:
        item = r.get("item")
        magasin = r.get("magasin")
        qte = flt(r.get("quantite"))
        if not item or not magasin or not qte:
            continue
        # Sécurité : une Sortie doit décrémenter (quantité négative).
        if type_mouvement == "Sortie" and qte > 0:
            qte = -qte
        if type_mouvement in ("Entrée", "Retour") and qte < 0:
            qte = -qte
        doc = frappe.new_doc("Mouvement Stock KYA")
        doc.date_mouvement = dt
        doc.type_mouvement = type_mouvement
        doc.item = item
        doc.magasin = magasin
        doc.quantite = qte
        doc.etat = r.get("etat") or "Bon état"
        doc.reference_doctype = reference_doctype
        doc.reference_name = reference_name
        doc.remarque = r.get("remarque")
        doc.flags.ignore_permissions = True
        doc.insert()
        n += 1
    if commit:
        frappe.db.commit()
    return n


def supprimer_mouvements(reference_doctype, reference_name, commit=False):
    """Retire du ledger tous les mouvements d'une fiche (annulation)."""
    if not reference_name:
        return 0
    names = frappe.get_all("Mouvement Stock KYA",
                           filters={"reference_doctype": reference_doctype,
                                    "reference_name": reference_name},
                           pluck="name")
    for nm in names:
        frappe.delete_doc("Mouvement Stock KYA", nm, ignore_permissions=True, force=True)
    if commit:
        frappe.db.commit()
    return len(names)


# ── Calcul des soldes ──────────────────────────────────────────────────────
def _bucketize(rows):
    """rows = [{item, item_name, magasin, etat, q}] -> agrège par (item, magasin)."""
    agg = {}
    for r in rows:
        key = (r["item"], r["magasin"])
        d = agg.setdefault(key, {"item": r["item"], "item_name": r.get("item_name") or r["item"],
                                 "magasin": r["magasin"], "bon_etat": 0.0,
                                 "reparation": 0.0, "autre": 0.0, "total": 0.0})
        q = flt(r["q"])
        if r["etat"] in _BON:
            d["bon_etat"] += q
        elif r["etat"] in _REPAR:
            d["reparation"] += q
        else:
            d["autre"] += q
    for d in agg.values():
        d["total"] = round(d["bon_etat"] + d["reparation"], 3)
        for k in ("bon_etat", "reparation", "autre"):
            d[k] = round(d[k], 3)
    return agg


def _raw_sums(magasin=None, item=None):
    conds = ["1=1"]
    params = {}
    if magasin:
        conds.append("m.magasin = %(mag)s")
        params["mag"] = magasin
    if item:
        conds.append("m.item = %(it)s")
        params["it"] = item
    return frappe.db.sql(f"""
        SELECT m.item AS item, MAX(m.item_name) AS item_name, m.magasin AS magasin,
               m.etat AS etat, SUM(m.quantite) AS q
        FROM `tabMouvement Stock KYA` m
        WHERE {' AND '.join(conds)}
        GROUP BY m.item, m.magasin, m.etat
    """, params, as_dict=True)


@frappe.whitelist()
def solde_item_magasin(item, magasin):
    _guard()
    agg = _bucketize(_raw_sums(magasin=magasin, item=item))
    return agg.get((item, magasin), {"item": item, "magasin": magasin,
                                     "bon_etat": 0, "reparation": 0, "total": 0})


@frappe.whitelist()
def soldes(magasin=None, item=None, only_nonzero=1):
    """Liste des soldes calculés par (article, magasin)."""
    _guard()
    agg = _bucketize(_raw_sums(magasin=magasin, item=item))
    out = list(agg.values())
    if str(only_nonzero) not in ("0", "false", "False"):
        out = [d for d in out if abs(d["total"]) > 1e-9 or abs(d["autre"]) > 1e-9]
    out.sort(key=lambda d: (d["magasin"], d["item_name"]))
    return out


@frappe.whitelist()
def etat_inventaire(magasin=None):
    """Soldes groupés par magasin, au format de la fiche État d'inventaire."""
    _guard()
    rows = soldes(magasin=magasin, only_nonzero=1)
    par_magasin = {}
    for d in rows:
        par_magasin.setdefault(d["magasin"], []).append(d)
    sections = []
    for mag in sorted(par_magasin):
        lignes = []
        for i, d in enumerate(par_magasin[mag], start=1):
            lignes.append({"n": i, "item": d["item"], "designation": d["item_name"],
                           "qte_totale": d["total"], "bon_etat": d["bon_etat"],
                           "reparation": d["reparation"], "obs": ""})
        sections.append({"magasin": mag, "lignes": lignes,
                         "total_lignes": len(lignes)})
    return {"sections": sections, "genere_le": today()}


# ── Masters (pickers) ───────────────────────────────────────────────────────
@frappe.whitelist()
def magasins():
    _guard()
    return frappe.get_all("Warehouse", filters={"disabled": 0},
                          fields=["name", "warehouse_name"], order_by="name asc")


# ── Import d'articles ───────────────────────────────────────────────────────
def _ensure_item_group(groupe):
    groupe = (groupe or "").strip() or "Tous les Groupes d'Articles"
    if frappe.db.exists("Item Group", groupe):
        return groupe
    parent = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ""}, "name") \
        or frappe.db.get_value("Item Group", {"is_group": 1}, "name") \
        or "All Item Groups"
    try:
        g = frappe.new_doc("Item Group")
        g.item_group_name = groupe
        g.parent_item_group = parent
        g.is_group = 0
        g.flags.ignore_permissions = True
        g.insert()
    except Exception:
        return parent
    return groupe


def _ensure_uom(uom):
    uom = (uom or "").strip() or "Unit"
    if not frappe.db.exists("UOM", uom):
        try:
            frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)
        except Exception:
            return "Unit" if frappe.db.exists("UOM", "Unit") else "Nos"
    return uom


_REF_IMPORT = "Import Stock Initial"


@frappe.whitelist()
def importer_stock_initial(rows):
    """Import « template » : crée les articles ET les classe dans leur magasin
    avec un stock d'ouverture. `rows` = [{code, nom, groupe, uom, magasin,
    bon_etat, reparation}]. Idempotent : ré-importer une ligne (même article +
    magasin) REMPLACE son ouverture (on ne cumule pas). Réservé au magasin."""
    _guard(write=True)
    if isinstance(rows, str):
        rows = frappe.parse_json(rows)
    cree_item, maj_item, lignes_stock, erreurs = 0, 0, 0, []
    for r in rows:
        code = (r.get("code") or "").strip()
        nom = (r.get("nom") or code).strip()
        magasin = (r.get("magasin") or "").strip()
        if not code:
            continue
        try:
            groupe = _ensure_item_group(r.get("groupe"))
            uom = _ensure_uom(r.get("uom"))
            if frappe.db.exists("Item", code):
                it = frappe.get_doc("Item", code)
                changed = False
                if nom and it.item_name != nom:
                    it.item_name = nom; changed = True
                if groupe and it.item_group != groupe:
                    it.item_group = groupe; changed = True
                if changed:
                    it.flags.ignore_permissions = True; it.save(); maj_item += 1
            else:
                it = frappe.new_doc("Item")
                it.item_code = code; it.item_name = nom
                it.item_group = groupe; it.stock_uom = uom; it.is_stock_item = 1
                it.flags.ignore_permissions = True; it.insert(); cree_item += 1

            if magasin and frappe.db.exists("Warehouse", magasin):
                bon = flt(r.get("bon_etat"))
                repar = flt(r.get("reparation"))
                # Remplace l'ouverture précédente de cet article dans ce magasin.
                old = frappe.get_all("Mouvement Stock KYA",
                    filters={"reference_doctype": _REF_IMPORT, "reference_name": magasin,
                             "item": code}, pluck="name")
                for nm in old:
                    frappe.delete_doc("Mouvement Stock KYA", nm, ignore_permissions=True, force=True)
                op = []
                if bon:
                    op.append({"item": code, "magasin": magasin, "quantite": bon, "etat": "Bon état"})
                if repar:
                    op.append({"item": code, "magasin": magasin, "quantite": repar, "etat": "En réparation"})
                if op:
                    enregistrer_mouvements(op, "Inventaire", reference_doctype=_REF_IMPORT,
                                           reference_name=magasin)
                    lignes_stock += 1
        except Exception:
            erreurs.append(code)
            frappe.log_error(frappe.get_traceback(), "stock_kya.importer_stock_initial")
    frappe.db.commit()
    return {"items_crees": cree_item, "items_maj": maj_item,
            "lignes_stock": lignes_stock, "erreurs": erreurs, "total": len(rows)}


@frappe.whitelist()
def dashboard_overview():
    """Indicateurs temps réel du stock maison (pour le cockpit)."""
    _guard()
    lignes = soldes(only_nonzero=1)
    magasins_set = {d["magasin"] for d in lignes}
    articles_set = {d["item"] for d in lignes}
    en_reparation = sum(1 for d in lignes if d["reparation"] > 0)
    ruptures = sum(1 for d in lignes if d["total"] <= 0)
    total_unites = round(sum(d["total"] for d in lignes), 2)
    # Par magasin : nb articles + unités
    par_mag = {}
    for d in lignes:
        m = par_mag.setdefault(d["magasin"], {"magasin": d["magasin"], "articles": 0, "unites": 0.0,
                                              "bon_etat": 0.0, "reparation": 0.0})
        m["articles"] += 1
        m["unites"] = round(m["unites"] + d["total"], 2)
        m["bon_etat"] = round(m["bon_etat"] + d["bon_etat"], 2)
        m["reparation"] = round(m["reparation"] + d["reparation"], 2)
    # Derniers mouvements
    recents = frappe.get_all("Mouvement Stock KYA",
        fields=["date_mouvement", "type_mouvement", "item_name", "magasin",
                "quantite", "etat", "reference_name"],
        order_by="creation desc", limit=15)
    # Répartition par type de mouvement (30 derniers jours)
    from frappe.utils import add_days
    depuis = add_days(today(), -30)
    par_type = frappe.db.sql("""
        SELECT type_mouvement, COUNT(*) AS n
        FROM `tabMouvement Stock KYA` WHERE date_mouvement >= %(d)s
        GROUP BY type_mouvement""", {"d": depuis}, as_dict=True)
    return {
        "kpi": {"articles": len(articles_set), "magasins": len(magasins_set),
                "unites": total_unites, "en_reparation": en_reparation, "ruptures": ruptures},
        "par_magasin": sorted(par_mag.values(), key=lambda x: x["magasin"]),
        "recents": recents, "par_type": par_type,
    }


@frappe.whitelist()
def importer_articles(rows):
    """Crée/Met à jour des Items depuis un import. `rows` = [{code, nom, groupe,
    uom}]. Retourne un compte-rendu. Réservé au magasin."""
    _guard(write=True)
    if isinstance(rows, str):
        rows = frappe.parse_json(rows)
    cree, maj, ignore, erreurs = 0, 0, 0, []
    for r in rows:
        code = (r.get("code") or "").strip()
        nom = (r.get("nom") or code).strip()
        if not code:
            ignore += 1
            continue
        try:
            groupe = _ensure_item_group(r.get("groupe"))
            uom = _ensure_uom(r.get("uom"))
            if frappe.db.exists("Item", code):
                it = frappe.get_doc("Item", code)
                it.item_name = nom or it.item_name
                it.item_group = groupe or it.item_group
                it.flags.ignore_permissions = True
                it.save()
                maj += 1
            else:
                it = frappe.new_doc("Item")
                it.item_code = code
                it.item_name = nom
                it.item_group = groupe
                it.stock_uom = uom
                it.is_stock_item = 1
                it.flags.ignore_permissions = True
                it.insert()
                cree += 1
        except Exception:
            erreurs.append(code)
            frappe.log_error(frappe.get_traceback(), "stock_kya.importer_articles")
    frappe.db.commit()
    return {"crees": cree, "maj": maj, "ignores": ignore,
            "erreurs": erreurs, "total": len(rows)}

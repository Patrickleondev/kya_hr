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
# Entrepôts « plomberie » ERPNext (créés d'office par société) : ce ne sont PAS
# des magasins KYA, on les masque du sélecteur pour ne pas perdre la magasinière.
_WH_NATIFS = {"Goods In Transit", "Work In Progress", "Finished Goods",
              "All Warehouses", "Stores"}


@frappe.whitelist()
def magasins():
    """Magasins KYA sélectionnables (exclut les entrepôts techniques ERPNext)."""
    _guard()
    rows = frappe.get_all("Warehouse", filters={"disabled": 0, "is_group": 0},
                          fields=["name", "warehouse_name"], order_by="name asc")
    reels = [w for w in rows if (w.get("warehouse_name") or "").strip() not in _WH_NATIFS]
    # Repli : sur un site sans magasin métier (ex. install neuve), on montre tout
    # plutôt qu'un sélecteur vide.
    return reels or rows


@frappe.whitelist()
def categories():
    """Liste des catégories d'article (pour les pickers de saisie)."""
    _guard()
    return frappe.get_all("Categorie Article KYA", order_by="categorie asc", pluck="name")


@frappe.whitelist()
def saisir_stock_direct(magasin, lignes, date_saisie=None):
    """Saisie directe depuis la page /stock-kya (onglet « Saisie directe »).

    Crée + valide UNE fiche « Saisie Stock KYA » (source unique de vérité,
    auditable, annulable) à partir des lignes saisies. `lignes` =
    [{designation, categorie, unite, bon_etat, en_reparation}]. Les catégories
    libres sont créées au besoin ; les articles manquants aussi (sans code)."""
    _guard(write=True)
    if isinstance(lignes, str):
        lignes = frappe.parse_json(lignes)
    if not magasin or not frappe.db.exists("Warehouse", magasin):
        frappe.throw(_("Choisissez un magasin valide."))
    doc = frappe.new_doc("Saisie Stock KYA")
    doc.magasin = magasin
    doc.date_saisie = date_saisie or today()
    for l in lignes or []:
        design = " ".join((l.get("designation") or "").split())
        if not design:
            continue
        cat = l.get("categorie")
        doc.append("lignes", {
            "designation": design,
            "categorie": _ensure_categorie(cat) if cat else None,
            "unite": l.get("unite") or "Unité",
            "bon_etat": flt(l.get("bon_etat")),
            "en_reparation": flt(l.get("en_reparation")),
        })
    if not doc.lignes:
        frappe.throw(_("Aucune ligne valide (désignation + quantité requises)."))
    doc.insert()
    doc.submit()
    frappe.db.commit()
    return {"name": doc.name, "lignes": len(doc.lignes), "magasin": magasin}


# ── Import d'articles (SANS code — modèle Article KYA maison) ────────────────
def _ensure_categorie(nom):
    """Garantit une Catégorie Article KYA et la retourne (défaut : « Non classé »)."""
    nom = (nom or "").strip() or "Non classé"
    if not frappe.db.exists("Categorie Article KYA", nom):
        try:
            c = frappe.new_doc("Categorie Article KYA")
            c.categorie = nom
            c.flags.ignore_permissions = True
            c.insert()
        except Exception:
            return "Non classé"
    return nom


_REF_IMPORT = "Import Stock Initial"


@frappe.whitelist()
def importer_stock_initial(rows):
    """Import « template » SANS code : crée les articles (par désignation) ET pose
    leur stock d'ouverture dans un magasin. `rows` = [{designation, categorie,
    unite, magasin, bon_etat, reparation}] (ou l'ancien {quantite, etat}). La
    désignation est la clé (jamais de code). Idempotent : ré-importer un
    (article, magasin) REMPLACE toute son ouverture (on ne cumule pas). Magasin."""
    _guard(write=True)
    if isinstance(rows, str):
        rows = frappe.parse_json(rows)
    from kya_hr.kya_hr.doctype.article_kya.article_kya import creer_ou_recuperer
    cree, lignes_stock, erreurs = 0, 0, []
    purges = set()
    for r in rows:
        design = " ".join((r.get("designation") or r.get("nom") or "").split())
        magasin = (r.get("magasin") or "").strip()
        if not design:
            continue
        try:
            cat = _ensure_categorie(r.get("categorie") or r.get("groupe"))
            existed = frappe.db.exists("Article KYA", {"designation": design})
            art = creer_ou_recuperer(
                design, cat, r.get("unite") or r.get("uom") or "Unité", r.get("type"))
            if not existed:
                cree += 1

            if magasin and frappe.db.exists("Warehouse", magasin):
                # Deux colonnes (bon état / réparation) comme la fiche d'inventaire,
                # sinon repli sur quantite + etat.
                if any(k in r for k in ("bon_etat", "reparation", "en_reparation")):
                    postes = [("Bon état", flt(r.get("bon_etat"))),
                              ("En réparation", flt(r.get("reparation") or r.get("en_reparation")))]
                else:
                    postes = [(_norm_etat(r.get("etat")), flt(r.get("quantite")))]
                # Idempotent : purge l'ouverture précédente de cet article/magasin.
                if (art, magasin) not in purges:
                    for nm in frappe.get_all("Mouvement Stock KYA",
                            filters={"reference_doctype": _REF_IMPORT,
                                     "reference_name": magasin, "item": art}, pluck="name"):
                        frappe.delete_doc("Mouvement Stock KYA", nm,
                                          ignore_permissions=True, force=True)
                    purges.add((art, magasin))
                for etat, q in postes:
                    if q:
                        enregistrer_mouvements(
                            [{"item": art, "magasin": magasin, "quantite": q, "etat": etat}],
                            "Inventaire", reference_doctype=_REF_IMPORT, reference_name=magasin)
                        lignes_stock += 1
        except Exception:
            erreurs.append(design)
            frappe.log_error(frappe.get_traceback(), "stock_kya.importer_stock_initial")
    frappe.db.commit()
    return {"articles_crees": cree, "lignes_stock": lignes_stock,
            "erreurs": erreurs, "total": len(rows)}


# ── Export « État d'inventaire » au format officiel KYA (AEA-ENG-13) ─────────
# Bloc des 3 signataires = les fonctions qui VALIDENT toujours (décision user).
# Les noms varient : le Responsable Stock les SAISIT au moment de l'export (champs
# accessibles), sinon on laisse vide → tout le monde signe/écrit à la main à
# l'impression. AUCUNE résolution auto (pas d'intervention requise).
_INV_SIGNATAIRES = [
    {"label": "CHARGÉ DES STOCKS"},
    {"label": "RESPONSABLE STOCK"},
    {"label": "CHEF D'ÉQUIPE ACHATS ET STOCKS"},
]


def _signataires_block(signataires):
    """Construit les 3 signataires à afficher. `signataires` (optionnel) = liste
    alignée sur _INV_SIGNATAIRES : [{nom, fonction}, ...]. Non fourni → vides
    (Fonction pré-remplie au libellé, éditable ; Nom vide, à écrire à la main)."""
    if isinstance(signataires, str):
        signataires = frappe.parse_json(signataires)
    out = []
    for i, spec in enumerate(_INV_SIGNATAIRES):
        s = (signataires[i] if signataires and i < len(signataires) else {}) or {}
        out.append({
            "label": spec["label"],
            "nom": (s.get("nom") or "").strip(),
            "fonction": (s.get("fonction") or "").strip(),
        })
    return out


def _logo_data_uri():
    """Logo KYA en data URI (base64) — wkhtmltopdf ne résout pas les URLs /assets."""
    import base64, os
    for rel in ("public/images/logo_kya.png", "public/images/kya_logo.png"):
        p = frappe.get_app_path("kya_hr", rel)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return ""


def _mag_label(name):
    """« Magasin KYA - D » → « MAGASIN KYA » ; « SOGBOSSITO - D » → « MAGASIN SOGBOSSITO »."""
    wn = frappe.db.get_value("Warehouse", name, "warehouse_name") or name
    wn = wn.strip().upper()
    return wn if wn.startswith("MAGASIN") else f"MAGASIN {wn}"


@frappe.whitelist()
def export_inventaire_xlsx(magasin=None, signataires=None):
    """Exporte l'état d'inventaire (temps réel) en Excel, au format de la fiche :
    titre, date, sections par magasin (N°/Désignation/Total/Bon état/Réparation),
    puis le bloc des 3 signataires (noms/fonctions saisis par le Resp. Stock)."""
    _guard()
    import base64
    from frappe.utils.xlsxutils import make_xlsx
    inv = etat_inventaire(magasin)
    data = [["ETAT D'INVENTAIRE DE STOCK"],
            ["DATE : " + frappe.utils.formatdate(today(), "dd/MM/yyyy")],
            []]
    for s in inv["sections"]:
        data.append([_mag_label(s["magasin"])])
        data.append(["N°", "DESIGNATION", "TOTAL", "BON ETAT", "EN REPARAT°"])
        for l in s["lignes"]:
            data.append([l["n"], l["designation"], l["qte_totale"],
                         l["bon_etat"], l["reparation"]])
        data.append([])
    # Bloc signataires (fonctions fixes ; noms/fonctions saisis par le Resp. Stock)
    sign = _signataires_block(signataires)
    data.append([])
    data.append([""] + [s["label"] for s in sign])
    data.append(["Nom"] + [s["nom"] for s in sign])
    data.append(["Fonction"] + [s["fonction"] for s in sign])
    data.append(["Date"] + [frappe.utils.formatdate(today(), "dd/MM/yyyy") for _ in sign])
    data.append(["SIGNATURE", "", "", ""])
    xlsx = make_xlsx(data, "Inventaire")
    return {"filename": "etat-inventaire-kya-{0}.xlsx".format(today()),
            "content_base64": base64.b64encode(xlsx.getvalue()).decode("ascii"),
            "rows": sum(len(s["lignes"]) for s in inv["sections"])}


@frappe.whitelist()
def export_inventaire_pdf(magasin=None, signataires=None):
    """Exporte l'état d'inventaire en PDF fidèle à la fiche KYA (AEA-ENG-13) :
    logo + bandeau orange, date, sections par magasin, bloc 3 signataires
    (noms/fonctions saisis par le Resp. Stock, sinon vides à signer à la main)."""
    _guard()
    import base64
    from frappe.utils.pdf import get_pdf
    inv = etat_inventaire(magasin)
    date_fr = frappe.utils.formatdate(today(), "dd/MM/yyyy")

    sections_html = ""
    for s in inv["sections"]:
        lignes = "".join(
            f"<tr><td class='n'>{l['n']}</td><td class='d'>{frappe.utils.escape_html(l['designation'])}</td>"
            f"<td class='q'>{_fmt(l['qte_totale'])}</td><td class='q'>{_fmt(l['bon_etat'])}</td>"
            f"<td class='q'>{_fmt(l['reparation'])}</td></tr>"
            for l in s["lignes"])
        sections_html += (
            f"<tr class='mag'><td colspan='5'>{_mag_label(s['magasin'])}</td></tr>{lignes}")
    if not sections_html:
        sections_html = "<tr><td colspan='5' style='text-align:center;padding:14px'>Aucun stock.</td></tr>"

    sign = _signataires_block(signataires)
    sig_cells = "".join(f"<th>{s['label']}</th>" for s in sign)
    sig_nom = "".join(f"<td>{frappe.utils.escape_html(s['nom'])}</td>" for s in sign)
    sig_fct = "".join(f"<td>{frappe.utils.escape_html(s['fonction'])}</td>" for s in sign)
    sig_date = "".join(f"<td>{date_fr}</td>" for _ in sign)

    logo = _logo_data_uri()
    logo_img = f"<img src='{logo}'>" if logo else "&nbsp;"

    html = f"""<html><head><meta charset='utf-8'><style>
      * {{ font-family: 'DejaVu Sans Mono','Courier New',monospace; }}
      .hdr {{ width:100%; border-collapse:collapse; margin-bottom:6px; }}
      .hdr td {{ border:1px solid #000; vertical-align:middle; }}
      .logo {{ width:150px; text-align:center; padding:6px; }}
      .logo img {{ max-width:120px; }}
      .band {{ background:#F4A83B; text-align:center; font-weight:bold;
               font-size:15px; letter-spacing:1px; }}
      .date {{ font-weight:bold; font-size:13px; margin:6px 0 8px; }}
      table.inv {{ width:100%; border-collapse:collapse; font-size:11px; }}
      table.inv th, table.inv td {{ border:1px solid #000; padding:2px 5px; }}
      table.inv th {{ text-align:center; font-weight:bold; }}
      td.n {{ text-align:center; width:5%; }} td.d {{ width:60%; }}
      td.q {{ text-align:right; font-weight:bold; width:11%; }}
      tr.mag td {{ text-align:center; font-weight:bold; background:#eee; }}
      table.sig {{ width:100%; border-collapse:collapse; margin-top:26px; font-size:11px; }}
      table.sig th, table.sig td {{ border:1px solid #000; padding:5px; text-align:center; }}
      table.sig th {{ background:#ccc; }}
      table.sig td.lbl {{ background:#f2f2f2; font-weight:bold; text-align:left; width:14%; }}
      .sigrow td {{ height:34px; }}
    </style></head><body>
      <table class='hdr'><tr>
        <td class='logo'>{logo_img}</td>
        <td class='band'>ETAT D'INVENTAIRE DE STOCK</td>
      </tr></table>
      <div class='date'>DATE : {date_fr}</div>
      <table class='inv'>
        <thead><tr><th rowspan='2'>N°</th><th rowspan='2'>DESIGNATION</th>
          <th colspan='3'>QUANTITE</th></tr>
          <tr><th>TOTAL</th><th>BON ETAT</th><th>EN REPARAT°</th></tr></thead>
        <tbody>{sections_html}</tbody>
      </table>
      <table class='sig'>
        <tr><th class='lbl'></th>{sig_cells}</tr>
        <tr><td class='lbl'>Nom</td>{sig_nom}</tr>
        <tr><td class='lbl'>Fonction</td>{sig_fct}</tr>
        <tr><td class='lbl'>Date</td>{sig_date}</tr>
        <tr class='sigrow'><td class='lbl'>SIGNATURE</td><td></td><td></td><td></td></tr>
      </table>
    </body></html>"""
    pdf = get_pdf(html)
    return {"filename": "etat-inventaire-kya-{0}.pdf".format(today()),
            "content_base64": base64.b64encode(pdf).decode("ascii")}


def _fmt(v):
    v = flt(v)
    return str(int(v)) if v == int(v) else str(v)


@frappe.whitelist()
def modele_import_xlsx():
    """Modèle d'import SANS code, calqué sur la fiche d'inventaire :
    designation, categorie, unite, magasin, bon_etat, en_reparation."""
    _guard()
    import base64
    from frappe.utils.xlsxutils import make_xlsx
    mag = frappe.db.get_value("Warehouse", {"is_group": 0, "disabled": 0}, "name") or ""
    headers = ["designation", "categorie", "unite", "magasin", "bon_etat", "en_reparation"]
    ex1 = ["MODULE PV 455Wc", "Modules PV", "Unité", mag, 12, 0]
    ex2 = ["BALAIS TELESCOPIQUE", "Outillage", "Unité", mag, 2, 3]
    ex3 = ["CABLE 1X25mm² (m)", "Câbles", "m", mag, 6376, 0]
    xlsx = make_xlsx([headers, ex1, ex2, ex3], "Modele import")
    return {"filename": "modele-import-stock-kya.xlsx",
            "content_base64": base64.b64encode(xlsx.getvalue()).decode("ascii")}


# États possibles d'un article en stock (une seule dimension « état »).
_ETATS = {
    "bon etat": "Bon état", "bon état": "Bon état", "bon": "Bon état", "": "Bon état",
    "neuf": "Neuf", "nouveau": "Neuf",
    "en reparation": "En réparation", "en réparation": "En réparation",
    "reparation": "En réparation", "réparation": "En réparation", "repar": "En réparation",
    "hors service": "Hors service", "hs": "Hors service", "hors-service": "Hors service",
}


def _norm_etat(v):
    """Normalise le libellé d'état vers une valeur canonique (défaut : Bon état)."""
    return _ETATS.get((v or "").strip().lower(), "Bon état")


def _map_import_row(d):
    """Normalise une ligne d'import (dict en-tête→valeur) vers le format SANS code.

    Format calqué sur la fiche d'inventaire :
    designation, categorie, unite, magasin, bon_etat, en_reparation.
    (Repli accepté : une colonne quantite + etat.)
    """
    g = lambda *keys: next((str(d[k]).strip() for k in keys
                            if k in d and d[k] not in (None, "")), "")
    row = {
        "designation": g("designation", "désignation", "nom", "nom de l'article",
                         "article", "libelle", "libellé"),
        "categorie": g("categorie", "catégorie", "groupe", "groupe d'article",
                       "groupe d'articles", "famille"),
        "unite": g("unite", "unité", "udm", "uom", "unité de mesure", "u.d.m"),
        "magasin": g("magasin", "entrepot", "entrepôt", "warehouse", "stock"),
    }
    bon = g("bon_etat", "bon état", "bon etat", "bonetat")
    rep = g("en_reparation", "reparation", "réparation", "en réparation",
            "en reparation", "repar")
    if bon or rep:
        row["bon_etat"] = flt(bon)
        row["en_reparation"] = flt(rep)
    else:
        row["quantite"] = flt(g("quantite", "quantité", "qte", "quantity", "qté", "total"))
        row["etat"] = _norm_etat(g("etat", "état", "condition"))
    return row


@frappe.whitelist()
def importer_stock_fichier(content_base64, filename=None):
    """Import d'articles depuis un fichier **Excel (.xlsx)** ou CSV téléversé.
    On travaille sur Excel ici : on lit directement le classeur rempli."""
    _guard(write=True)
    import base64
    import io
    raw = base64.b64decode(content_base64)
    rows = []
    name = (filename or "").lower()
    is_xlsx = name.endswith(".xlsx") or raw[:2] == b"PK"
    if is_xlsx:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
        ws = wb.active
        header = None
        for r in ws.iter_rows(values_only=True):
            if header is None:
                header = [str(c).strip().lower() if c is not None else "" for c in r]
                continue
            d = {header[i]: r[i] for i in range(min(len(header), len(r)))}
            row = _map_import_row(d)
            if row["designation"]:
                rows.append(row)
    else:
        import csv
        txt = raw.decode("utf-8-sig", errors="replace")
        sample = txt.splitlines()[0] if txt.splitlines() else ""
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        for d in csv.DictReader(io.StringIO(txt), delimiter=delim):
            d = {(k or "").strip().lower(): v for k, v in d.items()}
            row = _map_import_row(d)
            if row["designation"]:
                rows.append(row)
    if not rows:
        frappe.throw(_("Aucune ligne valide trouvée (vérifiez l'en-tête : designation, categorie, unite, magasin, bon_etat, en_reparation)."))
    return importer_stock_initial(rows)


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
    """Crée des Articles KYA (catalogue seul, sans stock) depuis un import.
    `rows` = [{designation, categorie, unite}]. SANS code. Réservé au magasin."""
    _guard(write=True)
    if isinstance(rows, str):
        rows = frappe.parse_json(rows)
    from kya_hr.kya_hr.doctype.article_kya.article_kya import creer_ou_recuperer
    cree, ignore, erreurs = 0, 0, []
    for r in rows:
        design = " ".join((r.get("designation") or r.get("nom") or "").split())
        if not design:
            ignore += 1
            continue
        try:
            existed = frappe.db.exists("Article KYA", {"designation": design})
            creer_ou_recuperer(
                design, _ensure_categorie(r.get("categorie") or r.get("groupe")),
                r.get("unite") or r.get("uom") or "Unité")
            if not existed:
                cree += 1
        except Exception:
            erreurs.append(design)
            frappe.log_error(frappe.get_traceback(), "stock_kya.importer_articles")
    frappe.db.commit()
    return {"crees": cree, "ignores": ignore, "erreurs": erreurs, "total": len(rows)}

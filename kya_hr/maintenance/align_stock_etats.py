"""Aligne le stock KYA sur le vocabulaire d'état UNIQUE : Bon état / À réparer /
Défectueux (décision magasin, remplace Neuf / En réparation / Hors service /
Endommagé).

POURQUOI un script : les child doctypes PV Entree Materiel Item, Inventaire KYA
Item et Retour Materiel KYA Item sont `custom: 1` → Frappe NE resynchronise PAS
leur JSON au migrate (cf. ensure_webform_table_columns). On applique donc les
changements de schéma directement en base (ajout de champ / options), puis on
reclasse les mouvements existants. 100 % idempotent, aucune perte de données.

Branché dans safe_migrations (avant ensure_webform_table_columns, qui règle
ensuite la largeur des colonnes des nouveaux champs).
"""
from __future__ import annotations

import frappe

# Reclassement des libellés hérités du grand livre vers le vocabulaire unique.
_MOUV_RELABEL = [
    ("Neuf", "Bon état"),
    ("En réparation", "À réparer"),
    ("Hors service", "Défectueux"),
    ("Endommagé", "Défectueux"),
]
_OPTS_3 = "Bon état\nÀ réparer\nDéfectueux"


def _field(dt, fieldname):
    for f in frappe.get_doc("DocType", dt).fields:
        if f.fieldname == fieldname:
            return f
    return None


def _has_field(dt, fieldname):
    return bool(frappe.db.exists("DocField", {"parent": dt, "fieldname": fieldname}))


def _save_doctype(doc):
    """Sauvegarde un DocType custom (crée/retire les colonnes en base)."""
    doc.flags.ignore_permissions = True
    doc.flags.ignore_version = True
    doc.save()


def _add_field_after(dt, anchor, spec, out):
    """Insère un DocField natif juste après `anchor` sur un doctype custom."""
    if not frappe.db.exists("DocType", dt):
        out["absents"].append(dt)
        return
    if _has_field(dt, spec["fieldname"]):
        return
    doc = frappe.get_doc("DocType", dt)
    newf = doc.append("fields", spec)
    # Repositionner juste après l'ancre (sinon ajouté en fin de grille).
    try:
        doc.fields.remove(newf)
        pos = next((i for i, f in enumerate(doc.fields) if f.fieldname == anchor),
                   len(doc.fields) - 1) + 1
        doc.fields.insert(pos, newf)
        for i, f in enumerate(doc.fields):
            f.idx = i + 1
    except Exception:
        doc.fields.append(newf)
    _save_doctype(doc)
    out["champs_ajoutes"].append("%s.%s" % (dt, spec["fieldname"]))


def _set_field(dt, fieldname, **attrs):
    """Met à jour options/label/description d'un champ existant (doctype custom)."""
    if not frappe.db.exists("DocType", dt) or not _has_field(dt, fieldname):
        return False
    doc = frappe.get_doc("DocType", dt)
    changed = False
    for f in doc.fields:
        if f.fieldname == fieldname:
            for k, v in attrs.items():
                if (f.get(k) or "") != v:
                    f.set(k, v)
                    changed = True
    if changed:
        _save_doctype(doc)
    return changed


def execute() -> dict:
    out = {"champs_ajoutes": [], "options_maj": [], "mouvements_reclasses": {},
           "absents": []}

    # 1) PV Entrée : capter l'état à la réception (le posting le lit déjà).
    _add_field_after("PV Entree Materiel Item", "qte_recue", {
        "fieldname": "etat", "label": "État à la réception", "fieldtype": "Select",
        "options": _OPTS_3, "default": "Bon état", "in_list_view": 1, "columns": 1,
        "description": ("Bon état → stock disponible. À réparer / Défectueux → "
                        "reçu mais non disponible (le matériel reste enregistré)."),
    }, out)

    # 2) Inventaire : compter aussi le défectueux.
    _add_field_after("Inventaire KYA Item", "qte_en_reparation", {
        "fieldname": "qte_defectueux", "label": "Défectueux", "fieldtype": "Float",
        "default": "0", "in_list_view": 1, "columns": 1,
    }, out)
    if _set_field("Inventaire KYA Item", "qte_en_reparation", label="À réparer"):
        out["options_maj"].append("Inventaire KYA Item.qte_en_reparation (label)")

    # 3) Retour : options d'état alignées (Bon état / À réparer / Défectueux).
    if _set_field("Retour Materiel KYA Item", "etat_au_retour", options=_OPTS_3,
                  description=("Bon état → stock disponible. À réparer → immobilisé "
                               "(récupérable). Défectueux → hors stock utile "
                               "(à retourner/rebut).")):
        out["options_maj"].append("Retour Materiel KYA Item.etat_au_retour (options)")

    # 4) Grand livre : options canoniques (custom=0, migrate le fait aussi ; défensif).
    if _set_field("Mouvement Stock KYA", "etat", options=_OPTS_3):
        out["options_maj"].append("Mouvement Stock KYA.etat (options)")

    # 5) Reclasser les mouvements existants (aucune perte : simple relabel).
    for old, new in _MOUV_RELABEL:
        n = frappe.db.count("Mouvement Stock KYA", {"etat": old})
        if n:
            frappe.db.sql(
                "UPDATE `tabMouvement Stock KYA` SET etat=%s WHERE etat=%s",
                (new, old))
            out["mouvements_reclasses"]["%s→%s" % (old, new)] = n

    frappe.db.commit()
    frappe.clear_cache()
    print("[align_stock_etats] champs+=%s options=%s reclasses=%s" % (
        out["champs_ajoutes"], out["options_maj"], out["mouvements_reclasses"]))
    return out

# -*- coding: utf-8 -*-
"""Import/Export CSV maison pour la Comptabilité KYA (comme pour le stock).

Deux jeux d'endpoints, réservés Comptabilité/Direction :

1. Grand Livre — écritures comptables (typiquement un export Sage 100) :
   - download_template_ecritures() : CSV vide (entêtes FR) + 2 lignes exemple
   - import_ecritures(content_base64, submit) : crée des « Ecriture Comptable KYA »

2. Paie — bulletins :
   - download_template_bulletins() : CSV modèle (matricule, mois, salaire, primes)
   - import_bulletins(content_base64, submit) : crée des « Bulletin Paie KYA »
     (le moteur compute_bulletin recalcule CNSS/IRPP/net depuis Parametres Paie KYA)

Le format CSV colle aux libellés métier FR pour que le Comptable remplisse le
modèle téléchargé sans mapping. Séparateur « ; » toléré comme « , » (Excel FR).
"""
from __future__ import annotations

import base64
import csv
import io

import frappe
from frappe.utils import cstr, flt, getdate

IMPORT_ROLES = {
    "Comptable", "Accounts Manager", "DFC", "Responsable Comptable",
    "Directeur Général", "DGA", "System Manager",
}

# ── Grand Livre ──────────────────────────────────────────────────────
ECR_HEADERS = ["Date", "Journal", "N° pièce", "Compte", "Libellé du compte",
               "Libellé", "Débit", "Crédit", "Lettrage"]
ECR_EXAMPLE = [
    ["01/03/2026", "AC", "AC-001", "401100", "Fournisseurs",
     "Achat panneaux solaires", "1500000", "0", ""],
    ["05/03/2026", "BQ", "BQ-014", "521000", "Banque",
     "Règlement fournisseur", "0", "1500000", "A"],
]

# ── Paie ─────────────────────────────────────────────────────────────
BP_HEADERS = ["Matricule ou email", "Année", "Mois", "Personnes à charge",
              "Salaire de base", "Primes (libellé:montant|libellé:montant)"]
BP_EXAMPLE = [
    ["HR-EMP-00001", "2026", "Mars", "2", "300000",
     "Prime de responsabilité:50000|Prime de transport:25000"],
    ["agent@kya-energy.com", "2026", "Mars", "0", "180000", ""],
]


def _check_role(action="import"):
    if not (set(frappe.get_roles(frappe.session.user)) & IMPORT_ROLES):
        frappe.throw(f"Accès réservé à la Comptabilité pour {action}.",
                     frappe.PermissionError)


def _csv_b64(headers, rows):
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    for r in rows:
        writer.writerow(r)
    txt = out.getvalue()
    return base64.b64encode(txt.encode("utf-8")).decode("ascii"), len(txt)


def _read_rows(content_base64):
    raw = base64.b64decode(content_base64).decode("utf-8-sig", errors="replace")
    # Détection séparateur : « ; » (Excel FR) sinon « , »
    first = raw.splitlines()[0] if raw.strip() else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    return list(csv.DictReader(io.StringIO(raw), delimiter=delim))


def _col(row, *keys):
    """Lit une colonne par plusieurs libellés possibles (insensible casse/espaces)."""
    norm = {cstr(k).strip().lower(): v for k, v in row.items()}
    for k in keys:
        v = norm.get(k.strip().lower())
        if v not in (None, ""):
            return cstr(v).strip()
    return ""


def _parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            import datetime
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return getdate(s)
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════
#  Grand Livre
# ════════════════════════════════════════════════════════════════════
@frappe.whitelist(allow_guest=False)
def download_template_ecritures() -> dict:
    _check_role("télécharger le modèle")
    b64, size = _csv_b64(ECR_HEADERS, ECR_EXAMPLE)
    return {"filename": "modele-grand-livre-kya.csv", "content_base64": b64, "size": size}


@frappe.whitelist(allow_guest=False)
def import_ecritures(content_base64: str, submit: int = 0) -> dict:
    """Crée des Ecriture Comptable KYA depuis un CSV. `submit=1` les valide."""
    _check_role("importer des écritures")
    submit = int(submit or 0)
    rows = _read_rows(content_base64)
    res = {"total": len(rows), "crees": 0, "valides": 0, "ignores": 0, "erreurs": []}

    for i, row in enumerate(rows, start=2):
        date = _parse_date(_col(row, "Date", "date_ecriture"))
        compte = _col(row, "Compte", "compte_numero")
        libelle = _col(row, "Libellé", "Libelle", "libelle")
        journal = _col(row, "Journal", "journal")
        if not (date and compte and journal and libelle):
            res["ignores"] += 1
            if any(_col(row, h) for h in ECR_HEADERS):  # ligne non vide → signaler
                res["erreurs"].append(f"L.{i}: Date/Journal/Compte/Libellé requis")
            continue
        try:
            doc = frappe.new_doc("Ecriture Comptable KYA")
            doc.date_ecriture = date
            doc.journal = journal
            doc.numero_piece = _col(row, "N° pièce", "N pièce", "numero_piece", "piece")
            doc.compte_numero = compte
            doc.compte_libelle = _col(row, "Libellé du compte", "compte_libelle")
            doc.libelle = libelle
            doc.debit = flt(_col(row, "Débit", "Debit", "debit").replace(" ", "").replace(",", "."))
            doc.credit = flt(_col(row, "Crédit", "Credit", "credit").replace(" ", "").replace(",", "."))
            doc.lettrage = _col(row, "Lettrage", "lettrage")
            doc.insert(ignore_permissions=True)
            res["crees"] += 1
            if submit:
                doc.submit()
                res["valides"] += 1
        except Exception as e:
            res["erreurs"].append(f"L.{i}: {cstr(e)[:120]}")

    frappe.db.commit()
    return res


# ════════════════════════════════════════════════════════════════════
#  Paie / Bulletins
# ════════════════════════════════════════════════════════════════════
@frappe.whitelist(allow_guest=False)
def download_template_bulletins() -> dict:
    _check_role("télécharger le modèle")
    b64, size = _csv_b64(BP_HEADERS, BP_EXAMPLE)
    return {"filename": "modele-bulletins-paie-kya.csv", "content_base64": b64, "size": size}


def _resolve_employee(ref):
    """Résout un Employee depuis un matricule (name) ou un email (user_id)."""
    ref = (ref or "").strip()
    if not ref:
        return None
    if frappe.db.exists("Employee", ref):
        return ref
    emp = frappe.db.get_value("Employee", {"user_id": ref}, "name")
    if emp:
        return emp
    emp = frappe.db.get_value("Employee", {"personal_email": ref}, "name")
    return emp


def _parse_primes(s):
    """« libellé:montant;libellé:montant » → [ {libelle, montant, imposable, soumis_cnss} ].
    Les flags imposable/CNSS viennent du catalogue Parametres Paie KYA si connus,
    sinon défaut imposable+CNSS."""
    out = []
    if not s:
        return out
    catalogue = {}
    try:
        cfg = frappe.get_single("Parametres Paie KYA")
        for p in (cfg.get("primes") or []):
            catalogue[cstr(p.get("libelle")).strip().lower()] = (
                1 if p.get("imposable") else 0, 1 if p.get("soumis_cnss") else 0)
    except Exception:
        pass
    for part in s.replace("|", ";").split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        lib, _, mnt = part.partition(":")
        lib = lib.strip()
        imp, cnss = catalogue.get(lib.lower(), (1, 1))
        out.append({"libelle": lib,
                    "montant": flt(mnt.replace(" ", "").replace(",", ".")),
                    "imposable": imp, "soumis_cnss": cnss})
    return out


@frappe.whitelist(allow_guest=False)
def import_bulletins(content_base64: str, submit: int = 0) -> dict:
    """Crée des Bulletin Paie KYA depuis un CSV. Le moteur recalcule tout."""
    _check_role("importer des bulletins")
    submit = int(submit or 0)
    rows = _read_rows(content_base64)
    res = {"total": len(rows), "crees": 0, "valides": 0, "ignores": 0, "erreurs": []}

    for i, row in enumerate(rows, start=2):
        ref = _col(row, "Matricule ou email", "Matricule", "employee", "matricule", "email")
        mois = _col(row, "Mois", "mois")
        annee = _col(row, "Année", "Annee", "annee")
        base = _col(row, "Salaire de base", "salaire_base")
        if not (ref and mois and annee):
            res["ignores"] += 1
            if any(_col(row, h) for h in BP_HEADERS):
                res["erreurs"].append(f"L.{i}: Matricule/Mois/Année requis")
            continue
        emp = _resolve_employee(ref)
        if not emp:
            res["erreurs"].append(f"L.{i}: employé introuvable ({ref})")
            continue
        try:
            doc = frappe.new_doc("Bulletin Paie KYA")
            doc.employee = emp
            doc.annee = int(flt(annee))
            doc.mois = mois.strip().capitalize()
            doc.nb_charges = int(flt(_col(row, "Personnes à charge", "nb_charges") or 0))
            doc.salaire_base = flt(base.replace(" ", "").replace(",", "."))
            for p in _parse_primes(_col(row, "Primes (libellé:montant|libellé:montant)",
                                        "Primes (libellé:montant;libellé:montant)",
                                        "Primes", "primes")):
                doc.append("primes", p)
            doc.insert(ignore_permissions=True)
            res["crees"] += 1
            if submit:
                doc.submit()
                res["valides"] += 1
        except Exception as e:
            res["erreurs"].append(f"L.{i}: {cstr(e)[:120]}")

    frappe.db.commit()
    return res

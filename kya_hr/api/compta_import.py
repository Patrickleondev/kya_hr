# -*- coding: utf-8 -*-
"""Import/Export Excel maison pour la Comptabilité KYA (comme pour le stock).

Deux jeux d'endpoints, réservés Comptabilité/Direction :

1. Grand Livre — écritures comptables (typiquement un export Sage 100) :
   - download_template_ecritures() : classeur Excel (.xlsx) modèle + 2 lignes exemple
   - import_ecritures(content_base64, submit) : crée des « Ecriture Comptable KYA »

2. Paie — bulletins :
   - download_template_bulletins() : classeur Excel modèle (matricule, mois, salaire, primes)
   - import_bulletins(content_base64, submit) : crée des « Bulletin Paie KYA »
     (le moteur compute_bulletin recalcule CNSS/IRPP/net depuis Parametres Paie KYA)

Les modèles sont fournis en **Excel (.xlsx)** ; à la lecture on accepte aussi un
CSV (Excel-FR séparateur « ; » ou « , ») par tolérance. Les entêtes collent aux
libellés métier FR pour que le Comptable remplisse le modèle sans mapping.
"""
from __future__ import annotations

import base64
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
     "Achat panneaux solaires", 1500000, 0, ""],
    ["05/03/2026", "BQ", "BQ-014", "521000", "Banque",
     "Règlement fournisseur", 0, 1500000, "A"],
]

# ── Paie ─────────────────────────────────────────────────────────────
BP_HEADERS = ["Matricule ou email", "Année", "Mois", "Personnes à charge",
              "Salaire de base", "Primes (libellé:montant|libellé:montant)"]
BP_EXAMPLE = [
    ["HR-EMP-00001", 2026, "Mars", 2, 300000,
     "Prime de responsabilité:50000|Prime de transport:25000"],
    ["agent@kya-energy.com", 2026, "Mars", 0, 180000, ""],
]


def _check_role(action="import"):
    if not (set(frappe.get_roles(frappe.session.user)) & IMPORT_ROLES):
        frappe.throw(f"Accès réservé à la Comptabilité pour {action}.",
                     frappe.PermissionError)


def _xlsx_b64(headers, rows, sheet):
    """Construit un classeur Excel (entêtes + lignes) → base64."""
    from frappe.utils.xlsxutils import make_xlsx
    data = [headers] + [list(r) for r in rows]
    xlsx = make_xlsx(data, sheet)
    return base64.b64encode(xlsx.getvalue()).decode("ascii"), len(xlsx.getvalue())


def _read_rows(content_base64):
    """Lit un fichier téléversé (Excel .xlsx OU CSV) → liste de dicts (entête→valeur).

    Excel détecté par la signature ZIP « PK » ; sinon CSV (séparateur ; ou ,)."""
    raw = base64.b64decode(content_base64)
    if raw[:2] == b"PK":  # .xlsx (archive ZIP)
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
        ws = wb.active
        header = None
        out = []
        for r in ws.iter_rows(values_only=True):
            if header is None:
                if r is None or all(c is None for c in r):
                    continue
                header = [cstr(c).strip() if c is not None else "" for c in r]
                continue
            if r is None or all(c is None for c in r):
                continue
            out.append({header[i]: r[i] for i in range(min(len(header), len(r)))})
        return out
    # CSV fallback
    import csv
    txt = raw.decode("utf-8-sig", errors="replace")
    first = txt.splitlines()[0] if txt.strip() else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    return list(csv.DictReader(io.StringIO(txt), delimiter=delim))


def _col(row, *keys):
    """Lit une colonne par plusieurs libellés possibles (insensible casse/espaces)."""
    norm = {cstr(k).strip().lower(): v for k, v in row.items()}
    for k in keys:
        v = norm.get(k.strip().lower())
        if v not in (None, ""):
            return cstr(v).strip()
    return ""


def _num(s):
    return flt(cstr(s).replace(" ", "").replace(" ", "").replace(",", "."))


def _parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    # openpyxl peut renvoyer un datetime déjà formaté « 2026-03-01 00:00:00 »
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y",
                "%Y-%m-%d %H:%M:%S"):
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
    b64, size = _xlsx_b64(ECR_HEADERS, ECR_EXAMPLE, "Grand Livre")
    return {"filename": "modele-grand-livre-kya.xlsx", "content_base64": b64, "size": size}


@frappe.whitelist(allow_guest=False)
def import_ecritures(content_base64: str, submit: int = 0) -> dict:
    """Crée des Ecriture Comptable KYA depuis un Excel/CSV. `submit=1` les valide."""
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
            if any(_col(row, h) for h in ECR_HEADERS):
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
            doc.debit = _num(_col(row, "Débit", "Debit", "debit"))
            doc.credit = _num(_col(row, "Crédit", "Credit", "credit"))
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
    b64, size = _xlsx_b64(BP_HEADERS, BP_EXAMPLE, "Bulletins")
    return {"filename": "modele-bulletins-paie-kya.xlsx", "content_base64": b64, "size": size}


_MOIS_CANON = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
               "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _norm_mois(s):
    """Ramène un mois saisi (avec/sans accent, casse libre, n° 1-12) vers l'une
    des options exactes du champ Select. Ex. 'aout'→'Août', '03'→'Mars'."""
    import unicodedata
    s = cstr(s).strip()
    if not s:
        return s
    if s.isdigit():
        n = int(s)
        return _MOIS_CANON[n - 1] if 1 <= n <= 12 else s

    def _strip(x):
        return "".join(c for c in unicodedata.normalize("NFD", x.lower())
                       if unicodedata.category(c) != "Mn")
    cible = _strip(s)
    for m in _MOIS_CANON:
        if _strip(m) == cible:
            return m
    return s.capitalize()


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
    return frappe.db.get_value("Employee", {"personal_email": ref}, "name")


def _parse_primes(s):
    """« libellé:montant|libellé:montant » → lignes de prime. Les flags
    imposable/CNSS viennent du catalogue Parametres Paie KYA si connus,
    sinon défaut imposable + soumis CNSS."""
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
    for part in cstr(s).replace(";", "|").split("|"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        lib, _, mnt = part.partition(":")
        lib = lib.strip()
        imp, cnss = catalogue.get(lib.lower(), (1, 1))
        out.append({"libelle": lib, "montant": _num(mnt),
                    "imposable": imp, "soumis_cnss": cnss})
    return out


@frappe.whitelist(allow_guest=False)
def import_bulletins(content_base64: str, submit: int = 0) -> dict:
    """Crée des Bulletin Paie KYA depuis un Excel/CSV. Le moteur recalcule tout."""
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
            doc.mois = _norm_mois(mois)
            doc.nb_charges = int(_num(_col(row, "Personnes à charge", "nb_charges") or 0))
            doc.salaire_base = _num(base)
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

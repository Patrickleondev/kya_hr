"""Resynchronise les compteurs `tabSeries` avec le maximum réel des documents.

Bug corrigé : après import/migration, le compteur d'une série de nommage
(ex. « HR-EMP- » pour Employee) peut être EN RETARD par rapport au plus grand
ID existant. Le prochain enregistrement réutilise alors un ID déjà pris →
« Duplicate name » / ID employé en double.

Principe : pour chaque préfixe de série numérique d'un doctype, calculer le plus
grand suffixe existant et remonter `tabSeries.current` à cette valeur (jamais
vers le bas — on ne fait que combler le retard). Idempotent, `dry_run` dispo,
câblé AFTER_MIGRATE pour auto-réparation à chaque déploiement.
"""
from __future__ import annotations

import re

import frappe
from frappe.utils import cint


# Doctypes dont le compteur doit rester synchronisé (étendre au besoin).
# Couvre aussi bien le style `naming_series:` (menu déroulant) que
# `autoname: format:PREFIXE-{...}-{#####}` (la majorité des doctypes KYA) —
# la détection des préfixes est désormais EMPIRIQUE (cf. _series_prefixes),
# donc peu importe le mécanisme de nommage réel du doctype.
DEFAULT_DOCTYPES = [
    "Employee",
    "Demande Achat KYA", "Bon Commande KYA", "Appel Offre KYA",
    "Brouillard Caisse", "Etat Recap Cheques",
    "PV Entree Materiel", "PV Sortie Materiel", "Retour Materiel KYA",
    "Inventaire KYA", "Sortie Vehicule",
    # autoname format: — mêmes symptômes possibles (doublon de nom au
    # premier insert après un import massif/backfill qui laisse le
    # compteur en retard sur le max réel).
    "Article KYA", "Avenant Contrat KYA", "Besoin de Formation",
    "Contrat Stage Immersion KYA", "Demande Conge Stagiaire",
    "Document RH KYA", "Document Vehicule", "Entretien Vehicule KYA",
    "Evolution Carriere KYA", "Fiche de Poste KYA", "KYA Compta Import",
    "KYA Contrat", "KYA Import RH", "KYA Reunion Sync Log",
    "KYA SoP Client", "Marche KYA", "Modification Info Employe KYA",
    "Mouvement Stock KYA", "Plan de Formation", "Plein Carburant KYA",
    "Prestataire KYA", "Saisie Stock KYA", "Solde Tout Compte KYA",
    "Stagiaire RH KYA",
]


def _series_prefixes(doctype: str) -> set[str]:
    """Préfixes REELS détectés empiriquement dans les noms déjà en base.

    Ancienne version : ne lisait que les options du champ `naming_series`
    (menu déroulant) — ratait tous les doctypes en `autoname: format:...`
    (ex. Evolution Carriere KYA -> "EVOL-{#####}"), qui n'ont PAS de champ
    naming_series du tout. Preuve du bug : duplicate 'EVOL-00171' en prod
    (30/07) alors que ce script tournait déjà à chaque migrate, silencieux
    car ce doctype n'était même pas dans DEFAULT_DOCTYPES ET la détection
    par naming_series n'aurait de toute façon rien trouvé.

    Approche empirique : on regarde les noms réellement stockés (ex.
    "AVN-2026-00042") et on extrait tout ce qui précède le suffixe
    numérique final comme préfixe ("AVN-2026-"). Fonctionne pour
    naming_series ET format:, y compris les formats avec {YYYY} (chaque
    année produit naturellement son propre préfixe/série)."""
    prefixes: set[str] = set()
    try:
        names = frappe.db.sql_list(f"SELECT name FROM `tab{doctype}`")
    except Exception:
        return prefixes
    for n in names or []:
        m = re.match(r"^(.*?)(\d+)$", n or "")
        if m and m.group(1):
            prefixes.add(m.group(1))
    return prefixes


def _max_numeric_suffix(doctype: str, prefix: str) -> int | None:
    """Plus grand suffixe purement numérique des noms commençant par `prefix`."""
    try:
        names = frappe.db.sql_list(
            f"SELECT name FROM `tab{doctype}` WHERE name LIKE %s", prefix + "%")
    except Exception:
        return None
    best = None
    plen = len(prefix)
    for n in names:
        rest = (n or "")[plen:]
        if rest.isdigit():
            v = cint(rest)
            if best is None or v > best:
                best = v
    return best


def _current(prefix: str) -> int:
    row = frappe.db.sql("SELECT `current` FROM `tabSeries` WHERE name=%s", prefix)
    return cint(row[0][0]) if row else 0


def resync_naming_series(doctypes=None, dry_run: bool = False) -> dict:
    if isinstance(doctypes, str):
        doctypes = [doctypes]
    doctypes = doctypes or DEFAULT_DOCTYPES
    report = {"dry_run": bool(dry_run), "fixed": [], "ok": [], "errors": []}

    for dt in doctypes:
        if not frappe.db.exists("DocType", dt):
            continue
        for prefix in _series_prefixes(dt):
            try:
                max_n = _max_numeric_suffix(dt, prefix)
                if max_n is None:
                    continue
                cur = _current(prefix)
                if max_n > cur:
                    if not dry_run:
                        if frappe.db.sql("SELECT name FROM `tabSeries` WHERE name=%s", prefix):
                            frappe.db.sql("UPDATE `tabSeries` SET `current`=%s WHERE name=%s",
                                          (max_n, prefix))
                        else:
                            frappe.db.sql("INSERT INTO `tabSeries` (name, `current`) VALUES (%s, %s)",
                                          (prefix, max_n))
                    report["fixed"].append({"doctype": dt, "prefix": prefix,
                                            "from": cur, "to": max_n})
                else:
                    report["ok"].append({"prefix": prefix, "current": cur, "max": max_n})
            except Exception:
                report["errors"].append(f"{dt} / {prefix}")
                frappe.log_error(frappe.get_traceback(), f"fix_naming_series: {dt} {prefix}")

    if not dry_run and report["fixed"]:
        try:
            frappe.db.commit()
        except Exception:
            pass

    print(f"[fix_naming_series] dry_run={dry_run} fixed={len(report['fixed'])} "
          f"ok={len(report['ok'])} errors={len(report['errors'])}")
    return report


def execute(dry_run: bool = False) -> dict:
    """Point d'entrée AFTER_MIGRATE."""
    return resync_naming_series(dry_run=dry_run)

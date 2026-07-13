# -*- coding: utf-8 -*-
"""API Grand Livre KYA — restitue les écritures groupées par compte avec solde
progressif, sur le modèle du grand-livre SYSCOHADA (cf. export Sage 100).

Source : doctype « Ecriture Comptable KYA » (saisie manuelle ou import). Aucune
écriture automatique depuis d'autres modules (choix : registre autonome). La
comptabilité générale de référence reste tenue dans Sage ; ce grand-livre KYA
sert de restitution/consultation interne et d'archive imprimable.

Endpoints (réservés Comptabilité / Direction) :
- get_grand_livre(from_date, to_date, compte=None) : lignes + totaux par compte
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

RH_COMPTA_ROLES = {
    "Comptable", "Accounts Manager", "DFC", "Responsable Comptable",
    "Directeur Général", "DGA", "System Manager",
}


def _check_role():
    if not (RH_COMPTA_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la Comptabilité et à la Direction."),
                     frappe.PermissionError)


@frappe.whitelist()
def get_grand_livre(from_date=None, to_date=None, compte=None):
    """Grand-livre : pour chaque compte mouvementé sur la période, la liste des
    écritures (date, journal, pièce, libellé, débit, crédit) et le solde
    progressif. Renvoie aussi les totaux par compte et le total général."""
    _check_role()
    year = getdate(today()).year
    from_date = getdate(from_date) if from_date else getdate(f"{year}-01-01")
    to_date = getdate(to_date) if to_date else getdate(f"{year}-12-31")

    cond = "e.docstatus = 1 AND e.date_ecriture BETWEEN %(fd)s AND %(td)s"
    params = {"fd": from_date, "td": to_date}
    if compte:
        cond += " AND e.compte_numero = %(cpt)s"
        params["cpt"] = compte

    rows = frappe.db.sql(
        f"""
        SELECT e.compte_numero, e.compte_libelle, e.date_ecriture, e.journal,
               e.numero_piece, e.libelle, e.lettrage,
               COALESCE(e.debit,0) AS debit, COALESCE(e.credit,0) AS credit
        FROM `tabEcriture Comptable KYA` e
        WHERE {cond}
        ORDER BY e.compte_numero ASC, e.date_ecriture ASC, e.creation ASC
        """,
        params, as_dict=True,
    )

    comptes = []
    cur = None
    tot_debit = tot_credit = 0.0
    for r in rows:
        if not cur or cur["compte_numero"] != r.compte_numero:
            cur = {
                "compte_numero": r.compte_numero,
                "compte_libelle": r.compte_libelle or "",
                "lignes": [], "total_debit": 0.0, "total_credit": 0.0,
                "solde": 0.0,
            }
            comptes.append(cur)
            solde = 0.0
        solde += flt(r.debit) - flt(r.credit)
        cur["lignes"].append({
            "date": str(r.date_ecriture),
            "journal": r.journal, "piece": r.numero_piece or "",
            "libelle": r.libelle or "", "lettrage": r.lettrage or "",
            "debit": flt(r.debit), "credit": flt(r.credit),
            "solde": round(solde, 2),
        })
        cur["total_debit"] += flt(r.debit)
        cur["total_credit"] += flt(r.credit)
        cur["solde"] = round(solde, 2)
        tot_debit += flt(r.debit)
        tot_credit += flt(r.credit)

    for c in comptes:
        c["total_debit"] = round(c["total_debit"], 2)
        c["total_credit"] = round(c["total_credit"], 2)

    return {
        "from_date": str(from_date), "to_date": str(to_date),
        "compte": compte or "",
        "comptes": comptes,
        "nb_comptes": len(comptes),
        "total_debit": round(tot_debit, 2),
        "total_credit": round(tot_credit, 2),
        "solde_general": round(tot_debit - tot_credit, 2),
    }


@frappe.whitelist()
def liste_comptes():
    """Liste des comptes mouvementés (pour le filtre)."""
    _check_role()
    return frappe.db.sql(
        """SELECT DISTINCT compte_numero, compte_libelle
           FROM `tabEcriture Comptable KYA` WHERE docstatus=1
           ORDER BY compte_numero""", as_dict=True)

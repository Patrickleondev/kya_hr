# -*- coding: utf-8 -*-
"""Campagne de tests RÉALISTES des opérations KYA, rôle par rôle.

Différence avec multirole_test (gating des workflows) : ici chaque étape est
exécutée COMME DANS LA VRAIE VIE avec la session du rôle, SANS passe-droit :
  - création du document par le rôle initiateur (insert sans ignore_permissions) ;
  - à chaque visa : le rôle POSE SA SIGNATURE (champ Signature) puis franchit
    l'action de workflow avec sa session ;
  - vérification des EFFETS métier (grand-livre stock, PDF, dashboards) ;
  - vérification des ACCÈS pages/API (le bon rôle passe, l'« Employee » simple
    est refusé là où il doit l'être).

Usage :
  bench --site frontend execute kya_hr.maintenance.realistic_ops_test.run_stocks
Résultats : imprimés + écrits dans /tmp/realistic_<domaine>.json
NE PAS lancer en prod (crée des users t_*@kyatest.local et des documents).
"""
from __future__ import annotations

import json

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import today

from kya_hr.maintenance.multirole_test import (  # réutilise les comptes rôle-unique
    TEST_USERS, _email, ensure_test_users,
)

# petite signature dataURL (trait) pour les champs Signature
_SIG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAF0lEQVR4"
        "nGNgYGD4z0AswKtypes0AAAAASUVORK5CYII=").replace("types", "BsT")


# ── infra ────────────────────────────────────────────────────────────────────
class _Report:
    def __init__(self, domaine):
        self.domaine = domaine
        self.rows = []

    def add(self, etape, acteur, ok, detail=""):
        self.rows.append({"etape": etape, "acteur": acteur, "ok": bool(ok),
                          "detail": str(detail)[:300]})
        print("RES|%s|%s|%s|%s" % ("PASS" if ok else "FAIL", etape, acteur,
                                   str(detail)[:160]))

    def dump(self):
        path = "/tmp/realistic_%s.json" % self.domaine
        ok = sum(1 for r in self.rows if r["ok"])
        out = {"domaine": self.domaine, "pass": ok, "fail": len(self.rows) - ok,
               "total": len(self.rows), "rows": self.rows}
        with open(path, "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("RES|DONE|%s|%d/%d PASS|%s" % (self.domaine, ok, len(self.rows), path))
        return out


def _as(key):
    """Bascule la session sur l'utilisateur de test du rôle `key`."""
    frappe.set_user(_email(key) if key != "admin" else "Administrator")


def _insert_as(rep, key, doctype, fields, etape):
    """Insert RÉEL (sans ignore_permissions) avec la session du rôle."""
    _as(key)
    try:
        doc = frappe.get_doc(dict(fields, doctype=doctype))
        doc.insert()  # PAS de ignore_permissions : on teste le droit 'create'
        frappe.db.commit()
        rep.add(etape, key, True, doc.name)
        return doc.name
    except Exception as e:
        rep.add(etape, key, False, e)
        return None
    finally:
        frappe.set_user("Administrator")


def _sign_and_act(rep, key, doctype, name, action, sign_field=None, etape=None):
    """Le rôle signe (save réel) puis franchit l'action de workflow."""
    etape = etape or ("%s : %s" % (doctype, action))
    _as(key)
    try:
        doc = frappe.get_doc(doctype, name)
        if sign_field:
            setattr(doc, sign_field, _SIG)
            doc.save()  # écrit AVEC la session du rôle (test du droit write)
            doc = frappe.get_doc(doctype, name)
        apply_workflow(doc, action)
        frappe.db.commit()
        rep.add(etape, key, True, frappe.db.get_value(doctype, name, "workflow_state"))
        return True
    except Exception as e:
        frappe.db.rollback()
        rep.add(etape, key, False, e)
        return False
    finally:
        frappe.set_user("Administrator")


def _api_as(rep, key, fn, etape, expect_deny=False, **kwargs):
    """Appelle une API whitelistée avec la session du rôle."""
    _as(key)
    try:
        out = fn(**kwargs)
        ok = not expect_deny
        rep.add(etape, key, ok, "refus attendu mais accès accordé" if expect_deny
                else (str(out)[:120] if out is not None else "ok"))
        return out
    except frappe.PermissionError:
        rep.add(etape, key, expect_deny, "PermissionError" +
                ("" if expect_deny else " (accès refusé à tort)"))
        return None
    except Exception as e:
        rep.add(etape, key, False, e)
        return None
    finally:
        frappe.set_user("Administrator")


def _pdf_as(rep, key, doctype, name):
    """Télécharge le PDF de la fiche avec la session du rôle (comme le bouton)."""
    _as(key)
    try:
        html = frappe.get_print(doctype, name)
        ok = bool(html) and "Traceback" not in html
        rep.add("PDF %s" % doctype, key, ok, "%d octets html" % len(html or ""))
    except Exception as e:
        rep.add("PDF %s" % doctype, key, False, e)
    finally:
        frappe.set_user("Administrator")


def _cleanup_doc(doctype, name):
    if not name or not frappe.db.exists(doctype, name):
        return
    frappe.set_user("Administrator")
    try:
        doc = frappe.get_doc(doctype, name)
        if doc.docstatus == 1:
            doc.cancel()
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()


# ── STOCKS ───────────────────────────────────────────────────────────────────
_ART_DESIGN = "Article Test Réaliste"


def _magasin():
    rows = frappe.get_all("Warehouse", filters={"is_group": 0, "disabled": 0},
                          pluck="name", limit=1)
    return rows[0] if rows else None


def run_stocks():
    """PV entrée → sortie → retour → inventaire + ajout article + dashboards,
    chaque étape avec la session du rôle réel."""
    frappe.set_user("Administrator")
    ensure_test_users()
    rep = _Report("stocks")
    from kya_hr.api import stock_kya as SK

    mag = _magasin()
    if not mag:
        rep.add("préparation", "-", False, "aucun Warehouse actif sur ce site")
        return rep.dump()
    rep.add("préparation : magasin", "-", True, mag)
    created = []  # [(doctype, name)]
    art = None

    try:
        # 1. AJOUT ARTICLE — par le magasin, via l'API (SANS code : désignation)
        _api_as(rep, "stock", SK.importer_articles,
                "Ajouter un article (sans code)", rows=[{
                    "designation": _ART_DESIGN, "categorie": "Modules PV",
                    "unite": "Unité"}])
        # le même appel par un employé simple doit être REFUSÉ
        _api_as(rep, "employee", SK.importer_articles,
                "Ajouter un article (employé simple → refus)", expect_deny=True,
                rows=[{"designation": "HACK ARTICLE"}])
        art = frappe.db.get_value("Article KYA", {"designation": _ART_DESIGN}, "name")
        rep.add("Article KYA créé (désignation = clé, pas de code)", "-", bool(art), art)

        # 2. PV ENTRÉE +20 : employé déclare → stock valide → comptable → audit
        name = _insert_as(rep, "employee", "PV Entree Materiel", {
            "objet": "Test réaliste entrée", "date_entree": today(),
            "items": [{"item_code": art, "designation": "Article Test Réaliste",
                       "qte_recue": 20, "warehouse": mag}],
        }, "PV Entrée : création (employé)")
        if name:
            created.append(("PV Entree Materiel", name))
            _sign_and_act(rep, "employee", "PV Entree Materiel", name,
                          "Déclarer la Réception")
            _sign_and_act(rep, "stock", "PV Entree Materiel", name,
                          "Valider Réception Stock", sign_field="signature_achats_stock")
            _sign_and_act(rep, "comptable", "PV Entree Materiel", name,
                          "Valider Comptabilité", sign_field="signature_comptable")
            _sign_and_act(rep, "audit", "PV Entree Materiel", name,
                          "Approuver", sign_field="signature_audit",
                          etape="PV Entree Materiel : Approuver (Audit)")
            solde = _api_as(rep, "stock", SK.solde_item_magasin,
                            "Ledger : solde après entrée (attendu 20)",
                            item=art, magasin=mag)
            if solde is not None:
                rep.add("Ledger : +20 appliqué", "-", (solde.get("total") == 20), solde)
            _pdf_as(rep, "stock", "PV Entree Materiel", name)

        # 3. PV SORTIE −5 : employé → chef → audit → dga → stock livre
        name = _insert_as(rep, "employee", "PV Sortie Materiel", {
            "objet": "Test réaliste sortie", "date_sortie": today(),
            "items": [{"item_code": art, "designation": "Article Test Réaliste",
                       "qte_demandee": 5, "qte_reellement_sortie": 5,
                       "warehouse": mag}],
        }, "PV Sortie : création (employé)")
        if name:
            created.append(("PV Sortie Materiel", name))
            _sign_and_act(rep, "employee", "PV Sortie Materiel", name,
                          "Envoyer pour Approbation", sign_field="signature_demandeur")
            _sign_and_act(rep, "chef", "PV Sortie Materiel", name, "Approuver",
                          etape="PV Sortie : Approuver (Chef)")
            _sign_and_act(rep, "audit", "PV Sortie Materiel", name, "Approuver",
                          sign_field="signature_audit",
                          etape="PV Sortie : Approuver (Audit)")
            _sign_and_act(rep, "dga", "PV Sortie Materiel", name, "Approuver",
                          sign_field="signature_dga",
                          etape="PV Sortie : Approuver (DGA)")
            _sign_and_act(rep, "stock", "PV Sortie Materiel", name, "Livrer",
                          sign_field="signature_magasin")
            solde = _api_as(rep, "stock", SK.solde_item_magasin,
                            "Ledger : solde après sortie (attendu 15)",
                            item=art, magasin=mag)
            if solde is not None:
                rep.add("Ledger : −5 appliqué", "-", (solde.get("total") == 15), solde)
            _pdf_as(rep, "stock", "PV Sortie Materiel", name)

        # 4. RETOUR +2 en réparation : employé déclare → stock réceptionne
        etat_opts = (frappe.get_meta("Retour Materiel KYA Item")
                     .get_field("etat_au_retour").options or "").split("\n")
        etat_rep = next((o for o in etat_opts if "répar" in o.lower()),
                        etat_opts[0] if etat_opts else "Bon")
        name = _insert_as(rep, "employee", "Retour Materiel KYA", {
            "date_retour": today(), "objet": "Test réaliste retour",
            "items": [{"item_code": art, "designation": "Article Test Réaliste",
                       "qte_retournee": 2, "etat_au_retour": etat_rep,
                       "warehouse": mag}],
        }, "Retour : création (employé)")
        if name:
            created.append(("Retour Materiel KYA", name))
            _sign_and_act(rep, "employee", "Retour Materiel KYA", name,
                          "Déclarer le Retour", sign_field="signature_retourneur")
            _sign_and_act(rep, "stock", "Retour Materiel KYA", name,
                          "Réceptionner Retour", sign_field="signature_magasin")
            solde = _api_as(rep, "stock", SK.solde_item_magasin,
                            "Ledger : solde après retour (attendu total 17)",
                            item=art, magasin=mag)
            if solde is not None:
                rep.add("Ledger : +2 réparation", "-",
                        (solde.get("total") == 17 and solde.get("reparation") == 2),
                        solde)
            _pdf_as(rep, "stock", "Retour Materiel KYA", name)

        # 5. INVENTAIRE : le magasin compte 10 bon état + 1 réparation → Ajustement
        name = _insert_as(rep, "stock", "Inventaire KYA", {
            "objet": "Test réaliste inventaire", "date_inventaire": today(),
            "responsable_nom": "Magasin Test",
            "items": [{"item_code": art, "warehouse": mag,
                       "qte_bon_etat": 10, "qte_en_reparation": 1,
                       "qte_comptee": 11}],
        }, "Inventaire : création (magasin)")
        if name:
            created.append(("Inventaire KYA", name))
            _sign_and_act(rep, "stock", "Inventaire KYA", name,
                          "Soumettre au Magasin", sign_field="signature_responsable")
            _sign_and_act(rep, "stock", "Inventaire KYA", name, "Valider",
                          sign_field="signature_magasin")
            solde = _api_as(rep, "stock", SK.solde_item_magasin,
                            "Ledger : solde après inventaire (attendu total 11)",
                            item=art, magasin=mag)
            if solde is not None:
                rep.add("Ledger : ajustement inventaire", "-",
                        (solde.get("total") == 11), solde)
            _pdf_as(rep, "stock", "Inventaire KYA", name)

        # 6. DASHBOARDS & PAGES — bon rôle OK, employé simple refusé
        _api_as(rep, "stock", SK.dashboard_overview, "Cockpit : dashboard_overview (magasin)")
        _api_as(rep, "stock", SK.etat_inventaire, "Cockpit : état inventaire (magasin)",
                magasin=mag)
        _api_as(rep, "employee", SK.dashboard_overview,
                "Cockpit : dashboard_overview (employé simple → refus)", expect_deny=True)
        _api_as(rep, "dg", SK.dashboard_overview, "Cockpit : dashboard_overview (DG lecture)")

        from kya_hr.www import stock_kya as PAGE
        for key, deny in (("stock", False), ("employee", True), ("dg", False)):
            _as(key)
            try:
                ctx = frappe._dict()
                PAGE.get_context(ctx)
                rep.add("Page /stock-kya", key, not deny,
                        "refus attendu mais page servie" if deny else "servie")
            except (frappe.PermissionError, frappe.Redirect):
                rep.add("Page /stock-kya", key, deny,
                        "refusée" + ("" if deny else " à tort"))
            except Exception as e:
                rep.add("Page /stock-kya", key, False, e)
            finally:
                frappe.set_user("Administrator")

    finally:
        # ── nettoyage : fiches, mouvements du ledger, article de test ──
        frappe.set_user("Administrator")
        for dt, nm in reversed(created):
            _cleanup_doc(dt, nm)
        if art and frappe.db.exists("DocType", "Mouvement Stock KYA"):
            for nm in frappe.get_all("Mouvement Stock KYA",
                                     filters={"item": art}, pluck="name"):
                frappe.delete_doc("Mouvement Stock KYA", nm,
                                  ignore_permissions=True, force=True)
        if art and frappe.db.exists("Article KYA", art):
            try:
                frappe.delete_doc("Article KYA", art, ignore_permissions=True, force=True)
            except Exception:
                frappe.db.set_value("Article KYA", art, "actif", 0)
        frappe.db.commit()

    return rep.dump()


# ── ACHATS ───────────────────────────────────────────────────────────────────
def _ref_emp():
    return frappe.db.get_value("Employee", {"user_id": _email("employee")}, "name")


def run_achats():
    """Demande d'achat (≤100k direct DAAF / >100k jusqu'au DG), Bon de commande
    (≤100k DGA / >100k DG + négatif DGA bloqué), Appel d'offre — signatures posées."""
    frappe.set_user("Administrator")
    ensure_test_users()
    rep = _Report("achats")
    emp = _ref_emp()
    created = []

    try:
        # 1. DEMANDE ACHAT ≤100k : employé → chef → DAAF (approuvé direct)
        name = _insert_as(rep, "employee", "Demande Achat KYA", {
            "employee": emp, "date_demande": today(), "objet": "Petites fournitures",
            "items": [{"description": "Ramette papier", "quantite": 10,
                       "prix_unitaire": 3500, "montant": 35000}],
        }, "DA ≤100k : création (employé)")
        if name:
            created.append(("Demande Achat KYA", name))
            _sign_and_act(rep, "employee", "Demande Achat KYA", name, "Soumettre",
                          sign_field="signature_demandeur", etape="DA ≤100k : Soumettre (employé)")
            _sign_and_act(rep, "chef", "Demande Achat KYA", name, "Approuver",
                          sign_field="signature_chef", etape="DA ≤100k : Approuver (Chef)")
            _sign_and_act(rep, "daaf", "Demande Achat KYA", name, "Approuver",
                          etape="DA ≤100k : Approuver (DAAF) → Approuvé")
            st = frappe.db.get_value("Demande Achat KYA", name, "workflow_state")
            rep.add("DA ≤100k : approuvé SANS étape DG", "-", st == "Approuvé", st)
            _pdf_as(rep, "daaf", "Demande Achat KYA", name)

        # 2. DEMANDE ACHAT >100k : employé → chef → DAAF → DG
        name = _insert_as(rep, "employee", "Demande Achat KYA", {
            "employee": emp, "date_demande": today(), "objet": "Gros équipement",
            "items": [{"description": "Groupe électrogène", "quantite": 1,
                       "prix_unitaire": 850000, "montant": 850000}],
        }, "DA >100k : création (employé)")
        if name:
            created.append(("Demande Achat KYA", name))
            _sign_and_act(rep, "employee", "Demande Achat KYA", name, "Soumettre",
                          sign_field="signature_demandeur", etape="DA >100k : Soumettre (employé)")
            _sign_and_act(rep, "chef", "Demande Achat KYA", name, "Approuver",
                          sign_field="signature_chef", etape="DA >100k : Approuver (Chef)")
            _sign_and_act(rep, "daaf", "Demande Achat KYA", name, "Approuver",
                          etape="DA >100k : Approuver (DAAF) → passe au DG")
            st = frappe.db.get_value("Demande Achat KYA", name, "workflow_state")
            rep.add("DA >100k : bien routé En attente DG", "-", st == "En attente DG", st)
            _sign_and_act(rep, "dg", "Demande Achat KYA", name, "Approuver",
                          sign_field="signature_dg", etape="DA >100k : Approuver (DG)")
            _pdf_as(rep, "dg", "Demande Achat KYA", name)

        # 3. BON COMMANDE ≤100k : achats → visa audit → DGA autorise
        name = _insert_as(rep, "achats", "Bon Commande KYA", {
            "numero_bc": "BC-TEST-R1", "date_bc": today(), "objet": "Consommables",
            "fournisseur_nom": "Fournisseur Test",
            "articles": [{"description": "Câble 4mm²", "quantite": 10,
                          "prix_unitaire": 8000}],
        }, "BC ≤100k : création (Resp. Achats)")
        if name:
            created.append(("Bon Commande KYA", name))
            _sign_and_act(rep, "achats", "Bon Commande KYA", name, "Soumettre",
                          etape="BC ≤100k : Soumettre (Achats)")
            _sign_and_act(rep, "audit", "Bon Commande KYA", name, "Viser",
                          etape="BC ≤100k : Viser (Audit)")
            _sign_and_act(rep, "dga", "Bon Commande KYA", name, "Autoriser",
                          sign_field="signature_dga", etape="BC ≤100k : Autoriser (DGA)")
            _pdf_as(rep, "achats", "Bon Commande KYA", name)

        # 4. BON COMMANDE >100k : DGA doit être BLOQUÉ, seul le DG autorise
        name = _insert_as(rep, "achats", "Bon Commande KYA", {
            "numero_bc": "BC-TEST-R2", "date_bc": today(), "objet": "Gros lot",
            "fournisseur_nom": "Fournisseur Test",
            "articles": [{"description": "Onduleur 10kW", "quantite": 2,
                          "prix_unitaire": 950000}],
        }, "BC >100k : création (Resp. Achats)")
        if name:
            created.append(("Bon Commande KYA", name))
            _sign_and_act(rep, "achats", "Bon Commande KYA", name, "Soumettre",
                          etape="BC >100k : Soumettre (Achats)")
            _sign_and_act(rep, "audit", "Bon Commande KYA", name, "Viser",
                          etape="BC >100k : Viser (Audit)")
            # négatif : le DGA n'a PAS le droit d'autoriser >100k
            _as("dga")
            try:
                doc = frappe.get_doc("Bon Commande KYA", name)
                apply_workflow(doc, "Autoriser")
                frappe.db.rollback()
                rep.add("BC >100k : DGA bloqué (seuil)", "dga", False,
                        "le DGA a pu autoriser >100k — seuil non respecté !")
            except Exception:
                frappe.db.rollback()
                rep.add("BC >100k : DGA bloqué (seuil)", "dga", True, "refus attendu")
            finally:
                frappe.set_user("Administrator")
            _sign_and_act(rep, "dg", "Bon Commande KYA", name, "Autoriser",
                          sign_field="signature_dg", etape="BC >100k : Autoriser (DG)")
            _pdf_as(rep, "dg", "Bon Commande KYA", name)

        # 5. APPEL D'OFFRE : création par Achats (pas de workflow) + PDF
        name = _insert_as(rep, "achats", "Appel Offre KYA", {
            "date_ao": today(), "date_limite": today(), "demandeur": emp,
            "objet": "AO test réaliste",
            "items": [{"description": "Modules PV 455Wc", "quantite": 50}],
            "fournisseurs": [{"fournisseur_nom": "Fournisseur A"},
                             {"fournisseur_nom": "Fournisseur B"}],
        }, "AO : création (Resp. Achats)")
        if name:
            created.append(("Appel Offre KYA", name))
            _pdf_as(rep, "achats", "Appel Offre KYA", name)

        # 6. Un caissier ne crée PAS de demande d'achat (rôle sans droit).
        # HRMS ré-ajoute automatiquement le rôle « Employee » aux comptes liés à
        # une fiche Employee ; ce rôle donne le droit de créer une DA. Pour que
        # l'assertion « le rôle Caissier SEUL ne suffit pas » reste valable, on
        # remet le compte de test à son rôle pur avant le test négatif.
        frappe.set_user("Administrator")
        _cu = frappe.get_doc("User", _email("caissier"))
        _cu.set("roles", [r for r in _cu.roles if r.role == "Caissier"])
        _cu.save(ignore_permissions=True)
        frappe.db.commit()
        _as("caissier")
        try:
            d = frappe.get_doc({"doctype": "Demande Achat KYA", "employee": emp,
                                "date_demande": today(), "objet": "x",
                                "items": [{"description": "x", "quantite": 1}]})
            d.insert()
            created.append(("Demande Achat KYA", d.name))
            rep.add("DA : caissier bloqué en création", "caissier", False,
                    "le caissier a pu créer une DA")
        except frappe.PermissionError:
            rep.add("DA : caissier bloqué en création", "caissier", True, "refus attendu")
        except Exception as e:
            rep.add("DA : caissier bloqué en création", "caissier", False, e)
        finally:
            frappe.set_user("Administrator")

    finally:
        frappe.set_user("Administrator")
        for dt, nm in reversed(created):
            _cleanup_doc(dt, nm)
        frappe.db.commit()

    return rep.dump()


# ── COMPTA ───────────────────────────────────────────────────────────────────
def run_compta():
    """Brouillard de caisse (caissière→comptable→DFC), état récap chèques
    (comptable→DFC), dashboards compta, et mail hebdo DG/DGA (Email Queue)."""
    frappe.set_user("Administrator")
    ensure_test_users()
    rep = _Report("compta")
    emp = _ref_emp()
    created = []

    try:
        # 1. BROUILLARD CAISSE : caissière crée + signe → comptable → DFC
        name = _insert_as(rep, "caissier", "Brouillard Caisse", {
            "date_brouillard": today(), "caissiere": emp, "total_reel_caisse": 75000,
            "lignes": [{"date_ligne": today(), "designation": "Vente pièces", "entree": 75000}],
        }, "Brouillard : création (caissière)")
        if name:
            created.append(("Brouillard Caisse", name))
            _sign_and_act(rep, "caissier", "Brouillard Caisse", name,
                          "Soumettre au Comptable", sign_field="signature_caissiere")
            _sign_and_act(rep, "comptable", "Brouillard Caisse", name,
                          "Viser (Comptable)", sign_field="signature_comptable")
            _sign_and_act(rep, "dfc", "Brouillard Caisse", name,
                          "Approuver (DFC)", sign_field="signature_dfc")
            _pdf_as(rep, "dfc", "Brouillard Caisse", name)

        # 2. ÉTAT RÉCAP CHÈQUES : comptable crée + signe → DFC valide + signe
        name = _insert_as(rep, "comptable", "Etat Recap Cheques", {
            "date_etat": today(), "redacteur": emp,
            "semaine_du": today(), "semaine_au": today(),
            "lignes": [{"num_cheque": "0042", "banque": "Ecobank",
                        "beneficiaire": "Fournisseur Y", "montant": 250000}],
        }, "État récap : création (comptable)")
        if name:
            created.append(("Etat Recap Cheques", name))
            _sign_and_act(rep, "comptable", "Etat Recap Cheques", name,
                          "Soumettre au DFC", sign_field="signature_redacteur")
            _sign_and_act(rep, "dfc", "Etat Recap Cheques", name,
                          "Valider", sign_field="signature_dfc")
            _pdf_as(rep, "dfc", "Etat Recap Cheques", name)

        # 3. PAGES : dashboard compta + récap brouillards (bons rôles / refus employé)
        from kya_hr.www import comptabilite_dashboard as PC
        from kya_hr.www import recap_brouillards as PR
        for page_mod, label, cases in (
            (PC, "/comptabilite-dashboard", (("comptable", False), ("dfc", False),
                                             ("employee", True))),
            (PR, "/recap-brouillards", (("dg", False), ("dfc", False),
                                        ("employee", True))),
        ):
            for key, deny in cases:
                _as(key)
                try:
                    ctx = frappe._dict()
                    page_mod.get_context(ctx)
                    rep.add("Page %s" % label, key, not deny,
                            "refus attendu mais servie" if deny else "servie")
                except (frappe.PermissionError, frappe.Redirect):
                    rep.add("Page %s" % label, key, deny,
                            "refusée" + ("" if deny else " à tort"))
                except Exception as e:
                    rep.add("Page %s" % label, key, False, e)
                finally:
                    frappe.set_user("Administrator")

        # 4. MAIL HEBDO DG/DGA : on déclenche le scheduler et on vérifie la file
        frappe.set_user("Administrator")
        from kya_hr.kya_hr.doctype.brouillard_caisse.brouillard_caisse import (
            send_weekly_dg_summary)
        before = frappe.db.count("Email Queue")
        try:
            send_weekly_dg_summary()
            after = frappe.db.count("Email Queue")
            gained = after - before
            # le brouillard soumis à l'étape 1 est dans la semaine → mail attendu
            rep.add("Mail hebdo brouillards DG/DGA (Email Queue)", "-",
                    gained >= 1, "%d mail(s) mis en file" % gained)
            if gained:
                last = frappe.get_all("Email Queue", fields=["name"],
                                      order_by="creation desc", limit=1)
                rcpt = frappe.get_all("Email Queue Recipient",
                                      filters={"parent": last[0].name},
                                      pluck="recipient") if last else []
                rep.add("Mail hebdo : destinataires", "-", bool(rcpt), ", ".join(rcpt)[:200])
        except Exception as e:
            rep.add("Mail hebdo brouillards DG/DGA", "-", False, e)

    finally:
        frappe.set_user("Administrator")
        for dt, nm in reversed(created):
            _cleanup_doc(dt, nm)
        frappe.db.commit()

    return rep.dump()


# ── RH ───────────────────────────────────────────────────────────────────────
def _ensure_role_user(key, roles, as_employee=False):
    """Crée à la volée un utilisateur de test mono-rôle (pour les rôles RH pas
    déjà couverts par TEST_USERS : stagiaire, maître de stage, resp stagiaires)."""
    email = _email(key)
    if frappe.db.exists("User", email):
        u = frappe.get_doc("User", email)
    else:
        u = frappe.new_doc("User")
        u.email = email
        u.first_name = "Test"
        u.last_name = key.upper()
        u.send_welcome_email = 0
        u.user_type = "System User"
        u.insert(ignore_permissions=True)
    existing = {r.role for r in u.roles}
    for r in roles:
        if frappe.db.exists("Role", r) and r not in existing:
            u.append("roles", {"role": r})
    u.enabled = 1
    u.save(ignore_permissions=True)
    if as_employee and not frappe.db.exists("Employee", {"user_id": email}):
        company = frappe.db.get_default("company") or frappe.get_all("Company", pluck="name", limit=1)[0]
        e = frappe.new_doc("Employee")
        e.first_name, e.last_name = "Test", key.upper()
        e.date_of_birth, e.date_of_joining = "1998-01-01", today()
        e.company, e.status, e.user_id = company, "Active", email
        g = frappe.get_all("Gender", pluck="name", limit=1)
        if g:
            e.gender = g[0]
        e.insert(ignore_permissions=True)
    frappe.db.commit()
    return email


def run_rh():
    """Permission sortie employé (emp→chef→RH→DG) & stagiaire (stag→maître→resp
    stag→DG), Planning congé (emp→RH→DG), Besoin de formation (chef→revue RH),
    chacun avec la session du rôle et les signatures."""
    frappe.set_user("Administrator")
    ensure_test_users()
    rep = _Report("rh")
    emp = _ref_emp()
    created = []

    try:
        # 1. PERMISSION SORTIE EMPLOYÉ : emp signe → chef → RH → DG
        name = _insert_as(rep, "employee", "Permission Sortie Employe", {
            "employee": emp, "date_sortie": today(), "heure_depart": "09:00:00",
            "type_permission": "Personnelle", "motif": "RDV administratif",
        }, "Perm. sortie employé : création")
        if name:
            created.append(("Permission Sortie Employe", name))
            _sign_and_act(rep, "employee", "Permission Sortie Employe", name,
                          "Soumettre", sign_field="signature_employe")
            _sign_and_act(rep, "chef", "Permission Sortie Employe", name, "Approuver",
                          sign_field="signature_chef", etape="Perm. employé : Approuver (Chef)")
            _sign_and_act(rep, "rh", "Permission Sortie Employe", name, "Approuver",
                          sign_field="signature_rh", etape="Perm. employé : Approuver (RH)")
            _sign_and_act(rep, "dg", "Permission Sortie Employe", name, "Approuver",
                          sign_field="signature_dga", etape="Perm. employé : Approuver (Direction)")
            _pdf_as(rep, "rh", "Permission Sortie Employe", name)

        # 2. PERMISSION SORTIE STAGIAIRE : stagiaire → maître de stage → resp
        #    stagiaires → DG (rôles créés à la volée)
        _ensure_role_user("stagiaire", ["Stagiaire", "Employee"], as_employee=True)
        _ensure_role_user("maitre_stage", ["Maître de Stage"], as_employee=True)
        _ensure_role_user("resp_stagiaires", ["Responsable des Stagiaires"], as_employee=True)
        stag_emp = frappe.db.get_value("Employee", {"user_id": _email("stagiaire")}, "name")
        if stag_emp:  # rendre le stagiaire réaliste (type d'emploi = Stage)
            frappe.db.set_value("Employee", stag_emp, "employment_type", "Stage",
                                update_modified=False)
        name = _insert_as(rep, "stagiaire", "Permission Sortie Stagiaire", {
            "employee": stag_emp, "date_sortie": today(), "motif": "Sortie pédagogique",
        }, "Perm. sortie stagiaire : création")
        if name:
            created.append(("Permission Sortie Stagiaire", name))
            _sign_and_act(rep, "stagiaire", "Permission Sortie Stagiaire", name,
                          "Soumettre", etape="Perm. stagiaire : Soumettre (stagiaire)")
            _sign_and_act(rep, "maitre_stage", "Permission Sortie Stagiaire", name,
                          "Approuver", etape="Perm. stagiaire : Approuver (Maître de stage)")
            _sign_and_act(rep, "resp_stagiaires", "Permission Sortie Stagiaire", name,
                          "Approuver", etape="Perm. stagiaire : Approuver (Resp. stagiaires)")
            _sign_and_act(rep, "dg", "Permission Sortie Stagiaire", name, "Approuver",
                          etape="Perm. stagiaire : Approuver (DG)")
            _pdf_as(rep, "resp_stagiaires", "Permission Sortie Stagiaire", name)

        # 3. PLANNING CONGÉ : employé soumet → RH approuve → DG approuve
        lt = frappe.get_all("Leave Type", pluck="name", limit=1)
        type_conge = lt[0] if lt else "Congé Maladie"
        name = _insert_as(rep, "employee", "Planning Conge", {
            "employee": emp, "annee": int(today()[:4]),
            "periodes": [{"date_debut": today(), "date_fin": today(),
                          "type_conge": type_conge}],
        }, "Planning congé : création (employé)")
        if name:
            created.append(("Planning Conge", name))
            _sign_and_act(rep, "employee", "Planning Conge", name, "Soumettre",
                          etape="Planning congé : Soumettre (employé)")
            _sign_and_act(rep, "rh", "Planning Conge", name, "Approuver (RH)",
                          etape="Planning congé : Approuver (RH)")
            _sign_and_act(rep, "dg", "Planning Conge", name, "Approuver",
                          etape="Planning congé : Approuver (DG)")
            _pdf_as(rep, "rh", "Planning Conge", name)

        # 4. BESOIN DE FORMATION : chef d'équipe soumet → RH prend en revue → clôture
        eq = frappe.get_all("Equipe KYA", pluck="name", limit=1)
        if eq:
            # le chef de test doit porter le rôle Chef Equipe pour soumettre.
            # On (re)crée SA fiche employé AVANT de lire chef_emp : un run
            # précédent a pu la supprimer (teardown), et lire chef_emp trop tôt
            # donnait None -> « chef_equipe obligatoire » à la création.
            _ensure_role_user("chef", ["Chef Service", "Chef Equipe", "Employee"], as_employee=True)
            chef_emp = frappe.db.get_value("Employee", {"user_id": _email("chef")}, "name")
            # chef_equipe de Besoin de Formation est fetch_from equipe.chef_equipe :
            # on repose donc le chef courant sur l'Equipe (un teardown a pu le
            # détacher), sinon le fetch ramène un chef vide/pendant.
            frappe.db.set_value("Equipe KYA", eq[0], "chef_equipe", chef_emp)
            frappe.db.commit()
            name = _insert_as(rep, "chef", "Besoin de Formation", {
                "equipe": eq[0], "chef_equipe": chef_emp, "annee": int(today()[:4]),
                "lignes": [{"intitule": "Sécurité électrique",
                            "justification": "Mise à niveau habilitation"}],
            }, "Besoin formation : création (chef d'équipe)")
            if name:
                created.append(("Besoin de Formation", name))
                _sign_and_act(rep, "chef", "Besoin de Formation", name,
                              "Soumettre à la RH", etape="Besoin formation : Soumettre (chef)")
                _sign_and_act(rep, "rh", "Besoin de Formation", name,
                              "Prendre en revue", etape="Besoin formation : Prendre en revue (RH)")
                _sign_and_act(rep, "rh", "Besoin de Formation", name,
                              "Clôturer la revue", etape="Besoin formation : Clôturer (RH)")
                _pdf_as(rep, "rh", "Besoin de Formation", name)
        else:
            rep.add("Besoin formation", "-", True, "aucune Equipe KYA (skip)")

        # 5. NÉGATIF : un employé simple ne valide pas une permission d'autrui
        name = _insert_as(rep, "employee", "Permission Sortie Employe", {
            "employee": emp, "date_sortie": today(), "heure_depart": "10:00:00",
            "type_permission": "Personnelle", "motif": "Négatif"}, "Perm (négatif) : création")
        if name:
            created.append(("Permission Sortie Employe", name))
            _sign_and_act(rep, "employee", "Permission Sortie Employe", name,
                          "Soumettre", sign_field="signature_employe",
                          etape="Perm (négatif) : Soumettre")
            _as("comptable")
            try:
                doc = frappe.get_doc("Permission Sortie Employe", name)
                apply_workflow(doc, "Approuver")
                frappe.db.rollback()
                rep.add("Perm : comptable ne peut PAS approuver", "comptable", False,
                        "le comptable a approuvé une permission RH !")
            except Exception:
                frappe.db.rollback()
                rep.add("Perm : comptable ne peut PAS approuver", "comptable", True, "refus attendu")
            finally:
                frappe.set_user("Administrator")

    finally:
        frappe.set_user("Administrator")
        for dt, nm in reversed(created):
            _cleanup_doc(dt, nm)
        for key in ("stagiaire", "maitre_stage", "resp_stagiaires"):
            em = _email(key)
            if frappe.db.exists("User", em):
                for e in frappe.get_all("Employee", filters={"user_id": em}, pluck="name"):
                    frappe.delete_doc("Employee", e, ignore_permissions=True, force=True)
                frappe.delete_doc("User", em, ignore_permissions=True, force=True)
        # L'Employee créé pour le compte « chef » (Besoin de Formation) est
        # supprimé pour ne pas polluer d'autres harnais (ex. _ref_employee).
        # IMPORTANT : détacher d'abord tout lien `reports_to` / `chef_equipe`
        # pointant vers lui, sinon on laisse un lien PENDANT et les créations
        # DA / Permission / Planning d'un run ultérieur échouent avec
        # « Could not find Responsable direct » (validation de lien Frappe).
        for e in frappe.get_all("Employee", filters={"user_id": _email("chef")}, pluck="name"):
            for sub in frappe.get_all("Employee", filters={"reports_to": e}, pluck="name"):
                frappe.db.set_value("Employee", sub, "reports_to", None)
            for eq in frappe.get_all("Equipe KYA", filters={"chef_equipe": e}, pluck="name"):
                frappe.db.set_value("Equipe KYA", eq, "chef_equipe", None)
            try:
                frappe.delete_doc("Employee", e, ignore_permissions=True, force=True)
            except Exception:
                pass
        frappe.db.commit()

    return rep.dump()


def run_all():
    """Lance les 4 domaines et agrège."""
    frappe.set_user("Administrator")
    out = {}
    for fn in (run_stocks, run_achats, run_compta, run_rh):
        r = fn()
        out[r["domaine"]] = {"pass": r["pass"], "fail": r["fail"], "total": r["total"]}
    tot_p = sum(v["pass"] for v in out.values())
    tot = sum(v["total"] for v in out.values())
    print("RES|GLOBAL|%d/%d PASS|%s" % (tot_p, tot, out))
    return out


# ── mots de passe pour les tests navigateur (Playwright) ───────────────────
@frappe.whitelist()
def set_test_passwords(pwd="Test1234!"):
    """Donne un mot de passe connu aux comptes t_* pour les tests UI réels."""
    from frappe.utils.password import update_password
    frappe.set_user("Administrator")
    ensure_test_users()
    done = []
    for key in TEST_USERS:
        email = _email(key)
        if frappe.db.exists("User", email):
            update_password(email, pwd)
            done.append(email)
    frappe.db.commit()
    print("RES|PASSWORDS|%d comptes|%s" % (len(done), pwd))
    return done

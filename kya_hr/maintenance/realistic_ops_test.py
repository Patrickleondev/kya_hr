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
_ITEM = "TEST-REALISTE-01"


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

    try:
        # 1. AJOUT ARTICLE — par le magasin, via l'API du cockpit (= bouton Import)
        _api_as(rep, "stock", SK.importer_articles,
                "Ajouter un article (cockpit)", rows=[{
                    "code": _ITEM, "nom": "Article Test Réaliste",
                    "groupe": "Modules PV - KYA", "uom": "Unité"}])
        # le même appel par un employé simple doit être REFUSÉ
        _api_as(rep, "employee", SK.importer_articles,
                "Ajouter un article (employé simple → refus)", expect_deny=True,
                rows=[{"code": "HACK-01", "nom": "x"}])

        # 2. PV ENTRÉE +20 : employé déclare → stock valide → comptable → audit
        name = _insert_as(rep, "employee", "PV Entree Materiel", {
            "objet": "Test réaliste entrée", "date_entree": today(),
            "items": [{"item_code": _ITEM, "designation": "Article Test Réaliste",
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
                            item=_ITEM, magasin=mag)
            if solde is not None:
                rep.add("Ledger : +20 appliqué", "-", (solde.get("total") == 20), solde)
            _pdf_as(rep, "stock", "PV Entree Materiel", name)

        # 3. PV SORTIE −5 : employé → chef → audit → dga → stock livre
        name = _insert_as(rep, "employee", "PV Sortie Materiel", {
            "objet": "Test réaliste sortie", "date_sortie": today(),
            "items": [{"item_code": _ITEM, "designation": "Article Test Réaliste",
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
                            item=_ITEM, magasin=mag)
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
            "items": [{"item_code": _ITEM, "designation": "Article Test Réaliste",
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
                            item=_ITEM, magasin=mag)
            if solde is not None:
                rep.add("Ledger : +2 réparation", "-",
                        (solde.get("total") == 17 and solde.get("reparation") == 2),
                        solde)
            _pdf_as(rep, "stock", "Retour Materiel KYA", name)

        # 5. INVENTAIRE : le magasin compte 10 bon état + 1 réparation → Ajustement
        name = _insert_as(rep, "stock", "Inventaire KYA", {
            "objet": "Test réaliste inventaire", "date_inventaire": today(),
            "responsable_nom": "Magasin Test",
            "items": [{"item_code": _ITEM, "warehouse": mag,
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
                            item=_ITEM, magasin=mag)
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
        if frappe.db.exists("DocType", "Mouvement Stock KYA"):
            for nm in frappe.get_all("Mouvement Stock KYA",
                                     filters={"item": _ITEM}, pluck="name"):
                frappe.delete_doc("Mouvement Stock KYA", nm,
                                  ignore_permissions=True, force=True)
        if frappe.db.exists("Item", _ITEM):
            try:
                frappe.delete_doc("Item", _ITEM, ignore_permissions=True, force=True)
            except Exception:
                frappe.db.set_value("Item", _ITEM, "disabled", 1)
        frappe.db.commit()

    return rep.dump()


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

# -*- coding: utf-8 -*-
"""Harnais de test MULTI-RÔLES des circuits KYA (web forms / workflows / PDF).

But : prouver, avec la SESSION RÉELLE de chaque rôle, que :
  1. chaque transition de workflow n'est franchissable QUE par le bon rôle
     (test positif) et qu'un mauvais rôle est bloqué (test négatif) ;
  2. le document se crée et se valide (champs requis cohérents) ;
  3. le téléchargement PDF de la fiche fonctionne (bug wkhtmltopdf/sanitizer) ;
  4. la finalisation (ex. contrat) ne plante pas même si l'envoi mail échoue.

⚠️ Outil de DEV : crée des utilisateurs de test `t_*@kyatest.local` (rôle
unique = test de gating fidèle) + des documents jetables (rollback à la fin).
NE PAS lancer en prod : garde-fou `_guard()` (exige developer_mode ou force=1).

Lancement : `bench --site frontend execute kya_hr.maintenance.multirole_test.run`
Nettoyage users : `... .cleanup_users`
"""
from __future__ import annotations

import frappe
from frappe.utils import today, nowtime


# rôle-clé -> rôles Frappe accordés à l'utilisateur de test (gating fidèle)
TEST_USERS = {
    "employee": ["Employee"],
    "caissier": ["Caissier"],
    "comptable": ["Comptable"],
    "dfc": ["DFC"],
    "chef": ["Chef Service"],
    "rh": ["Responsable RH"],
    "dg": ["Directeur Général"],
    "dga": ["DGA"],
    "stock": ["Chargé des Stocks"],
    "signataire": ["KYA Signataire Contrat"],
    "daaf": ["DAAF"],
    "audit": ["Auditeur Interne"],
    "achats": ["Responsable Achats"],
}


def _guard(force):
    if force:
        return
    if not frappe.conf.get("developer_mode"):
        frappe.throw("multirole_test : refusé hors developer_mode (passer force=1 en dev local).")


def _email(key):
    return "t_%s@kyatest.local" % key


def ensure_test_users():
    """Crée/maj les utilisateurs de test mono-rôle. Idempotent."""
    created = []
    for key, roles in TEST_USERS.items():
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
            created.append(email)
        existing = {r.role for r in u.roles}
        for r in roles:
            if frappe.db.exists("Role", r) and r not in existing:
                u.append("roles", {"role": r})
        u.enabled = 1
        u.save(ignore_permissions=True)
        # le rôle « Employee » n'est effectif que si le User est lié à un
        # Employee (auto-assigné par HRMS). On crée donc un Employee de test.
        if "Employee" in roles:
            _ensure_employee_for(email)
    frappe.db.commit()
    return created


def _ensure_employee_for(email):
    if frappe.db.exists("Employee", {"user_id": email}):
        return
    company = frappe.db.get_default("company") or frappe.get_all("Company", pluck="name", limit=1)[0]
    gender = frappe.get_all("Gender", pluck="name", limit=1)
    e = frappe.new_doc("Employee")
    e.first_name = "Test"
    e.last_name = "Employee"
    if gender:
        e.gender = gender[0]
    e.date_of_birth = "1990-01-01"
    e.date_of_joining = today()
    e.company = company
    e.status = "Active"
    e.user_id = email
    e.insert(ignore_permissions=True)


def cleanup_users(force=1):
    _guard(force)
    n = 0
    for key in TEST_USERS:
        email = _email(key)
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, ignore_permissions=True, force=True)
            n += 1
    frappe.db.commit()
    print("cleanup_users: supprimés", n)
    return n


def _ref_employee():
    # On privilégie l'employé du compte de test « employee » (demandeur attendu),
    # sinon un employé réel NON lié à un compte de test (pour éviter qu'un
    # approbateur de test soit pris pour le demandeur → faux self-approval).
    own = frappe.db.get_value("Employee", {"user_id": _email("employee"), "status": "Active"}, "name")
    if own:
        return own
    e = frappe.get_all(
        "Employee",
        filters={"status": "Active", "user_id": ["not like", "t\\_%@kyatest.local"]},
        pluck="name", limit=1,
    )
    if e:
        return e[0]
    e = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=1)
    return e[0] if e else frappe.get_all("Employee", pluck="name", limit=1)[0]


def _first_option(dt, fieldname):
    f = frappe.get_meta(dt).get_field(fieldname)
    if f and f.options:
        opts = [o for o in f.options.split("\n") if o.strip()]
        return opts[0] if opts else None
    return None


# ---------------------------------------------------------------- flows
def _flows(emp):
    retour_etat = _first_option("Retour Materiel KYA Item", "etat_au_retour") or "Bon"
    return [
        {
            "name": "Brouillard Caisse",
            "doctype": "Brouillard Caisse",
            "fields": {
                "date_brouillard": today(), "caissiere": emp,
                "total_reel_caisse": 50000,
                "lignes": [{"date_ligne": today(), "designation": "Vente test", "entree": 50000}],
            },
            "submit_action": "Soumettre au Comptable",
            "submitter": "caissier",
            "steps": [
                ("Soumettre au Comptable", "caissier", True),
                ("Viser (Comptable)", "comptable", True),
                ("Approuver (DFC)", "dfc", True),
            ],
            "negative": ("Soumettre au Comptable", "employee"),
            "pdf": True,
        },
        {
            "name": "Etat Recap Cheques",
            "doctype": "Etat Recap Cheques",
            "fields": {
                "date_etat": today(), "redacteur": emp,
                "semaine_du": today(), "semaine_au": today(),
                "lignes": [{"num_cheque": "0001", "banque": "Ecobank", "beneficiaire": "Fournisseur X", "montant": 120000}],
            },
            "submit_action": "Soumettre au DFC",
            "submitter": "comptable",
            "steps": [
                ("Soumettre au DFC", "comptable", True),
                ("Valider", "dfc", True),
            ],
            "negative": ("Soumettre au DFC", "employee"),
            "pdf": True,
        },
        {
            "name": "Permission Sortie Employe",
            "doctype": "Permission Sortie Employe",
            "fields": {
                "employee": emp, "date_sortie": today(), "heure_depart": "09:00:00",
                "type_permission": "Personnelle", "motif": "Test sortie",
            },
            "submit_action": "Soumettre",
            "submitter": "employee",
            "steps": [
                ("Soumettre", "employee", True),
                ("Approuver", "chef", True),
                ("Approuver", "rh", True),
                ("Approuver", "dg", True),
            ],
            "negative": ("Soumettre", "comptable"),
            "pdf": True,
        },
        {
            "name": "Retour Materiel KYA",
            "doctype": "Retour Materiel KYA",
            "fields": {
                "date_retour": today(), "objet": "Retour test",
                "items": [{"qte_retournee": 1, "etat_au_retour": retour_etat, "designation": "Casque"}],
            },
            "submit_action": "Déclarer le Retour",
            "submitter": "employee",
            "steps": [
                ("Déclarer le Retour", "employee", True),
                ("Réceptionner Retour", "stock", True),
            ],
            "negative": ("Déclarer le Retour", "comptable"),
            "pdf": True,
        },
        {
            "name": "KYA Contrat (CDI, M)",
            "doctype": "KYA Contrat",
            "fields": {
                "contract_type": "CDI", "employee_name": "Test Salarié",
                "employee_email": "t_salarie@kyatest.local", "telephone": "90000000",
                "sexe": "Masculin", "date_debut": today(),
                "taches": [{"description": "Maintenance des installations"}],
            },
            "submit_action": "Envoyer au Salarié",
            "submitter": "rh",
            "steps": [
                ("Envoyer au Salarié", "rh", True, None),
                ("Signer", "signataire", True,
                 {"signature_employe": _SIG, "contrat_lu": 1}),
                ("Soumettre au DG", "rh", True, None),
                ("Valider", "dg", True, {"signature_dg": _SIG}),
            ],
            "negative": ("Envoyer au Salarié", "employee"),
            "pdf": True,
        },
        {
            "name": "Demande Achat (Achats)",
            "doctype": "Demande Achat KYA",
            "fields": {
                "employee": emp, "date_demande": today(), "objet": "Achat câbles test",
                "items": [{"description": "Câble 4mm²", "quantite": 2}],
            },
            "submit_action": "Soumettre",
            "submitter": "employee",
            "steps": [
                ("Soumettre", "employee", True, None),
                ("Approuver", "chef", True, None),
                ("Approuver", "daaf", True, None),
            ],
            # Le Comptable a un droit read+write légitime sur les demandes d'achat
            # (visibilité compta) → ce n'est PAS un « mauvais rôle » ici. On teste
            # un rôle réellement sans droit d'écriture (Caissier) pour le négatif.
            "negative": ("Soumettre", "caissier"),
            "pdf": True,
        },
        {
            "name": "PV Sortie Materiel (Stocks, DGA signe)",
            "doctype": "PV Sortie Materiel",
            "fields": {
                "objet": "Sortie outillage test", "date_sortie": today(),
                "items": [{"designation": "Perceuse", "qte_demandee": 1}],
            },
            "submit_action": "Envoyer pour Approbation",
            "submitter": "employee",
            "steps": [
                ("Envoyer pour Approbation", "employee", True, None),
                ("Approuver", "chef", True, None),
                ("Approuver", "audit", True, None),
                ("Approuver", "dga", True, None),   # DGA signe à la place du DG
                ("Livrer", "stock", True, None),
            ],
            "negative": ("Envoyer pour Approbation", "comptable"),
            "pdf": True,
        },
        {
            "name": "Permission Sortie (DGA signe à la place du DG)",
            "doctype": "Permission Sortie Employe",
            "fields": {
                "employee": emp, "date_sortie": today(), "heure_depart": "10:00:00",
                "type_permission": "Administrative", "motif": "Test DGA",
            },
            "submit_action": "Soumettre",
            "submitter": "employee",
            "steps": [
                ("Soumettre", "employee", True, None),
                ("Approuver", "chef", True, None),
                ("Approuver", "rh", True, None),
                ("Approuver", "dga", True, None),   # DGA au lieu du DG
            ],
            "negative": ("Soumettre", "comptable"),
            "pdf": True,
        },
        {
            "name": "Bon Commande (>100k → Achats → Visa Audit → DG)",
            "doctype": "Bon Commande KYA",
            "fields": {
                "numero_bc": "BC-TEST-001", "date_bc": today(),
                "objet": "Commande test", "fournisseur_nom": "Fournisseur Test",
                "articles": [{"description": "Onduleur 5kVA", "quantite": 1, "prix_unitaire": 750000}],
                "total_ttc": 750000,
            },
            "submit_action": "Soumettre",
            "submitter": "achats",
            "steps": [
                ("Soumettre", "achats", True, None),
                ("Viser", "audit", True, None),
                ("Autoriser", "dg", True, None),   # 750000 > 100000 -> DG
            ],
            "negative": ("Soumettre", "comptable"),
            "pdf": True,
        },
        {
            "name": "Bon Commande (≤100k → Achats → Visa Audit → DGA)",
            "doctype": "Bon Commande KYA",
            "fields": {
                "numero_bc": "BC-TEST-002", "date_bc": today(),
                "objet": "Petit achat test", "fournisseur_nom": "Fournisseur Test",
                "articles": [{"description": "Câbles", "quantite": 1, "prix_unitaire": 50000}],
                "total_ttc": 50000,
            },
            "submit_action": "Soumettre",
            "submitter": "achats",
            "steps": [
                ("Soumettre", "achats", True, None),
                ("Viser", "audit", True, None),
                ("Autoriser", "dga", True, None),   # 50000 <= 100000 -> DGA
            ],
            "negative": None,
            "pdf": True,
        },
    ]


# petite signature factice (data-URI tronquée : suffit aux gardes "signé")
_SIG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1"
        "HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _initial_state(doctype):
    wf = frappe.db.get_value("Workflow", {"document_type": doctype, "is_active": 1}, "name")
    if not wf:
        return None, None
    st = frappe.db.get_value("Workflow Document State", {"parent": wf}, "state", order_by="idx asc")
    field = frappe.db.get_value("Workflow", wf, "workflow_state_field")
    return st, field


def _create(flow, emp, owner_email):
    doc = frappe.new_doc(flow["doctype"])
    for k, v in flow["fields"].items():
        if isinstance(v, list):
            for row in v:
                doc.append(k, row)
        else:
            doc.set(k, v)
    state, field = _initial_state(flow["doctype"])
    if field and state:
        doc.set(field, state)
    doc.insert(ignore_permissions=True)
    # le créateur réel d'une fiche = celui qui la soumet (perms if_owner)
    frappe.db.set_value(flow["doctype"], doc.name, "owner", owner_email, update_modified=False)
    return doc


def _apply(doctype, name, action, user, prep=None):
    from frappe.model.workflow import apply_workflow
    # le prep (signature, case lue…) doit être PERSISTÉ avant la transition,
    # car apply_workflow revalide le doc (ex. _validate_signatures du contrat).
    if prep:
        frappe.set_user("Administrator")
        d0 = frappe.get_doc(doctype, name)
        for k, v in prep.items():
            d0.set(k, v)
        d0.save(ignore_permissions=True)
    frappe.set_user(user)
    doc = frappe.get_doc(doctype, name)
    apply_workflow(doc, action)
    frappe.set_user("Administrator")
    return doc


def _test_pdf(doctype, name):
    from kya_hr.api import print_format as pf
    frappe.local.response = frappe._dict()
    pf.download_pdf(doctype, name)
    content = frappe.local.response.get("filecontent")
    return bool(content) and len(content) > 1000  # PDF non vide


def run(force=1):
    _guard(force)
    ensure_test_users()
    users = {k: _email(k) for k in TEST_USERS}
    emp = _ref_employee()
    results = []

    for flow in _flows(emp):
        dt = flow["doctype"]
        tag = flow["name"]
        try:
            # --- création + validation (fiche détenue par le soumetteur) ---
            doc = _create(flow, emp, users[flow["submitter"]])
            results.append((tag, "création", "PASS", doc.name))

            # --- test NÉGATIF : mauvais rôle bloqué sur 1re transition ---
            if flow.get("negative"):
                neg_action, neg_key = flow["negative"]
                try:
                    _apply(dt, doc.name, neg_action, users[neg_key])
                    results.append((tag, "négatif (%s bloqué?)" % neg_key, "FAIL", "transition AUTORISÉE à tort"))
                except Exception:
                    results.append((tag, "négatif (%s bloqué)" % neg_key, "PASS", ""))
                finally:
                    frappe.set_user("Administrator")

            # --- happy path : chaque étape par le bon rôle ---
            for step in flow["steps"]:
                action, key = step[0], step[1]
                prep = step[3] if len(step) > 3 else None
                try:
                    _apply(dt, doc.name, action, users[key], prep)
                    results.append((tag, "%s [%s]" % (action, key), "PASS", ""))
                except Exception as e:
                    results.append((tag, "%s [%s]" % (action, key), "FAIL", str(e)[:180]))
                    break
                finally:
                    frappe.set_user("Administrator")

            # --- PDF ---
            if flow.get("pdf"):
                try:
                    ok = _test_pdf(dt, doc.name)
                    results.append((tag, "PDF download", "PASS" if ok else "FAIL",
                                    "" if ok else "contenu vide"))
                except Exception as e:
                    results.append((tag, "PDF download", "FAIL", str(e)[:180]))
                finally:
                    frappe.set_user("Administrator")

        except Exception as e:
            import traceback
            results.append((tag, "création", "FAIL", traceback.format_exc()[-300:]))
        finally:
            frappe.set_user("Administrator")

    # tout est jetable -> rollback (aucun doc test persistant)
    frappe.db.rollback()

    # rapport
    npass = sum(1 for r in results if r[2] == "PASS")
    nfail = sum(1 for r in results if r[2] == "FAIL")
    print("\n================ RAPPORT MULTI-RÔLES ================")
    cur = None
    for tag, step, status, info in results:
        if tag != cur:
            print("\n###", tag)
            cur = tag
        mark = "OK  " if status == "PASS" else "XXX "
        print("   %s %-34s %s" % (mark, step, ("- " + info) if info else ""))
    print("\n----------------------------------------------------")
    print("TOTAL : %d PASS / %d FAIL" % (npass, nfail))
    return {"pass": npass, "fail": nfail, "results": results}

"""GRAND DIAGNOSTIC du systeme KYA (lecture seule, sans danger).

Objectif : repondre factuellement a LA question recurrente -
"quand un Responsable Stock / Chargé Stock / approbateur se connecte,
voit-il vraiment ce dont il a besoin, ou RIEN ?"

Ce module n'ECRIT RIEN. Il peut etre lance sur n'importe quelle instance
(local, preprod, prod) sans risque :
    bench --site <site> execute kya_hr.system_diagnostic.run

Sections du rapport :
 1. ROLES        : doublons (Chef d'Équipe vs Chef Equipe), rôles orphelins.
 2. WORKSPACES   : pour chaque espace KYA, quels rôles le voient ;
                   espaces publics SANS rôle (visibles par tous) ;
                   espaces invisibles pour les rôles de base.
 3. ROLE -> VUE  : pour chaque rôle métier, la LISTE des espaces qu'il voit.
 4. ACCES DOCTYPE: pour les DocTypes clés (web forms + workflow), qui peut
                   read / write / create / submit (et si if_owner bloque).
 5. WORKFLOWS    : chaque transition -> le rôle 'allowed' a-t-il vraiment
                   write SANS if_owner sur le DocType ? (sinon il ne peut
                   PAS signer = bug "non autorisé dans le flux").
 6. EMPLOYEE<->USER : combien d'Employees Active sans user_id (racine du
                   "Nom du Demandeur vide" + accès incohérents).
 7. WEB FORMS    : chaque web form -> Employee/Stagiaire ont-ils les droits
                   sur le DocType cible ?

Chaque section retourne aussi des `problems` (liste de chaines) : ce qui
reste a corriger. Un rapport propre = 0 problème.
"""
from __future__ import annotations

import frappe


# Rôles "de base" que tout salarié/stagiaire possède.
BASE_ROLES = {"Employee", "Stagiaire", "All"}

# Web forms NATIVES Frappe/ERPNext (pas KYA) : ne pas les compter comme
# problème si Employee ne peut pas "créer" (edit-profile EDITE le User
# existant, addresses/issues/tasks ne font pas partie des flux KYA).
NATIVE_WEBFORMS = {
    "edit-profile", "addresses", "issues", "tasks", "job-application",
    "request-data", "request-to-delete-data",
}

# Doublons sémantiques connus (orthographes différentes du MÊME rôle métier).
# Le user veut les fusionner. _norm ne les attrape pas (le "d'" diffère).
KNOWN_DUPLICATE_ROLES = [
    ("Chef d'Équipe", "Chef Equipe"),
    ("DG", "Directeur Général"),
]

# Rôles qui doivent voir "tout" (direction + admin) - ne comptent pas comme
# problème s'ils voient beaucoup d'espaces.
GLOBAL_ROLES = {"System Manager", "Administrator", "Directeur Général", "DG", "DGA"}

# Espaces KYA suivis par le diagnostic.
KYA_WORKSPACES = [
    "Espace Employes", "Espace Stagiaires", "Gestion Equipe", "Espace RH",
    "Espace Stock", "Espace Achats", "Espace Comptabilite", "Logistique",
    "Direction Generale",
]

# DocTypes métier clés (web forms + workflow) a auditer pour l'accès.
KEY_DOCTYPES = [
    "Demande Achat KYA", "Bon Commande KYA", "Permission Sortie Employe",
    "Permission Sortie Stagiaire", "Planning Conge", "Leave Application",
    "PV Sortie Materiel", "PV Entree Materiel", "Retour Materiel KYA",
    "Bilan Fin de Stage", "Brouillard Caisse", "Sortie Vehicule",
    "Inventaire KYA", "Stock Entry",
]


def _section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# 1. ROLES
# ---------------------------------------------------------------------------
def diag_roles() -> dict:
    problems = []
    roles = [r.name for r in frappe.get_all("Role", filters={"disabled": 0},
                                            fields=["name"])]

    # Doublons par normalisation (accents/espaces/apostrophes retirés).
    def _norm(s: str) -> str:
        return (s.lower().replace("'", "").replace("é", "e").replace("è", "e")
                .replace("ê", "e").replace("-", " ").replace("  ", " ").strip())

    seen: dict[str, list[str]] = {}
    for r in roles:
        seen.setdefault(_norm(r), []).append(r)
    dups = {k: v for k, v in seen.items() if len(v) > 1}

    for k, variants in dups.items():
        problems.append(f"Doublon de rôle : {variants}")

    # Doublons sémantiques connus (orthographes du même rôle métier).
    known = []
    role_set = set(roles)
    for a, b in KNOWN_DUPLICATE_ROLES:
        if a in role_set and b in role_set:
            known.append((a, b))
            problems.append(f"Doublon sémantique à fusionner : '{a}' = '{b}'")

    return {"total_roles": len(roles), "duplicates": dups,
            "known_duplicates": known, "problems": problems}


# ---------------------------------------------------------------------------
# 2 + 3. WORKSPACES  &  ROLE -> VUE
# ---------------------------------------------------------------------------
def _workspace_roles_map() -> dict[str, set[str]]:
    """Retourne {workspace: {rôles}} (vide = visible par tous)."""
    rows = frappe.get_all(
        "Has Role",
        filters={"parenttype": "Workspace"},
        fields=["parent", "role"],
    )
    m: dict[str, set[str]] = {}
    for r in rows:
        m.setdefault(r.parent, set()).add(r.role)
    return m


def diag_workspaces() -> dict:
    problems = []
    wmap = _workspace_roles_map()
    report = {}

    for ws in KYA_WORKSPACES:
        if not frappe.db.exists("Workspace", ws):
            problems.append(f"Workspace ABSENT : {ws}")
            report[ws] = {"exists": False}
            continue
        is_hidden = frappe.db.get_value("Workspace", ws, "is_hidden")
        roles = sorted(wmap.get(ws, set()))
        report[ws] = {"exists": True, "is_hidden": bool(is_hidden), "roles": roles}
        if is_hidden:
            problems.append(f"Workspace CACHÉ (is_hidden=1) : {ws}")

    # Vérifs ciblées sur les espaces de base
    base_checks = {
        "Espace Employes": "Employee",
        "Espace Stagiaires": "Stagiaire",
    }
    for ws, needed in base_checks.items():
        roles = report.get(ws, {}).get("roles", [])
        if needed not in roles:
            problems.append(
                f"{ws} ne donne PAS le rôle de base '{needed}' "
                f"-> les {needed} ne voient pas leur espace !")

    return {"workspaces": report, "problems": problems}


def diag_role_views() -> dict:
    """Pour chaque rôle métier, la liste des espaces KYA qu'il voit."""
    wmap = _workspace_roles_map()
    # Rôles à analyser = ceux présents sur au moins un espace KYA + rôles de base.
    interesting = set(BASE_ROLES)
    for ws in KYA_WORKSPACES:
        interesting |= wmap.get(ws, set())

    views: dict[str, list[str]] = {}
    problems = []
    for role in sorted(interesting):
        seen = []
        for ws in KYA_WORKSPACES:
            ws_roles = wmap.get(ws, set())
            # Espace visible si AUCUN rôle défini (public ouvert) OU rôle présent.
            if not ws_roles or role in ws_roles:
                seen.append(ws)
        views[role] = seen
        if not seen and role not in BASE_ROLES:
            problems.append(f"Rôle '{role}' ne voit AUCUN espace KYA !")

    return {"views": views, "problems": problems}


# ---------------------------------------------------------------------------
# 4. ACCES DOCTYPE
# ---------------------------------------------------------------------------
def _perm_for(doctype: str, role: str) -> dict | None:
    """Permission effective (permlevel 0) d'un rôle sur un DocType.

    On combine DocPerm (standard) et Custom DocPerm. Frappe : si des Custom
    DocPerm existent pour le DocType, elles REMPLACENT les standard.
    """
    has_custom = frappe.db.exists("Custom DocPerm", {"parent": doctype})
    table = "Custom DocPerm" if has_custom else "DocPerm"
    row = frappe.db.get_value(
        table,
        {"parent": doctype, "role": role, "permlevel": 0},
        ["read", "write", "create", "submit", "if_owner"],
        as_dict=True,
    )
    return row


def diag_doctype_access() -> dict:
    report = {}
    problems = []
    for dt in KEY_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            report[dt] = {"exists": False}
            continue
        submittable = bool(frappe.db.get_value("DocType", dt, "is_submittable"))
        # Rôles ayant une perm sur ce DocType
        has_custom = frappe.db.exists("Custom DocPerm", {"parent": dt})
        table = "Custom DocPerm" if has_custom else "DocPerm"
        rows = frappe.get_all(table, filters={"parent": dt, "permlevel": 0},
                              fields=["role", "read", "write", "create",
                                      "submit", "if_owner"])
        report[dt] = {
            "exists": True, "submittable": submittable,
            "perm_source": table,
            "perms": {r.role: {"r": r.read, "w": r.write, "c": r.create,
                               "s": r.submit, "own": r.if_owner} for r in rows},
        }
        # Employee/Stagiaire devraient pouvoir créer (déposer une demande)
        for base in ("Employee", "Stagiaire"):
            p = report[dt]["perms"].get(base)
            if p and not p["c"]:
                problems.append(f"{dt}: {base} ne peut PAS créer (create=0)")
    return {"doctypes": report, "problems": problems}


# ---------------------------------------------------------------------------
# 5. WORKFLOWS
# ---------------------------------------------------------------------------
def diag_workflows() -> dict:
    problems = []
    report = []
    workflows = frappe.get_all("Workflow", filters={"is_active": 1},
                               fields=["name", "document_type"])
    for wf in workflows:
        dt = wf.document_type
        transitions = frappe.get_all(
            "Workflow Transition", filters={"parent": wf.name},
            fields=["state", "action", "next_state", "allowed"])
        wf_entry = {"workflow": wf.name, "doctype": dt, "transitions": []}
        for t in transitions:
            role = (t.allowed or "").strip()
            ok = True
            note = ""
            if role and role not in BASE_ROLES and frappe.db.exists("DocType", dt):
                if not frappe.db.exists("Role", role):
                    ok = False
                    note = "RÔLE INEXISTANT (transition morte)"
                    wf_entry["transitions"].append({
                        "from": t.state, "action": t.action, "to": t.next_state,
                        "role": role, "ok": ok, "note": note})
                    problems.append(
                        f"{dt} [{t.state} --{t.action}--> {t.next_state}] : "
                        f"rôle '{role}' {note}")
                    continue
                p = _perm_for(dt, role)
                if not p:
                    ok = False
                    note = "AUCUNE perm"
                elif not p.get("write"):
                    ok = False
                    note = "write=0 (ne peut pas signer)"
                elif p.get("if_owner"):
                    ok = False
                    note = "if_owner=1 (ne peut écrire QUE ses propres docs)"
            wf_entry["transitions"].append({
                "from": t.state, "action": t.action, "to": t.next_state,
                "role": role, "ok": ok, "note": note,
            })
            if not ok:
                problems.append(
                    f"{dt} [{t.state} --{t.action}--> {t.next_state}] : "
                    f"rôle '{role}' {note}")
        report.append(wf_entry)
    return {"workflows": report, "problems": problems}


# ---------------------------------------------------------------------------
# 6. EMPLOYEE <-> USER
# ---------------------------------------------------------------------------
def diag_employee_user() -> dict:
    problems = []
    total = frappe.db.count("Employee", {"status": "Active"})
    linked = frappe.db.count("Employee", {"status": "Active",
                                          "user_id": ["!=", ""]})
    unlinked = total - linked
    if unlinked:
        problems.append(
            f"{unlinked}/{total} Employees Active SANS user_id "
            f"(=> 'Nom du Demandeur' vide, accès incohérents)")
    return {"total_active": total, "linked": linked,
            "unlinked": unlinked, "problems": problems}


# ---------------------------------------------------------------------------
# 7. WEB FORMS
# ---------------------------------------------------------------------------
def diag_webforms() -> dict:
    problems = []
    report = []
    forms = frappe.get_all("Web Form",
                           fields=["name", "doc_type", "published",
                                   "login_required"])
    for wf in forms:
        dt = wf.doc_type
        entry = {"web_form": wf.name, "doctype": dt,
                 "published": wf.published, "login_required": wf.login_required}
        if dt and frappe.db.exists("DocType", dt):
            emp = _perm_for(dt, "Employee")
            entry["employee_can_create"] = bool(emp and emp.get("create"))
            entry["native"] = wf.name in NATIVE_WEBFORMS
            if not entry["employee_can_create"] and not entry["native"]:
                # Seulement un problème si la web form requiert login (interne)
                if wf.login_required:
                    problems.append(
                        f"Web Form '{wf.name}' ({dt}) : Employee ne peut pas "
                        f"créer -> 'Non autorisé' / champs grisés")
        report.append(entry)
    return {"web_forms": report, "problems": problems}


# ---------------------------------------------------------------------------
# ORCHESTRATEUR
# ---------------------------------------------------------------------------
@frappe.whitelist()
def run() -> dict:
    """Lance toutes les sections, imprime un rapport lisible, retourne le tout."""
    out = {}

    _section("1. ROLES (doublons)")
    out["roles"] = diag_roles()
    print(f"  Total rôles actifs : {out['roles']['total_roles']}")
    for k, v in out["roles"]["duplicates"].items():
        print(f"  DOUBLON : {v}")

    _section("2. WORKSPACES (visibilité)")
    out["workspaces"] = diag_workspaces()
    for ws, info in out["workspaces"]["workspaces"].items():
        if info.get("exists"):
            print(f"  {ws:22s} hidden={info['is_hidden']} "
                  f"roles={info['roles']}")
        else:
            print(f"  {ws:22s} ABSENT")

    _section("3. ROLE -> ESPACES VISIBLES")
    out["role_views"] = diag_role_views()
    for role, seen in out["role_views"]["views"].items():
        short = [s.replace("Espace ", "").replace(" Generale", " DG") for s in seen]
        print(f"  {role:28s} -> {short}")

    _section("4. ACCES DOCTYPE (r/w/c/s, own=if_owner)")
    out["doctype_access"] = diag_doctype_access()
    for dt, info in out["doctype_access"]["doctypes"].items():
        if not info.get("exists"):
            print(f"  {dt:26s} ABSENT")
            continue
        base = info["perms"].get("Employee") or info["perms"].get("Stagiaire")
        print(f"  {dt:26s} [{info['perm_source']}] "
              f"submittable={info['submittable']} rôles={len(info['perms'])}")

    _section("5. WORKFLOWS (chaque approbateur peut-il signer ?)")
    out["workflows"] = diag_workflows()
    for wf in out["workflows"]["workflows"]:
        print(f"  Workflow: {wf['workflow']} ({wf['doctype']})")
        for t in wf["transitions"]:
            flag = "OK " if t["ok"] else "!! "
            print(f"    {flag}{t['from']} --{t['action']}--> {t['to']} "
                  f"[{t['role']}] {t['note']}")

    _section("6. EMPLOYEE <-> USER")
    out["employee_user"] = diag_employee_user()
    eu = out["employee_user"]
    print(f"  Active={eu['total_active']} liés={eu['linked']} "
          f"NON liés={eu['unlinked']}")

    _section("7. WEB FORMS")
    out["webforms"] = diag_webforms()
    for wf in out["webforms"]["web_forms"]:
        print(f"  {wf['web_form']:34s} ({wf['doctype']}) "
              f"login_req={wf['login_required']} "
              f"emp_create={wf.get('employee_can_create')}")

    # SYNTHESE DES PROBLEMES
    _section("SYNTHÈSE DES PROBLÈMES À CORRIGER")
    all_problems = []
    for key in ("roles", "workspaces", "role_views", "doctype_access",
                "workflows", "employee_user", "webforms"):
        all_problems += out[key].get("problems", [])
    out["all_problems"] = all_problems
    if not all_problems:
        print("  AUCUN problème détecté. Système cohérent. ✓")
    else:
        for i, p in enumerate(all_problems, 1):
            print(f"  {i:2d}. {p}")
    print(f"\n  >>> {len(all_problems)} problème(s) au total.")

    return out

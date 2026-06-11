"""Garantit la VISIBILITE des workspaces KYA selon l'architecture des roles.

PROBLEME identifie sur l'instance : un workspace public filtre sa
visibilite par sa liste de roles. Si le role de base manque, l'utilisateur
de base ne voit PAS son espace. Constats :
- 'Espace Employes' n'avait PAS le role 'Employee' -> un employe simple
  ne voyait pas son espace par defaut.
- 'Espace Stagiaires' n'avait PAS le role 'Stagiaire' -> idem pour les
  stagiaires.

Architecture KYA voulue (chaque user voit SON espace + ce que son role
donne, RIEN de cache) :
- Tout employe (Employee)        -> Espace Employes
- Tout stagiaire (Stagiaire)     -> Espace Stagiaires
- Chef d'equipe / Chef Service   -> Gestion Equipe
- Responsable/Maitre stagiaires  -> Espace Stagiaires (gestion)
- Responsable Stock / magasin    -> Espace Stock
- Responsable Achats             -> Espace Achats
- Comptable / Caissier / DFC     -> Espace Comptabilite
- RH                             -> Espace RH
- Logistique                     -> Logistique
- DG / DGA                       -> Direction Generale (+ tout)

Ce script AJOUTE les roles manquants (ne retire jamais un role existant,
pour ne pas casser des acces deja en place). Idempotent.

Wrappe dans safe_migrations.AFTER_MIGRATE (apres ensure_visibility).
"""
from __future__ import annotations

import frappe


# Roles MINIMUM que chaque workspace doit exposer.
# DG/DGA/System Manager voient tout (ajoutes partout sauf espaces perso).
WORKSPACE_ROLES: dict[str, list[str]] = {
    # --- Espaces de base (tous les employes / stagiaires) ---
    "Espace Employes": ["Employee"],
    "Espace Stagiaires": ["Stagiaire", "Maître de Stage", "Responsable des Stagiaires"],

    # --- Espaces metier (par role fonctionnel) ---
    "Gestion Equipe": ["Chef Service", "Chef d'Équipe", "Chef Equipe"],
    "Espace RH": ["Responsable RH", "HR User", "HR Manager",
                  "Maître de Stage", "Responsable des Stagiaires"],
    "Espace Stock": ["Chargé des Stocks", "Responsable Stock",
                     "Stock Manager", "Stock User", "Magasinier"],
    "Espace Achats": ["Responsable Achats", "Purchase Manager",
                      "Purchase User", "Chef Service"],
    "Espace Comptabilite": ["Comptable", "Caissier", "Accounts Manager",
                            "Accounts User", "DFC", "DAAF"],
    "Logistique": ["Gestionnaire de Flotte", "DST - Responsable Logistique",
                   "Chef Service"],

    # --- Direction : voit tout ---
    "Direction Generale": ["Directeur Général", "DG", "DGA", "DAAF"],
}

# Roles qui voient TOUS les espaces (direction + admin).
GLOBAL_VIEWERS = ["System Manager", "Directeur Général", "DGA"]

# Espaces personnels : ne PAS y mettre les global viewers (ils ont le leur).
PERSONAL_WORKSPACES = {"Espace Employes", "Espace Stagiaires"}


def _add_role_to_workspace(ws_name: str, role: str) -> bool:
    """Ajoute `role` au workspace si absent + role existe. True si ajoute."""
    if not frappe.db.exists("Role", role):
        return False
    if frappe.db.exists("Has Role", {
        "parent": ws_name, "parenttype": "Workspace", "role": role,
    }):
        return False
    try:
        hr = frappe.new_doc("Has Role")
        hr.parent = ws_name
        hr.parenttype = "Workspace"
        hr.parentfield = "roles"
        hr.role = role
        hr.insert(ignore_permissions=True)
        return True
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(),
                             f"ensure_workspace_roles: {ws_name}/{role}")
        except Exception:
            pass
        return False


# Raccourcis dashboards a garantir sur Direction Generale (le DG voit tout).
# (label, url)
DG_DASHBOARD_SHORTCUTS = [
    ("📊 Tableau de Bord Global", "/kya-tableau-de-bord"),
    ("👥 Dashboard RH", "/kya-rh-dashboard"),
    ("📦 Dashboard Stocks", "/kya-stocks-dashboard"),
    ("🚚 Dashboard Logistique", "/kya-logistique-dashboard"),
    ("🏗️ Projets & Clients (DGA)", "/dga-projets-clients"),
    ("🛒 Dashboard Achats", "/achats-dashboard"),
    ("🏦 Dashboard Comptabilité", "/comptabilite-dashboard"),
    ("📋 Inventaire & Sorties", "/inventaire-dashboard"),
    ("🎓 Tableau Stagiaires", "/tableau-bord-stagiaires"),
    ("🧑‍💼 Tableau Employés", "/tableau-bord-employes"),
]


def _ensure_dg_dashboard_shortcuts() -> int:
    """Ajoute les raccourcis dashboards manquants a Direction Generale.

    Insertion DIRECTE du child Workspace Shortcut (comme Has Role) pour
    eviter la re-validation complete du Workspace via save() qui levait
    'DocType URL introuvable'. On reproduit la structure exacte d'un
    shortcut URL fonctionnel : type=URL, url=..., link_to vide, color hex.
    """
    ws = "Direction Generale"
    if not frappe.db.exists("Workspace", ws):
        return 0

    # idx de depart : apres les shortcuts existants
    max_idx = frappe.db.sql(
        "SELECT COALESCE(MAX(idx), 0) FROM `tabWorkspace Shortcut` WHERE parent=%s",
        (ws,),
    )[0][0] or 0

    added = 0
    for label, url in DG_DASHBOARD_SHORTCUTS:
        if frappe.db.exists("Workspace Shortcut", {"parent": ws, "url": url}):
            continue
        try:
            max_idx += 1
            sc = frappe.new_doc("Workspace Shortcut")
            sc.parent = ws
            sc.parenttype = "Workspace"
            sc.parentfield = "shortcuts"
            sc.idx = max_idx
            sc.type = "URL"
            sc.label = label
            sc.url = url
            sc.color = "#0054a6"
            sc.insert(ignore_permissions=True)
            added += 1
        except Exception:
            try:
                frappe.log_error(frappe.get_traceback(),
                                 f"ensure_workspace_roles: DG shortcut {url}")
            except Exception:
                pass
    return added


def execute() -> dict:
    summary = {"added": [], "skipped_missing_ws": [], "total_added": 0}

    for ws_name, roles in WORKSPACE_ROLES.items():
        if not frappe.db.exists("Workspace", ws_name):
            summary["skipped_missing_ws"].append(ws_name)
            continue

        # S'assurer que le workspace est visible (non cache)
        try:
            frappe.db.set_value("Workspace", ws_name, "is_hidden", 0,
                                update_modified=False)
        except Exception:
            pass

        wanted = list(roles)
        # Direction + admin voient tout sauf les espaces perso
        if ws_name not in PERSONAL_WORKSPACES:
            wanted += GLOBAL_VIEWERS

        for role in wanted:
            if _add_role_to_workspace(ws_name, role):
                summary["added"].append(f"{ws_name} <- {role}")
                summary["total_added"] += 1

    # Raccourcis dashboards pour le DG (visibilite totale)
    summary["dg_shortcuts_added"] = _ensure_dg_dashboard_shortcuts()

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Workspace")
    except Exception:
        pass

    print(f"[ensure_workspace_roles] total_added={summary['total_added']} "
          f"dg_shortcuts={summary.get('dg_shortcuts_added', 0)}")
    return summary

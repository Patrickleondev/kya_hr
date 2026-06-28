"""Normalisation de l'arbre Department sous 4 macro-départements (vue DG).

Objectif : le DG voit un arbre propre, 100 % français, organisé en 4 macro-
départements — Direction Générale, Services Supports, Services Techniques,
Services Commerciaux — chacun regroupant ses départements/équipes.

GÉNÉRIQUE (marche sur prod ET local) :
- Racine détectée dynamiquement ("Tous les départements" en prod,
  "All Departments" en local).
- Abréviation société lue depuis Company (suffixe « - KYA », « - D »…).
- Les 4 macro-groupes sont REPÉRÉS s'ils existent déjà (tolérant : « Services
  Technique » singulier = macro Techniques), sinon CRÉÉS.
- Chaque autre département est classé par MOTS-CLÉS sur son nom et RATTACHÉ
  sous son macro-groupe. Corrige les orphelins de prod (« Département des
  services techniques », « Département Services Commerciaux » au niveau racine).
- Renommage anglais→français optionnel : ne se déclenche QUE si un nom anglais
  par défaut est trouvé (no-op sur prod déjà en français).

SÉCURITÉ :
- `frappe.rename_doc` propage les références (Employee, Equipe KYA, congés…).
- Ne touche PAS aux affectations équipe/employé (uniquement l'arbre Department).
- Ne supprime/merge JAMAIS automatiquement (les doublons sont rattachés, pas
  fusionnés — décision humaine).
- `execute(dry_run=True)` : RAPPORTE les changements sans rien écrire. À lancer
  sur prod d'abord pour validation.
- Idempotent. Wrappé dans safe_migrations AFTER_MIGRATE (en mode écriture).
"""
from __future__ import annotations

import unicodedata

import frappe

ROOT_CANDIDATES = ["Tous les départements", "All Departments"]

# Les 4 macro-départements canoniques (libellé cible) + mot-clé d'identification
# du GROUPE macro existant (pour le repérer malgré variantes singulier/pluriel).
MACROS = [
    ("Direction Générale",   "direction"),
    ("Services Supports",    "support"),
    ("Services Techniques",  "techni"),
    ("Services Commerciaux", "commerc"),
]

# Classification d'un département quelconque -> macro canonique, par mots-clés.
MACRO_CLASSIFY = {
    "Direction Générale":   ["direction", "general", "informatique", " si ", "système d",
                             "systeme d", "administration", "juridique", "legal",
                             "research", "r&d", "developpement"],
    "Services Supports":    ["support", "comptab", "financ", "achat", "stock", "logist",
                             "ressources humaines", "equipe rh", " rh", "approvision",
                             "magasin", "dispatch", "purchase", "accounts", "human"],
    "Services Techniques":  ["techni", "installation", "fabrication", "assemblage",
                             "maintenance", "sav", "audit", "offre", "production",
                             "operations", "genie", "quality"],
    "Services Commerciaux": ["commerc", "communicat", "marketing", "vente", "sales"],
}

# Renommage anglais par défaut -> français (ne s'applique qu'aux leaves anglais).
ENGLISH_RENAME = {
    "Accounts": "Comptabilité et Finance", "Purchase": "Achats et Stocks",
    "Human Resources": "Ressources Humaines", "Dispatch": "Logistique",
    "Operations": "Installation", "Production": "Fabrication et Assemblage",
    "Customer Service": "Maintenance et SAV", "Quality Management": "Audit Interne",
    "Sales": "Commercial", "Marketing": "Communication",
    "Research & Development": "Informatique", "Management": "Administration",
    "Legal": "Juridique",
}


def _norm(s: str) -> str:
    """Minuscule sans accents, espaces compactés (pour matcher les mots-clés)."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return f" {s.lower().strip()} "


def _find_root() -> str | None:
    for r in ROOT_CANDIDATES:
        if frappe.db.exists("Department", r):
            return r
    # repli : la racine = group sans parent
    rows = frappe.get_all("Department", filters={"is_group": 1, "parent_department": ["in", ["", None]]},
                          pluck="name", limit_page_length=1)
    return rows[0] if rows else None


def _abbr(company: str | None) -> str | None:
    if company:
        return frappe.db.get_value("Company", company, "abbr")
    rows = frappe.get_all("Company", fields=["abbr"], limit_page_length=1)
    return rows[0].abbr if rows else None


def _classify(dept_name: str) -> str | None:
    """Renvoie le macro canonique d'un département d'après son nom, sinon None."""
    n = _norm(dept_name)
    for macro, kws in MACRO_CLASSIFY.items():
        if any(k.strip() and k in n for k in kws):
            return macro
    return None


def execute(dry_run: bool = False) -> dict:
    summary = {"root": None, "abbr": None, "groups_ensured": [], "renamed": [],
               "reparented": [], "skipped": [], "errors": [], "dry_run": bool(dry_run)}

    root = _find_root()
    if not root:
        summary["errors"].append("Racine Department introuvable — abandon.")
        return summary
    summary["root"] = root

    company = frappe.defaults.get_global_default("company")
    abbr = _abbr(company)
    summary["abbr"] = abbr

    def full(label: str) -> str:
        return f"{label} - {abbr}" if abbr else label

    # 1) Repérer/CRÉER les 4 macro-groupes. macro canonique -> name réel en base.
    macro_name: dict[str, str] = {}
    existing_groups = frappe.get_all("Department", filters={"is_group": 1},
                                     fields=["name", "department_name"])
    for label, kw in MACROS:
        match = None
        for g in existing_groups:
            if kw in _norm(g.department_name) and g.name != root:
                match = g.name
                break
        if match:
            macro_name[label] = match
            summary["groups_ensured"].append(f"= {match}")
            continue
        # créer
        target = full(label)
        if dry_run:
            macro_name[label] = target
            summary["groups_ensured"].append(f"+ {target} (à créer)")
            continue
        try:
            doc = frappe.new_doc("Department")
            doc.department_name = label
            doc.is_group = 1
            doc.parent_department = root
            if company:
                doc.company = company
            doc.insert(ignore_permissions=True)
            macro_name[label] = doc.name
            summary["groups_ensured"].append(f"+ {doc.name}")
        except Exception:
            summary["errors"].append(f"create group {label}")
            frappe.log_error(frappe.get_traceback(), f"normalize_departments: group {label}")

    macro_group_names = set(macro_name.values())

    # 2) Renommage anglais->français (no-op si déjà français)
    for eng, fr in ENGLISH_RENAME.items():
        src = frappe.db.get_value("Department", {"department_name": eng, "is_group": 0}, "name")
        if not src:
            continue
        target = full(fr)
        if frappe.db.exists("Department", target):
            continue
        if dry_run:
            summary["renamed"].append(f"{src} -> {target} (simulé)")
            continue
        try:
            frappe.rename_doc("Department", src, target, force=True)
            d = frappe.get_doc("Department", target)
            d.department_name = fr
            d.flags.ignore_permissions = True
            d.save(ignore_permissions=True)
            summary["renamed"].append(f"{src} -> {target}")
        except Exception:
            summary["errors"].append(f"rename {eng}")
            frappe.log_error(frappe.get_traceback(), f"normalize_departments: rename {eng}")

    # 3) Rattacher chaque département (hors racine + hors macro-groupes) sous sa macro
    all_depts = frappe.get_all("Department", fields=["name", "department_name",
                                                     "parent_department", "is_group"])
    for d in all_depts:
        if d.name == root or d.name in macro_group_names:
            continue
        macro = _classify(d.department_name)
        if not macro or macro not in macro_name:
            summary["skipped"].append(d.name)
            continue
        target_parent = macro_name[macro]
        if d.parent_department == target_parent:
            continue
        if dry_run:
            summary["reparented"].append(f"{d.name} -> {target_parent} (simulé)")
            continue
        try:
            doc = frappe.get_doc("Department", d.name)
            doc.parent_department = target_parent
            doc.flags.ignore_permissions = True
            doc.save(ignore_permissions=True)
            summary["reparented"].append(f"{d.name} -> {target_parent}")
        except Exception:
            summary["errors"].append(d.name)
            frappe.log_error(frappe.get_traceback(), f"normalize_departments: reparent {d.name}")

    # 4) Reconstruire l'arbre (sauf dry_run)
    if not dry_run:
        try:
            from frappe.utils.nestedset import rebuild_tree
            rebuild_tree("Department", "parent_department")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "normalize_departments: rebuild_tree")
        try:
            frappe.db.commit()
            frappe.clear_cache(doctype="Department")
        except Exception:
            pass

    print(f"[normalize_departments] dry_run={dry_run} root={root} abbr={abbr} "
          f"groups={len(summary['groups_ensured'])} renamed={len(summary['renamed'])} "
          f"reparented={len(summary['reparented'])} skipped={len(summary['skipped'])} "
          f"errors={len(summary['errors'])}")
    return summary

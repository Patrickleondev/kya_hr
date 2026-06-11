"""KYA Employment Types — normalise les Type d'emploi en francais.

Probleme RH : Frappe/ERPNext cree par defaut des Employment Type en anglais
(Intern, Contract, Full-time, etc.) qui s'affichent mal traduits dans l'UI
("Etape" pour Stage, "Interne" pour Intern...). La RH veut une liste
strictement francaise validee par Hanna IKPE :
  - Stage
  - CDD
  - CDI
  - Prestataire de services
  - Apprentissage

Ce script :
1. Cree les Employment Type FR voulus s'ils n'existent pas
2. Bascule les Employees qui utilisent encore un type EN vers le type FR
   equivalent (via mapping EN_TO_FR)
3. Supprime les Employment Type EN devenus orphelins (zero Employee dessus)

Idempotent : safe a relancer. Pas de delete force tant qu'il y a des
Employees, on garde l'historique propre.
"""
from __future__ import annotations

import frappe


# Liste cible (validee Hanna IKPE / RH KYA).
KYA_EMPLOYMENT_TYPES: list[str] = [
    "Stage",
    "CDD",
    "CDI",
    "Prestataire de services",
    "Apprentissage",
]

# Mapping des types EN natifs Frappe vers le type FR equivalent.
# Sert a basculer les Employees existants avant de purger les EN.
EN_TO_FR: dict[str, str] = {
    "Intern": "Stage",
    "Internship": "Stage",
    "Probation": "Stage",
    "Contract": "CDD",
    "Part-time": "CDD",
    "Full-time": "CDI",
    "Permanent": "CDI",
    "Apprenticeship": "Apprentissage",
    "Apprentice": "Apprentissage",
    "Piece-rate": "Prestataire de services",
    "Commission": "Prestataire de services",
    "Freelance": "Prestataire de services",
    "Consultant": "Prestataire de services",
}


def _ensure_fr_types() -> dict:
    """Cree les Employment Type FR s'ils sont absents."""
    stats = {"created": 0, "existing": 0}
    for name in KYA_EMPLOYMENT_TYPES:
        if frappe.db.exists("Employment Type", name):
            stats["existing"] += 1
            continue
        try:
            doc = frappe.new_doc("Employment Type")
            doc.employee_type_name = name
            doc.insert(ignore_permissions=True)
            stats["created"] += 1
        except Exception as exc:
            try:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"setup_employment_types: ensure '{name}'",
                )
            except Exception:
                pass
    return stats


def _migrate_employees() -> dict:
    """Bascule les Employees du type EN vers le type FR equivalent."""
    stats = {"migrated_employees": 0, "skipped_missing_fr": 0}
    for en_name, fr_name in EN_TO_FR.items():
        if not frappe.db.exists("Employment Type", en_name):
            continue
        if not frappe.db.exists("Employment Type", fr_name):
            stats["skipped_missing_fr"] += 1
            continue

        affected = frappe.db.get_all(
            "Employee",
            filters={"employment_type": en_name},
            fields=["name"],
            limit=10000,
        )
        for emp in affected:
            try:
                frappe.db.set_value(
                    "Employee", emp.name, "employment_type", fr_name,
                    update_modified=False,
                )
                stats["migrated_employees"] += 1
            except Exception:
                try:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"setup_employment_types: migrate {emp.name}",
                    )
                except Exception:
                    pass
    return stats


def _purge_orphan_en_types() -> dict:
    """Supprime les Employment Type EN qui n'ont plus aucun Employee."""
    stats = {"deleted": 0, "kept_still_used": 0}
    for en_name in EN_TO_FR.keys():
        if not frappe.db.exists("Employment Type", en_name):
            continue
        still_used = frappe.db.count("Employee", {"employment_type": en_name})
        if still_used > 0:
            stats["kept_still_used"] += 1
            continue
        try:
            frappe.delete_doc(
                "Employment Type", en_name,
                force=1, ignore_permissions=True,
            )
            stats["deleted"] += 1
        except Exception:
            try:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"setup_employment_types: delete {en_name}",
                )
            except Exception:
                pass
    return stats


def execute() -> dict:
    """Entrypoint after_migrate. Idempotent, ne leve jamais."""
    summary = {}
    try:
        summary["ensure"] = _ensure_fr_types()
        summary["migrate"] = _migrate_employees()
        summary["purge"] = _purge_orphan_en_types()
        frappe.db.commit()
        frappe.clear_cache(doctype="Employment Type")
        frappe.clear_cache(doctype="Employee")
    except Exception as exc:
        summary["error"] = str(exc)
        try:
            frappe.log_error(frappe.get_traceback(), "setup_employment_types: top-level")
        except Exception:
            pass

    print(f"[setup_employment_types] {summary}")
    return summary

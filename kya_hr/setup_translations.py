"""KYA Translation overrides — fix bugs traduction Type d'emploi.

Bug historique : ERPNext/HRMS traduit 'Stage' (EN) en 'Etape' (FR) via
ses translations natives, ce qui trompe la RH (un Employment Type nomme
'Stage' s'affiche 'Etape' dans les select). Idem pour Intern → Interne,
Internship → Stage, etc.

Solution : on force des entrees Translation en base qui ecrasent les
traductions natives parasites. C'est plus fiable que le fr.csv car :
- la base est toujours lue avant les fichiers
- pas besoin de re-build_translations a chaque migrate
- idempotent : on detecte les divergences et on les corrige

Hook : appele par after_migrate via safe_migrations.
"""
from __future__ import annotations

import frappe


# Mapping source (EN) -> traduction FR voulue par KYA.
# IMPORTANT : on ne touche QUE des termes sans risque d'ambiguite contextuelle.
# Ex : "Contract" est aussi un DocType -> ne pas forcer "CDD" ici (casserait
# l'UI ailleurs). Pour renommer les Employment Type, on passe par
# setup_employment_types.py qui touche directement les records.
KYA_TRANSLATION_OVERRIDES: dict[str, str] = {
    # Bug principal RH : "Stage" affiche "Etape" -> forcer Stage = Stage
    "Stage": "Stage",
    "Internship": "Stage",
}

LANGUAGE = "fr"


def _set_translation(source_text: str, target_text: str) -> str:
    """Force une seule entree Translation. Retourne created/updated/unchanged."""
    existing = frappe.db.get_all(
        "Translation",
        filters={"source_text": source_text, "language": LANGUAGE},
        fields=["name", "translated_text"],
        limit=10,
    )

    # Cas 1 : aucune entree -> on cree
    if not existing:
        doc = frappe.new_doc("Translation")
        doc.source_text = source_text
        doc.language = LANGUAGE
        doc.translated_text = target_text
        doc.insert(ignore_permissions=True)
        return "created"

    # Cas 2 : plusieurs entrees (doublons parasites) -> on garde la premiere bonne,
    # on supprime les autres
    correct = None
    to_delete = []
    for row in existing:
        if row.translated_text == target_text and correct is None:
            correct = row.name
        else:
            to_delete.append(row.name)

    for name in to_delete:
        try:
            frappe.delete_doc("Translation", name, force=1, ignore_permissions=True)
        except Exception:
            # Si delete echoue (verrou, FK, etc.) on update au lieu de supprimer
            try:
                frappe.db.set_value("Translation", name, "translated_text", target_text)
            except Exception:
                pass

    # Cas 3 : aucune entree correcte trouvee parmi les doublons -> on cree
    if correct is None:
        doc = frappe.new_doc("Translation")
        doc.source_text = source_text
        doc.language = LANGUAGE
        doc.translated_text = target_text
        doc.insert(ignore_permissions=True)
        return "created"

    return "updated" if to_delete else "unchanged"


def execute() -> dict:
    """Idempotent : safe a appeler plusieurs fois."""
    results = {"created": 0, "updated": 0, "unchanged": 0, "errors": []}

    for source, target in KYA_TRANSLATION_OVERRIDES.items():
        try:
            action = _set_translation(source, target)
            results[action] = results.get(action, 0) + 1
        except Exception as exc:
            results["errors"].append({"source": source, "error": str(exc)})
            try:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"setup_translations: {source}",
                )
            except Exception:
                pass

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[setup_translations] {results}")
    return results

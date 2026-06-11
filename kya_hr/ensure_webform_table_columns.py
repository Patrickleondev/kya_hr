"""Rend les tables des web forms lisibles SANS scroll horizontal.

PROBLEME (retour terrain) : dans les web forms, les tableaux (child tables)
debordent et imposent un scroll horizontal -> saisie penible. Cause : la
grille Frappe repartit les colonnes sur un total de 10 ; si la somme des
`columns` des champs `in_list_view` depasse 10, ca deborde.

Plusieurs child doctypes KYA depassaient 10 (Bon Commande=12, PV Entree=11,
Inventaire=11, Retour=15). Comme ils sont `custom: 1`, editer leur JSON ne
suffit pas (Frappe ne resynchronise pas au migrate). Ce module pose donc
directement, en base, `in_list_view` + `columns` sur les champs concernes
pour tenir la somme <= 10. Idempotent, aucune modif de donnees ni de schema.

Combine avec kya_webform.css (grille fluide 100%, plus de min-width fixe),
les tables tiennent dans la largeur du formulaire : visibles et confortables.
"""
from __future__ import annotations

import frappe


# doctype -> { fieldname: (in_list_view, columns) }.
# La somme des `columns` des champs in_list_view=1 doit rester <= 10.
LAYOUTS: dict[str, dict[str, tuple[int, int]]] = {
    # 2+3+1+1+1+2 = 10
    "Bon Commande KYA Item": {
        "item_code": (1, 2),
        "description": (1, 3),
        "unite": (1, 1),
        "quantite": (1, 1),
        "prix_unitaire": (1, 1),
        "total": (1, 2),
    },
    # 3+3+1+1+1 = 9 (observations -> hors liste, accessible via le crayon)
    "PV Entree Materiel Item": {
        "item_code": (1, 3),
        "designation": (1, 3),
        "uom": (1, 1),
        "qte_commandee": (1, 1),
        "qte_recue": (1, 1),
        "observations": (0, 2),
        "prix_unitaire": (0, 1),
    },
    # 3+2+2+1+1+1 = 10
    "Inventaire KYA Item": {
        "item_code": (1, 3),
        "designation": (1, 2),
        "warehouse": (1, 2),
        "qte_theorique": (1, 1),
        "qte_comptee": (1, 1),
        "ecart": (1, 1),
    },
    # 2+3+1+2+2 = 10 (uom + observations -> hors liste)
    "Retour Materiel KYA Item": {
        "item_code": (1, 2),
        "designation": (1, 3),
        "uom": (0, 1),
        "qte_retournee": (1, 1),
        "warehouse": (1, 2),
        "etat_au_retour": (1, 2),
        "observations": (0, 2),
    },
    # 4+1+1+2+2 = 10
    "Demande Achat Item": {
        "description": (1, 4),
        "quantite": (1, 1),
        "unite": (1, 1),
        "prix_unitaire": (1, 2),
        "montant": (1, 2),
    },
}


def execute() -> dict:
    summary = {"updated": [], "missing": [], "doctypes": 0}
    for dt, fields in LAYOUTS.items():
        if not frappe.db.exists("DocType", dt):
            summary["missing"].append(f"{dt} (doctype absent)")
            continue
        summary["doctypes"] += 1
        changed = False
        for fieldname, (in_list, cols) in fields.items():
            row = frappe.db.get_value(
                "DocField",
                {"parent": dt, "fieldname": fieldname},
                ["name", "in_list_view", "columns"],
                as_dict=True,
            )
            if not row:
                summary["missing"].append(f"{dt}.{fieldname}")
                continue
            if (row.in_list_view or 0) == in_list and (row.columns or 0) == cols:
                continue
            try:
                frappe.db.sql(
                    "UPDATE `tabDocField` SET in_list_view=%s, `columns`=%s WHERE name=%s",
                    (in_list, cols, row.name),
                )
                summary["updated"].append(f"{dt}.{fieldname} -> list={in_list} col={cols}")
                changed = True
            except Exception:
                try:
                    frappe.log_error(frappe.get_traceback(),
                                     f"ensure_webform_table_columns: {dt}.{fieldname}")
                except Exception:
                    pass
        if changed:
            try:
                frappe.clear_cache(doctype=dt)
            except Exception:
                pass

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[ensure_webform_table_columns] doctypes={summary['doctypes']} "
          f"champs_maj={len(summary['updated'])} manquants={len(summary['missing'])}")
    if summary["updated"]:
        print("  " + " | ".join(summary["updated"]))
    if summary["missing"]:
        print("  MANQUE: " + " | ".join(summary["missing"]))
    return summary

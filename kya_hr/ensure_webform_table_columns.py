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
    # 4+2+2+2 = 10 (item_code + specifications hors liste)
    "Appel Offre KYA Item": {
        "item_code": (0, 1),
        "description": (1, 4),
        "quantite": (1, 2),
        "udm": (1, 2),
        "date_requise": (1, 2),
        "specifications": (0, 2),
    },
    # 4+3+2+1 = 10 (le reste hors liste, accessible via le crayon)
    "Appel Offre KYA Fournisseur": {
        "fournisseur": (0, 1),
        "fournisseur_nom": (1, 4),
        "contact": (0, 1),
        "email": (1, 3),
        "telephone": (1, 2),
        "adresse": (0, 2),
        "montant_propose": (1, 1),
        "reponse_recue": (0, 1),
        "retenu": (0, 1),
        "commentaires": (0, 2),
    },
    # 1+3+2+2+2 = 10 (etait 12 -> debordait sur le brouillard de caisse)
    "Brouillard Caisse Ligne": {
        "date_ligne": (1, 1),
        "designation": (1, 3),
        "entree": (1, 2),
        "sortie": (1, 2),
        "solde": (1, 2),
    },
    # 4+3+3 = 10 (colonnes etaient toutes a 0 -> le champ Link Employe debordait)
    "Sortie Vehicule Passager": {
        "employee": (1, 4),
        "employee_name": (1, 3),
        "fonction": (1, 3),
    },
    # 3+2+2+1+1 = 9 (le chef saisit aussi concernés + nb ; justification via crayon)
    "Besoin Formation Item": {
        "intitule": (1, 3),
        "competence": (1, 2),
        "employes_concernes": (1, 2),
        "nb_participants": (1, 1),
        "priorite": (1, 1),
        "justification": (0, 3),
        "statut_rh": (0, 1),
    },
    # 2+2+1+2+3 = 10 (colonnes etaient toutes a 0)
    "Planning Conge Periode": {
        "date_debut": (1, 2),
        "date_fin": (1, 2),
        "nb_jours": (1, 1),
        "type_conge": (1, 2),
        "remarque": (1, 3),
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

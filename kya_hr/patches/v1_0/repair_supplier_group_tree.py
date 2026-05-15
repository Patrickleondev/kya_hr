"""Repair Supplier Group nested set tree.

Contexte : sur la première migration en CI/preprod, le `setup_wizard` ERPNext
lance `setup_demo` qui peut **timeout** (gunicorn 30s) pendant
`chart_of_accounts._import_accounts`. Le worker meurt et redémarre, mais la
table `tabSupplier Group` reste dans un état incohérent (lft/rgt cassés,
parent introuvable, racine manquante) — ce qui fait planter ensuite tout
`Supplier Group.insert()` avec `NestedSetRecursionError: L'article ne peut
être ajouté à ses propres descendants`.

Ce patch :
  1. S'assure que la racine "All Supplier Groups" existe (is_group=1).
  2. Réassigne tout Supplier Group dont le parent est introuvable / cyclique
     à la racine.
  3. Rebuild_tree("Supplier Group", "parent_supplier_group") pour
     recalculer lft/rgt proprement.

Idempotent — peut être rejoué sans effet de bord.
"""

import frappe

ROOT = "All Supplier Groups"


def execute():
    if not frappe.db.has_table("Supplier Group"):
        return

    _ensure_root()
    _detach_invalid_parents()
    _rebuild_tree()
    frappe.db.commit()
    print("[repair_supplier_group_tree] OK")


def _ensure_root():
    if frappe.db.exists("Supplier Group", ROOT):
        # Force is_group=1 + parent NULL (la racine ne doit jamais avoir de parent)
        frappe.db.sql(
            "UPDATE `tabSupplier Group` SET is_group=1, parent_supplier_group=NULL "
            "WHERE name=%s",
            (ROOT,),
        )
        return

    # Racine absente : la créer en bypass pour éviter on_update -> NestedSet
    # qui risque encore d'échouer si l'arbre est cassé. On insertera la ligne
    # à la main puis rebuild_tree recalcule lft/rgt.
    frappe.db.sql(
        """
        INSERT INTO `tabSupplier Group`
            (name, supplier_group_name, is_group, parent_supplier_group,
             lft, rgt, creation, modified, owner, modified_by, docstatus)
        VALUES
            (%s, %s, 1, NULL, 1, 2, NOW(), NOW(), 'Administrator', 'Administrator', 0)
        """,
        (ROOT, ROOT),
    )
    print(f"[repair_supplier_group_tree] racine '{ROOT}' (re)créée en SQL")


def _detach_invalid_parents():
    """Tout groupe dont le parent est introuvable ou pointe sur lui-même
    est ré-accroché à la racine."""
    rows = frappe.db.sql(
        """
        SELECT sg.name, sg.parent_supplier_group
        FROM `tabSupplier Group` sg
        LEFT JOIN `tabSupplier Group` p ON p.name = sg.parent_supplier_group
        WHERE sg.name != %s
          AND (sg.parent_supplier_group IS NULL
               OR sg.parent_supplier_group = ''
               OR sg.parent_supplier_group = sg.name
               OR p.name IS NULL)
        """,
        (ROOT,),
        as_dict=True,
    )
    if not rows:
        return
    for r in rows:
        frappe.db.sql(
            "UPDATE `tabSupplier Group` SET parent_supplier_group=%s WHERE name=%s",
            (ROOT, r.name),
        )
    print(f"[repair_supplier_group_tree] {len(rows)} groupe(s) ré-accroché(s) à la racine")


def _rebuild_tree():
    try:
        from frappe.utils.nestedset import rebuild_tree
        rebuild_tree("Supplier Group", "parent_supplier_group")
        print("[repair_supplier_group_tree] rebuild_tree OK")
    except Exception as e:
        frappe.log_error(
            title="repair_supplier_group_tree — rebuild_tree échec",
            message=frappe.get_traceback() + f"\n\nError: {e}",
        )
        print(f"[repair_supplier_group_tree] rebuild_tree échoué : {e}")

"""Restaure la hiérarchie Comptabilité ERPNext v16 natif.

Diagnostic (15/05/2026) : ERPNext 16.3 a **éclaté** l'ancien workspace
unique `Accounting` en plusieurs sub-workspaces (`Invoicing`,
`Financial Reports`), chacun ayant ses propres Links/Shortcuts. Le
workspace `Accounting` reste comme **parent agrégateur** :
quand l'utilisateur clique sur l'icône Comptabilité, Frappe v16
affiche une grille des workspaces dont `parent_page = "Accounting"`.

Bug observé sur 8087 : `Invoicing` a `parent_page = ""` au lieu de
`"Accounting"`, donc il n'apparaît pas dans la grille parent → seul
`Financial Reports` est visible quand on clique sur Comptabilité.

Ce patch :
  1. Rejoue `reload-doc` pour `invoicing` et `financial_reports` (depuis
     les JSON source ERPNext) pour s'assurer que les Links/Shortcuts
     sont à jour.
  2. Re-fixe `parent_page = "Accounting"` sur `Invoicing` si manquant.

Idempotent.
"""
import frappe


SUB_WORKSPACES = [
    ("accounts", "invoicing", "Invoicing"),
    ("accounts", "financial_reports", "Financial Reports"),
]


def execute():
    if not frappe.db.exists("Workspace", "Accounting"):
        print("[restore_accounting_workspace] Workspace 'Accounting' absent, skip")
        return

    # Étape 1 : reload des sub-workspaces depuis ERPNext source
    for app, folder, label in SUB_WORKSPACES:
        try:
            frappe.reload_doc(app, "workspace", folder, force=True)
            print(f"[restore_accounting_workspace] reload OK : {label}")
        except Exception as e:
            print(f"[restore_accounting_workspace] reload échec {label} : {e}")

    # Étape 2 : forcer parent_page = 'Accounting' sur les enfants
    fixed = 0
    for app, folder, label in SUB_WORKSPACES:
        if not frappe.db.exists("Workspace", label):
            continue
        current_parent = frappe.db.get_value("Workspace", label, "parent_page")
        if current_parent != "Accounting":
            frappe.db.set_value(
                "Workspace", label, "parent_page", "Accounting",
                update_modified=False,
            )
            fixed += 1
            print(f"[restore_accounting_workspace] {label} parent_page : "
                  f"'{current_parent}' → 'Accounting'")

    if fixed:
        frappe.db.commit()
        frappe.clear_cache()
        print(f"[restore_accounting_workspace] {fixed} parent_page corrigé(s)")
    else:
        print("[restore_accounting_workspace] hiérarchie déjà correcte, no-op")

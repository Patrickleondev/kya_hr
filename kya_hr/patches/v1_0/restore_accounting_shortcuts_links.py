"""Restaure les `link_to` des 9 shortcuts du workspace ERPNext `Accounting`.

Diagnostic (15/05/2026) : un agent précédent a vidé `link_to` sur les 9
shortcuts du workspace `Accounting` (Invoicing, Payments, Banking, Taxes,
Financial Reports, Accounts Setup, Budget, Subscription, Share Management).
Conséquence : les icônes s'affichent dans la grille du workspace mais le
clic ne mène nulle part (URL vide).

Ce patch remet les `link_to` corrects et le `type` adapté :
  - Workspaces enfants existants (Invoicing, Financial Reports) :
    `type = Workspace`, `link_to = <Workspace name>`
  - Autres sections (Payments, Banking, etc.) qui n'ont pas de workspace
    enfant en BDD : `type = URL`, `url = /app/<liste-doctype-appropriée>`
    pour pointer vers la list view ERPNext la plus pertinente.

Idempotent.
"""
import frappe


SHORTCUT_FIXES = {
    "Invoicing": {
        "type": "Workspace", "link_to": "Invoicing",
        "fallback_type": "URL", "fallback_url": "/app/sales-invoice",
    },
    "Financial Reports": {
        "type": "Workspace", "link_to": "Financial Reports",
        "fallback_type": "URL", "fallback_url": "/app/financial-statements",
    },
    "Payments": {
        "type": "URL", "url": "/app/payment-entry",
    },
    "Banking": {
        "type": "URL", "url": "/app/bank-account",
    },
    "Taxes": {
        "type": "URL", "url": "/app/tax-template",
    },
    "Accounts Setup": {
        "type": "URL", "url": "/app/account",
    },
    "Budget": {
        "type": "URL", "url": "/app/budget",
    },
    "Subscription": {
        "type": "URL", "url": "/app/subscription",
    },
    "Share Management": {
        "type": "URL", "url": "/app/share-balance",
    },
}


def execute():
    if not frappe.db.exists("Workspace", "Accounting"):
        print("[restore_accounting_shortcuts] Workspace 'Accounting' absent, skip")
        return

    fixed = 0
    for label, cfg in SHORTCUT_FIXES.items():
        shortcut_name = frappe.db.get_value(
            "Workspace Shortcut",
            {"parent": "Accounting", "label": label},
            "name",
        )
        if not shortcut_name:
            print(f"[restore_accounting_shortcuts] shortcut '{label}' introuvable, skip")
            continue

        # Choisir Workspace si existe, sinon fallback URL
        target_type = cfg.get("type")
        if target_type == "Workspace":
            ws_name = cfg["link_to"]
            if frappe.db.exists("Workspace", ws_name):
                new_type = "Workspace"
                new_link_to = ws_name
                new_url = ""
            else:
                new_type = cfg.get("fallback_type", "URL")
                new_link_to = ""
                new_url = cfg.get("fallback_url", "/app/home")
        else:  # URL
            new_type = "URL"
            new_link_to = ""
            new_url = cfg.get("url", "/app/home")

        # État actuel
        current = frappe.db.get_value(
            "Workspace Shortcut", shortcut_name,
            ["type", "link_to", "url"], as_dict=True,
        )
        if (current.type == new_type
                and (current.link_to or "") == new_link_to
                and (current.url or "") == new_url):
            continue  # déjà OK

        frappe.db.set_value("Workspace Shortcut", shortcut_name, {
            "type": new_type,
            "link_to": new_link_to,
            "url": new_url,
        }, update_modified=False)
        fixed += 1
        print(f"[restore_accounting_shortcuts] {label} : "
              f"type={new_type}, link_to={new_link_to}, url={new_url}")

    if fixed:
        frappe.db.commit()
        frappe.clear_cache()
        print(f"[restore_accounting_shortcuts] {fixed} shortcut(s) restauré(s)")
    else:
        print("[restore_accounting_shortcuts] tous les shortcuts déjà corrects, no-op")

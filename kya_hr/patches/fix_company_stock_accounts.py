# -*- coding: utf-8 -*-
"""Fix Company default accounts for Stock Entry validation."""
import frappe


def run():
    company = "KYA-Energy Group"
    abbr = frappe.db.get_value("Company", company, "abbr")

    defaults = {
        "stock_adjustment_account": [f"Stock Adjustment - {abbr}", "Expense", "Indirect Expenses"],
        "default_inventory_account": [f"Stock In Hand - {abbr}", "Asset", "Stock Assets"],
        "stock_received_but_not_billed": [f"Stock Received But Not Billed - {abbr}", "Liability", "Current Liabilities"],
        "default_expense_account": [f"Cost of Goods Sold - {abbr}", "Expense", "Direct Expenses"],
    }

    updates = {}
    for field, (name, root_type, parent_group) in defaults.items():
        if frappe.db.exists("Account", name):
            updates[field] = name
            continue
        parent = frappe.db.get_value("Account", {"company": company, "account_name": parent_group}) \
            or frappe.db.get_value("Account", {"company": company, "is_group": 1, "root_type": root_type}, order_by="lft asc")
        if not parent:
            print(f"  [SKIP] {field}: pas de parent '{parent_group}'")
            continue
        acc = frappe.get_doc({
            "doctype": "Account",
            "account_name": name.split(" - ")[0],
            "parent_account": parent,
            "company": company,
            "root_type": root_type,
            "report_type": "Profit and Loss" if root_type == "Expense" else "Balance Sheet",
            "is_group": 0,
        })
        acc.insert(ignore_permissions=True)
        updates[field] = acc.name
        print(f"  [NEW] {acc.name}")

    for field, value in updates.items():
        frappe.db.set_value("Company", company, field, value)

    # Stock Settings: default warehouse
    frappe.db.set_single_value("Stock Settings", "default_warehouse", "Magasin Central KYA - KG")

    frappe.db.commit()
    print(f"[OK] Company '{company}' mis a jour: {updates}")

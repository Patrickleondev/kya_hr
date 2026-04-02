import random
import string

import frappe
from frappe.utils.password import update_password


def _random_password(length=10):
    chars = string.ascii_letters + string.digits + "@#"
    return "Kya-" + "".join(random.choice(chars) for _ in range(length))


def execute(limit=8):
    limit = int(limit)
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active", "user_id": ["is", "set"]},
        fields=["name", "employee_name", "user_id"],
        order_by="modified desc",
        limit_page_length=2000,
    )

    rows = []
    for emp in employees:
        if len(rows) >= limit:
            break
        if not frappe.db.exists("User", emp.user_id):
            continue

        pwd = _random_password()
        update_password(emp.user_id, pwd)
        rows.append(
            {
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "user": emp.user_id,
                "password": pwd,
            }
        )

    frappe.db.commit()
    return {"ok": True, "total": len(rows), "credentials": rows}

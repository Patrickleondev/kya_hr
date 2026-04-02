import random
import string

import frappe


DEFAULT_ROLE = "Employee"


def _random_password(length=10):
    alphabet = string.ascii_letters + string.digits + "@#"
    return "Kya-" + "".join(random.choice(alphabet) for _ in range(length))


def _safe_email(employee_name, idx):
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in employee_name).strip("-")
    slug = "-".join(filter(None, slug.split("-")))
    return f"mobile.test.{idx}.{slug}@kya-energy.local"


def execute(limit=8, reset_passwords=0):
    """Create mobile test users linked to active employees and return credentials.

    Example:
      bench --site frontend execute kya_hr.setup.create_mobile_test_users.execute
      bench --site frontend execute kya_hr.setup.create_mobile_test_users.execute --kwargs "{'limit':10,'reset_passwords':1}"
    """
    limit = int(limit)
    reset_passwords = bool(int(reset_passwords))

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "user_id", "company"],
        order_by="modified desc",
        limit_page_length=2000,
    )

    created = []
    reused = []

    for idx, emp in enumerate(employees, start=1):
        if len(created) + len(reused) >= limit:
            break

        user_id = emp.user_id
        if user_id and frappe.db.exists("User", user_id):
            if reset_passwords:
                pwd = _random_password()
                frappe.utils.password.update_password(user_id, pwd)
                reused.append({
                    "employee": emp.name,
                    "employee_name": emp.employee_name,
                    "user": user_id,
                    "password": pwd,
                    "action": "password_reset",
                })
            else:
                reused.append({
                    "employee": emp.name,
                    "employee_name": emp.employee_name,
                    "user": user_id,
                    "password": "(inchangé)",
                    "action": "existing_user",
                })
            continue

        email = _safe_email(emp.employee_name or emp.name, idx)
        if frappe.db.exists("User", email):
            email = _safe_email(emp.employee_name or emp.name, idx + 100)

        pwd = _random_password()

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": emp.employee_name or emp.name,
                "send_welcome_email": 0,
                "enabled": 1,
                "user_type": "System User",
                "roles": [{"role": DEFAULT_ROLE}],
            }
        )
        user.flags.ignore_permissions = True
        user.insert(ignore_permissions=True)
        frappe.utils.password.update_password(email, pwd)

        frappe.db.set_value("Employee", emp.name, "user_id", email, update_modified=False)

        created.append(
            {
                "employee": emp.name,
                "employee_name": emp.employee_name,
                "user": email,
                "password": pwd,
                "action": "created",
            }
        )

    frappe.db.commit()
    return {
        "ok": True,
        "created": created,
        "reused": reused,
        "total": len(created) + len(reused),
    }

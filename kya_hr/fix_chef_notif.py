# -*- coding: utf-8 -*-
"""Run via: bench --site frontend execute kya_hr.fix_chef_notif.run"""
import frappe

def run():
    DOCTYPES = [
        ("Demande Achat KYA", "employee_name"),
        ("Permission Sortie Employe", "employee_name"),
        ("Permission Sortie Stagiaire", "employee_name"),
        ("Planning Conge", "employee_name"),
    ]
    
    print("\n=== PHASE A: Custom Field report_to_user ===")
    for dt, after in DOCTYPES:
        cf_name = f"{dt}-report_to_user"
        if frappe.db.exists("Custom Field", cf_name):
            print(f"  [EXISTS] {dt}")
            continue
        if not frappe.db.exists("DocType", dt):
            print(f"  [NO DOCTYPE] {dt}")
            continue
        try:
            cf = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": dt,
                "fieldname": "report_to_user",
                "label": "Email Chef (auto)",
                "fieldtype": "Data",
                "read_only": 1, "hidden": 1, "no_copy": 1,
                "insert_after": after,
                "description": "Auto: employee.reports_to.user_id"
            })
            cf.insert(ignore_permissions=True)
            print(f"  [CREATED] {dt}")
        except Exception as e:
            print(f"  [ERROR] {dt}: {e}")
    
    frappe.db.commit()
    frappe.clear_cache()
    
    # Force migrate to add columns
    print("\n=== PHASE B: Sync schema ===")
    from frappe.model.sync import sync_for
    try:
        sync_for("kya_hr", verbose=False)
    except Exception as e:
        print(f"  sync warning: {e}")
    
    print("\n=== PHASE C: Populate report_to_user ===")
    for dt, _ in DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            docs = frappe.db.sql(f"SELECT name, employee FROM `tab{dt}` WHERE employee IS NOT NULL", as_dict=1)
        except Exception as e:
            print(f"  [SKIP] {dt}: column missing - {e}")
            continue
        cnt = 0
        for d in docs:
            try:
                chef_emp = frappe.db.get_value("Employee", d.employee, "reports_to")
                if not chef_emp: continue
                chef_user = frappe.db.get_value("Employee", chef_emp, "user_id")
                if chef_user:
                    frappe.db.set_value(dt, d.name, "report_to_user", chef_user, update_modified=False)
                    cnt += 1
            except Exception: pass
        print(f"  {dt}: {cnt}/{len(docs)} doc(s) renseignes")
    frappe.db.commit()
    
    print("\n=== PHASE D: Update notifications 'En attente Chef' ===")
    rows = frappe.db.sql("""
        UPDATE `tabNotification Recipient` r
        JOIN `tabNotification` n ON n.name = r.parent
        SET r.receiver_by_document_field = 'report_to_user'
        WHERE n.name LIKE 'KYA%'
          AND n.name LIKE '%En attente Chef%'
          AND r.receiver_by_document_field = 'report_to'
          AND n.document_type IN ('Demande Achat KYA','Permission Sortie Employe','Permission Sortie Stagiaire','Planning Conge')
    """)
    affected = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    print(f"  Notifications mises a jour: {affected}")
    frappe.db.commit()
    
    # Pour Planning Conge le state Chef n'existe pas (skip),  
    # mais vérifier toutes "Chef" notifs:
    print("\n=== PHASE E: Verification ===")
    checks = frappe.db.sql("""
        SELECT n.name, n.document_type, r.receiver_by_document_field, r.receiver_by_role
        FROM `tabNotification` n JOIN `tabNotification Recipient` r ON r.parent=n.name
        WHERE n.name LIKE 'KYA%' ORDER BY n.document_type, n.name
    """, as_dict=1)
    for c in checks:
        rcpt = c.receiver_by_document_field or c.receiver_by_role or "?"
        print(f"  {c.name[:55]:55} -> {rcpt}")
    
    return "DONE"

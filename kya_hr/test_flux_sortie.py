import frappe
from frappe.utils import nowdate

def run():
    frappe.flags.in_test = True
    print("\n--- Starting Validation: Permission de Sortie ---\n")
    
    # 1. Ensure required test users exist
    users = [
        {'email': 'test_emp@kya.com', 'role': 'Employee', 'first_name': 'Test', 'last_name': 'Employee'},
        {'email': 'test_chef@kya.com', 'role': 'Chef Service', 'first_name': 'Test', 'last_name': 'Chef'},
        {'email': 'test_hr@kya.com', 'role': 'HR User', 'first_name': 'Test', 'last_name': 'HR'},
        {'email': 'test_guerite@kya.com', 'role': 'Guérite', 'first_name': 'Test', 'last_name': 'Gate'},
    ]
    
    for u in users:
        if not frappe.db.exists('User', u['email']):
            frappe.get_doc({
                'doctype': 'User',
                'email': u['email'],
                'first_name': u['first_name'],
                'last_name': u['last_name'],
                'roles': [{'role': u['role']}],
                'send_welcome_email': 0
            }).insert(ignore_permissions=True)
            print(f"Created Test User: {u['email']} as {u['role']}")
            
    frappe.db.commit()

    # 2. Setup Company & Employee
    company = frappe.db.get_value('Company', None, 'name') or 'KYA-Energy'
    emp_doc = None
    existing_emp = frappe.db.get_all('Employee', filters={'user_id': 'test_emp@kya.com'})
    if not existing_emp:
        emp_doc = frappe.get_doc({
            'doctype': 'Employee',
            'first_name': 'Test',
            'user_id': 'test_emp@kya.com',
            'company': company,
            'status': 'Active',
            'date_of_joining': nowdate(),
            'gender': 'Male',
            'date_of_birth': '1990-01-01'
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    else:
        emp_doc = frappe.get_doc('Employee', existing_emp[0].name)
    
    print(f"Employee setup complete: {emp_doc.name}")

    # 3. Look for the Permission DocType
    doctypes_found = frappe.db.get_all("DocType", filters={"name": ("like", "%Permission%")}, pluck="name")
    print(f"DocTypes related to Permission Found: {doctypes_found}")
    
    # Check Leave Application or Permission Sortie Stagiaire if it's the only one found.
    # The scenario test_flux_sortie.md mentions standard 'Permission de Sortie' for Employee.
    # In HRMS, this is 'Leave Application'. 
    
    print("\n--- Validation Prep Completed ---")
    
if __name__ == '__main__':
    run()

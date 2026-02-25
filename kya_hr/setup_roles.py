import frappe

def execute():
    roles = ["Responsable Stage", "Chef de Service", "DGA", "DG"]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role,
                "desk_access": 1
            }).insert()
            print(f"Role {role} created")
        else:
            print(f"Role {role} already exists")
    
    frappe.db.commit()

if __name__ == "__main__":
    execute()

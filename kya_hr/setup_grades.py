import frappe

def create_employee_grades():
    grades = [
        # Agents d'exécution (AE)
        {"name": "AE-A", "employee_grade_name": "Agents d'exécution (A)"},
        {"name": "AE-B", "employee_grade_name": "Agents d'exécution (B)"},
        {"name": "AE-C", "employee_grade_name": "Agents d'exécution (C)"},
        {"name": "AE-D", "employee_grade_name": "Agents d'exécution (D)"},
        # Agents de maîtrise (AM)
        {"name": "AM-E", "employee_grade_name": "Agents de maîtrise (E)"},
        {"name": "AM-F", "employee_grade_name": "Agents de maîtrise (F)"},
        {"name": "AM-G", "employee_grade_name": "Agents de maîtrise (G)"},
        # Cadres (C)
        {"name": "C-H", "employee_grade_name": "Cadres (H)"},
        {"name": "C-I", "employee_grade_name": "Cadres (I)"},
        {"name": "C-J", "employee_grade_name": "Cadres (J)"},
        {"name": "C-K", "employee_grade_name": "Cadres (K)"},
        {"name": "C-L", "employee_grade_name": "Cadres (L)"},
        # Hauts Cadres (HC)
        {"name": "HC-M", "employee_grade_name": "Hauts Cadres (M)"},
        {"name": "HC-N", "employee_grade_name": "Hauts Cadres (N)"},
        {"name": "HC-O", "employee_grade_name": "Hauts Cadres (O)"},
        {"name": "HC-P", "employee_grade_name": "Hauts Cadres (P)"},
    ]

    for grade_data in grades:
        if not frappe.db.exists("Employee Grade", grade_data["name"]):
            doc = frappe.get_doc({
                "doctype": "Employee Grade",
                "employee_grade_name": grade_data["employee_grade_name"],
                "name": grade_data["name"]
            })
            doc.insert()
            print(f"Created Grade: {grade_data['name']}")
        else:
            print(f"Grade {grade_data['name']} already exists.")

if __name__ == "__main__":
    create_employee_grades()
    frappe.db.commit()

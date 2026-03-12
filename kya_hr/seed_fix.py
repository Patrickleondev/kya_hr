import frappe

def run():
    frappe.conf.server_script_enabled = True

    # Fix Bilan: no workflow_state column, just set docstatus directly
    print("=== FIX BILAN ===")
    bilan_data = [
        {"email": "stagiaire1@kya-energy.com", "date_debut": "2025-03-01", "date_fin": "2025-08-31",
         "note_globale": 16,
         "evaluation": "<p><b>Points forts :</b> Excellente maîtrise des outils informatiques.</p><p><b>Recommandation :</b> Embauche recommandée.</p>"},
        {"email": "stagiaire2@kya-energy.com", "date_debut": "2025-03-01", "date_fin": "2025-08-31",
         "note_globale": 14,
         "evaluation": "<p><b>Points forts :</b> Bonne compréhension des processus comptables.</p>"},
        {"email": "stagiaire3@kya-energy.com", "date_debut": "2025-06-01", "date_fin": "2025-11-30",
         "note_globale": 12,
         "evaluation": "<p><b>Points forts :</b> Bonne aptitude technique en électronique.</p>"},
    ]

    for p in bilan_data:
        emp_id = frappe.db.get_value("Employee", {"user_id": p["email"]}, "name")
        if not emp_id:
            print(f"  Skip: no employee for {p['email']}")
            continue
        emp = frappe.get_doc("Employee", emp_id)
        # Check if bilan already exists
        if frappe.db.exists("Bilan Fin de Stage", {"employee": emp_id}):
            print(f"  Bilan already exists for {emp_id}")
            continue
        try:
            doc = frappe.get_doc({
                "doctype": "Bilan Fin de Stage",
                "employee": emp_id,
                "employee_name": emp.employee_name,
                "department": emp.department,
                "date_debut": p["date_debut"],
                "date_fin": p["date_fin"],
                "note_globale": p["note_globale"],
                "evaluation": p["evaluation"],
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            print(f"  Bilan: {doc.name}")
        except Exception as e:
            print(f"  Bilan error: {e}")
    frappe.db.commit()

    # Fix Leave Allocation: need total_leaves_allocated field
    print("\n=== FIX LEAVE ALLOCATION ===")
    company = "Demo"
    employees = frappe.get_all("Employee", filters={"company": company, "employment_type": "Full-time"}, pluck="name")
    for emp_id in employees:
        if frappe.db.exists("Leave Allocation", {"employee": emp_id, "leave_type": "Congé Annuel"}):
            print(f"  Leave alloc exists: {emp_id}")
            continue
        try:
            la = frappe.get_doc({
                "doctype": "Leave Allocation",
                "employee": emp_id,
                "leave_type": "Congé Annuel",
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "new_leaves_allocated": 22,
                "total_leaves_allocated": 22,
            })
            la.flags.ignore_permissions = True
            la.flags.ignore_validate = True
            la.flags.ignore_mandatory = True
            la.insert(ignore_permissions=True)
            frappe.db.set_value("Leave Allocation", la.name, "docstatus", 1, update_modified=False)
            print(f"  Leave allocated: {emp_id}")
        except Exception as e:
            print(f"  Leave alloc error: {e}")
    frappe.db.commit()
    print("\nDone!")

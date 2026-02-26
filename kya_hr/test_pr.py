import frappe

def test_pr():
    print("Testing KYA Purchase Request Creation and Workflow...")
    try:
        employee = frappe.get_all("Employee", limit=1)
        if employee:
            emp_name = employee[0].name
            doc = frappe.get_doc({
                "doctype": "KYA Purchase Request",
                "requester": emp_name,
                "purpose": "Test d'achat automatisé",
                "description": "Ceci est un test système du workflow d'achats.",
                "urgency": "Normale"
            })
            doc.insert(ignore_permissions=True)
            print(f"✅ Test Purchase Request created: {doc.name}")
            print(f"✅ Initial Workflow State: {doc.workflow_state}")
            
            # Test transition to see if emails would trigger
            doc.workflow_state = "En attente Validation Chef"
            doc.save(ignore_permissions=True)
            print(f"✅ Transitioned to: {doc.workflow_state}")
        else:
            print("No employee found to test.")
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_pr()


import frappe
import json

def execute():
    print("🚀 Setting up Client Scripts for Interns and Logistics...")
    
    scripts = [
        {
            "name": "KYA Permission Request Validation",
            "dt": "KYA Permission Request",
            "script": """
frappe.ui.form.on('KYA Permission Request', {
    validate: function(frm) {
        if (frm.doc.from_date && frm.doc.to_date) {
            if (frm.doc.from_date > frm.doc.to_date) {
                frappe.msgprint(__('La date de fin ne peut pas être antérieure à la date de début.'));
                frappe.validated = false;
            }
        }
        
        if (frm.doc.permission_type !== 'Absence') {
            if (frm.doc.from_time && frm.doc.to_time) {
                if (frm.doc.from_time >= frm.doc.to_time) {
                    frappe.msgprint(__('L\\'heure de fin doit être postérieure à l\\'heure de début.'));
                    frappe.validated = false;
                }
            }
        }
    }
});
"""
        },
        {
            "name": "KYA Exit Ticket Logic",
            "dt": "KYA Exit Ticket",
            "script": """
frappe.ui.form.on('KYA Exit Ticket', {
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            // Optionnel: pre-remplir l'employé
        }
    },
    validate: function(frm) {
        if (!frm.doc.passengers || frm.doc.passengers.length === 0) {
            frappe.msgprint(__('Veuillez ajouter au moins un passager (ou vous-même).'));
            frappe.validated = false;
        }
    }
});
"""
        },
        {
            "name": "KYA Fuel Log Validation",
            "dt": "KYA Fuel Log",
            "script": """
frappe.ui.form.on('KYA Fuel Log', {
    validate: function(frm) {
        if (frm.doc.odometer <= 0) {
            frappe.msgprint(__('Le kilométrage doit être positif.'));
            frappe.validated = false;
        }
    }
});
"""
        }
    ]

    for s in scripts:
        if not frappe.db.exists("Client Script", {"name": s["name"]}):
            frappe.get_doc({
                "doctype": "Client Script",
                "name": s["name"],
                "dt": s["dt"],
                "script": s["script"],
                "enabled": 1
            }).insert()
            print(f"Created Client Script: {s['name']}")
        else:
            frappe.db.set_value("Client Script", s["name"], "script", s["script"])
            print(f"Updated Client Script: {s['name']}")

    frappe.db.commit()
    print("✅ Client Scripts Setup Complete!")

if __name__ == "__main__":
    execute()

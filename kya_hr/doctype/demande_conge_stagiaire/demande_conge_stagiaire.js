frappe.ui.form.on("Demande Conge Stagiaire", {
    refresh(frm) {
        if (frm.is_new() && frappe.session.user !== "Guest") {
            // Auto-set employee from logged-in user
            frappe.db.get_value("Employee", { "user_id": frappe.session.user }, ["name", "employee_name"])
                .then(r => {
                    if (r && r.message && r.message.name) {
                        frm.set_value("employee", r.message.name);
                    }
                });
        }
    },

    employee(frm) {
        if (frm.doc.employee) {
            frm.set_value("signataire_stagiaire", frm.doc.employee_name || "");
            frm.set_value("date_signature_stagiaire", frappe.datetime.get_today());
        }
    },

    date_debut(frm) { calculate_jours(frm); },
    date_fin(frm)   { calculate_jours(frm); },
});

function calculate_jours(frm) {
    if (frm.doc.date_debut && frm.doc.date_fin) {
        const nb = frappe.datetime.get_day_diff(frm.doc.date_fin, frm.doc.date_debut) + 1;
        if (nb < 1) {
            frappe.msgprint(__("La date de fin doit être postérieure à la date de début."));
            frm.set_value("nombre_jours", 0);
        } else {
            frm.set_value("nombre_jours", nb);
        }
    }
}

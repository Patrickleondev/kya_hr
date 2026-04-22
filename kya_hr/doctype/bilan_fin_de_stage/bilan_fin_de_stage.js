// Bilan Fin de Stage - Client Script
frappe.ui.form.on("Bilan Fin de Stage", {
    refresh: function(frm) {
        // Status indicator
        if (frm.doc.statut === "Validé") {
            frm.page.set_indicator("Validé", "green");
        } else if (frm.doc.statut === "Soumis") {
            frm.page.set_indicator("Soumis", "blue");
        }

        // PDF button for validated bilans
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Télécharger PDF"), function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=Bilan de Stage KYA"
                    )
                );
            }, __("Actions"));
        }
    },

    note_globale: function(frm) {
        // Auto-calculate mention
        var note = frm.doc.note_globale;
        if (note !== null && note !== undefined) {
            var mention = "";
            if (note < 8) mention = "Insuffisant";
            else if (note < 10) mention = "Passable";
            else if (note < 12) mention = "Assez Bien";
            else if (note < 16) mention = "Bien";
            else mention = "Très Bien";
            frm.set_value("mention", mention);
        }
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee,
                ["employee_name", "department", "date_of_joining"],
                function(r) {
                    if (r) {
                        frm.set_value("employee_name", r.employee_name);
                        frm.set_value("department", r.department);
                        if (r.date_of_joining) {
                            frm.set_value("date_debut", r.date_of_joining);
                        }
                    }
                }
            );
        }
    }
});

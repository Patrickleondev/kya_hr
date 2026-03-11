// Permission Sortie Employé – Client Script
frappe.ui.form.on("Permission Sortie Employe", {
    refresh: function(frm) {
        // Color-coded status indicator
        var colors = {
            "Approuvé": "green",
            "Rejeté": "red",
            "Brouillon": "darkgrey"
        };
        if (frm.doc.statut) {
            var color = colors[frm.doc.statut] || "orange";
            frm.page.set_indicator(frm.doc.statut, color);
        }

        // Control signature field access
        _control_pse_signatures(frm);

        // Print ticket for approved permissions
        if (frm.doc.docstatus === 1 && frm.doc.statut === "Approuvé") {
            frm.add_custom_button(__("Imprimer Ticket"), function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=Ticket Sortie Employé"
                    )
                );
            });
        }
    },

    onload: function(frm) {
        // Auto-fill employee on new form
        if (frm.is_new() && !frm.doc.employee) {
            frappe.db.get_value("Employee", {"user_id": frappe.session.user},
                ["name", "employee_name", "department", "designation"],
                function(r) {
                    if (r && r.name) {
                        frm.set_value("employee", r.name);
                        frm.set_value("employee_name", r.employee_name);
                        frm.set_value("department", r.department);
                        frm.set_value("designation", r.designation);
                    }
                }
            );
        }
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee,
                ["employee_name", "department", "company", "designation", "employment_type"],
                function(r) {
                    if (r) {
                        frm.set_value("employee_name", r.employee_name);
                        frm.set_value("department", r.department);
                        frm.set_value("company", r.company);
                        frm.set_value("designation", r.designation);
                        if (r.employment_type && r.employment_type === "Stage") {
                            frappe.msgprint({
                                title: __("Attention"),
                                indicator: "orange",
                                message: __("Cet employé est un stagiaire. Utilisez le module Permission de Sortie Stagiaire.")
                            });
                        }
                    }
                }
            );
        }
    },

    heure_depart: function(frm) { _calc_duree_pse(frm); },
    heure_retour: function(frm) { _calc_duree_pse(frm); }
});

function _calc_duree_pse(frm) {
    if (frm.doc.heure_depart && frm.doc.heure_retour) {
        var dep = moment(frm.doc.heure_depart, "HH:mm:ss");
        var ret = moment(frm.doc.heure_retour, "HH:mm:ss");
        if (ret.isAfter(dep)) {
            var diff = moment.duration(ret.diff(dep));
            var h = Math.floor(diff.asHours());
            var m = diff.minutes();
            frm.set_value("duree", h + "h " + (m < 10 ? "0" : "") + m + "min");
        }
    }
}

function _control_pse_signatures(frm) {
    var ws = frm.doc.workflow_state || frm.doc.statut;
    var roles = frappe.user_roles || [];

    // Employé signature: editable at Brouillon for owner / Employee
    var can_sign_employe = (ws === "Brouillon")
        && (roles.includes("Employee") || frappe.session.user === frm.doc.owner);
    frm.set_df_property("signature_employe", "read_only", can_sign_employe ? 0 : 1);
    frm.set_df_property("signataire_employe", "read_only", 1);
    frm.set_df_property("date_signature_employe", "read_only", 1);

    // Chef signature: editable at "En attente Chef" for HR User
    var can_sign_chef = ws === "En attente Chef" && roles.includes("HR User");
    frm.set_df_property("signature_chef", "read_only", can_sign_chef ? 0 : 1);
    frm.set_df_property("signataire_chef", "read_only", 1);
    frm.set_df_property("date_signature_chef", "read_only", 1);

    // RH signature: editable at "En attente RH" for HR Manager
    var can_sign_rh = ws === "En attente RH" && roles.includes("HR Manager");
    frm.set_df_property("signature_rh", "read_only", can_sign_rh ? 0 : 1);
    frm.set_df_property("signataire_rh", "read_only", 1);
    frm.set_df_property("date_signature_rh", "read_only", 1);
}

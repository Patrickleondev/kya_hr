// PV Sortie Materiel - Client Script
frappe.ui.form.on("PV Sortie Materiel", {
    refresh: function(frm) {
        // Color-coded status
        var colors = {
            "Approuvé": "green",
            "Rejeté": "red",
            "Brouillon": "darkgrey"
        };
        if (frm.doc.statut) {
            var color = colors[frm.doc.statut] || "orange";
            frm.page.set_indicator(frm.doc.statut, color);
        }

        // Control signature field access based on workflow state and role
        _control_pv_signatures(frm);

        // Print buttons for approved PV
        if (frm.doc.docstatus === 1 && frm.doc.statut === "Approuvé") {
            frm.add_custom_button(__("Ticket de Sortie"), function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=Ticket Sortie Matériel"
                    )
                );
            }, __("Imprimer"));

            frm.add_custom_button(__("PV Officiel"), function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=PV Sortie Matériel Officiel"
                    )
                );
            }, __("Imprimer"));
        }
    },

    onload: function(frm) {
        // Auto-fill demandeur from logged-in employee
        if (frm.is_new() && !frm.doc.demandeur_nom) {
            frappe.db.get_value("Employee", {"user_id": frappe.session.user},
                "employee_name", function(r) {
                    if (r && r.employee_name) {
                        frm.set_value("demandeur_nom", r.employee_name);
                        frm.set_value("demandeur_date", frappe.datetime.get_today());
                    }
                }
            );
        }
    }
});

function _control_pv_signatures(frm) {
    var ws = frm.doc.workflow_state || frm.doc.statut;
    var roles = frappe.user_roles || [];

    // Demandeur signature: editable only for Employee at Brouillon or En attente Chef
    var can_sign_demandeur = (ws === "Brouillon" || ws === "En attente Chef")
        && roles.includes("Employee");
    frm.set_df_property("signature_demandeur", "read_only", can_sign_demandeur ? 0 : 1);

    // Magasin signature: editable only for Stock User at En attente Magasin
    var can_sign_magasin = ws === "En attente Magasin" && roles.includes("Stock User");
    frm.set_df_property("signature_magasin", "read_only", can_sign_magasin ? 0 : 1);
    frm.set_df_property("magasin_nom", "read_only", 1);
    frm.set_df_property("magasin_date", "read_only", 1);

    // Audit signature: editable only for Auditor at En attente Audit
    var can_sign_audit = ws === "En attente Audit" && roles.includes("Auditor");
    frm.set_df_property("signature_audit", "read_only", can_sign_audit ? 0 : 1);
    frm.set_df_property("audit_nom", "read_only", 1);
    frm.set_df_property("audit_date", "read_only", 1);

    // DGA signature: editable only for Stock Manager at En attente DGA
    var can_sign_dga = ws === "En attente DGA" && roles.includes("Stock Manager");
    frm.set_df_property("signature_dga", "read_only", can_sign_dga ? 0 : 1);
    frm.set_df_property("dga_nom", "read_only", 1);
    frm.set_df_property("dga_date", "read_only", 1);
}

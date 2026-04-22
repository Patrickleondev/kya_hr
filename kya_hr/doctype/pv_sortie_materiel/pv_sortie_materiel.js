// PV Sortie Matériel – Script Client
frappe.ui.form.on("PV Sortie Materiel", {
    refresh: function(frm) {
        // Indicateur de statut coloré
        var couleurs = {
            "Approuvé": "green",
            "Rejeté": "red",
            "Brouillon": "darkgrey"
        };
        if (frm.doc.statut) {
            var couleur = couleurs[frm.doc.statut] || "orange";
            frm.page.set_indicator(frm.doc.statut, couleur);
        }

        // Contrôle des champs signature selon état et rôle
        _control_pv_signatures(frm);

        // Boutons impression pour PV approuvé
        if (frm.doc.docstatus === 1 && frm.doc.statut === "Approuvé") {
            frm.add_custom_button("Ticket de Sortie", function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=Ticket Sortie Matériel"
                    )
                );
            }, "Imprimer");

            frm.add_custom_button("PV Officiel", function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=PV Sortie Matériel Officiel"
                    )
                );
            }, "Imprimer");
        }
    },

    onload: function(frm) {
        // Remplissage automatique du demandeur connecté
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

    // Signature demandeur : modifiable au Brouillon ou En attente Chef
    var peut_signer_demandeur = (ws === "Brouillon" || ws === "En attente Chef")
        && roles.includes("Employee");
    frm.set_df_property("signature_demandeur", "read_only", peut_signer_demandeur ? 0 : 1);

    // Signature Magasin : modifiable à "En attente Magasin" pour Stock User
    var peut_signer_magasin = ws === "En attente Magasin" && roles.includes("Stock User");
    frm.set_df_property("signature_magasin", "read_only", peut_signer_magasin ? 0 : 1);
    frm.set_df_property("magasin_nom", "read_only", 1);
    frm.set_df_property("magasin_date", "read_only", 1);

    // Signature Audit : modifiable à "En attente Audit" pour Auditor
    var peut_signer_audit = ws === "En attente Audit" && roles.includes("Auditor");
    frm.set_df_property("signature_audit", "read_only", peut_signer_audit ? 0 : 1);
    frm.set_df_property("audit_nom", "read_only", 1);
    frm.set_df_property("audit_date", "read_only", 1);

    // Signature DGA : modifiable à "En attente DGA" pour Stock Manager
    var peut_signer_dga = ws === "En attente DGA" && roles.includes("Stock Manager");
    frm.set_df_property("signature_dga", "read_only", peut_signer_dga ? 0 : 1);
    frm.set_df_property("dga_nom", "read_only", 1);
    frm.set_df_property("dga_date", "read_only", 1);
}

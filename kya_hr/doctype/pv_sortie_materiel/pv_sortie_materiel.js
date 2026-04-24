// PV Sortie MatÃ©riel â€“ Script Client
frappe.ui.form.on("PV Sortie Materiel", {
    refresh: function(frm) {
        // Indicateur de statut colorÃ©
        var couleurs = {
            "ApprouvÃ©": "green",
            "RejetÃ©": "red",
            "Brouillon": "darkgrey"
        };
        if (frm.doc.statut) {
            var couleur = couleurs[frm.doc.statut] || "orange";
            frm.page.set_indicator(frm.doc.statut, couleur);
        }

        // ContrÃ´le des champs signature selon Ã©tat et rÃ´le
        _control_pv_signatures(frm);

        // Boutons impression pour PV approuvÃ©
        if (frm.doc.docstatus === 1 && frm.doc.statut === "ApprouvÃ©") {
            frm.add_custom_button("Ticket de Sortie", function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=Ticket Sortie MatÃ©riel"
                    )
                );
            }, "Imprimer");

            frm.add_custom_button("PV Officiel", function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=PV Sortie MatÃ©riel Officiel"
                    )
                );
            }, "Imprimer");
        }
    },

    onload: function(frm) {
        // Remplissage automatique du demandeur connectÃ©
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

    // Signature Magasin : modifiable Ã  "En attente Magasin"
    var peut_signer_magasin = ws === "En attente Magasin" && (
        roles.includes("Stock User") || roles.includes("Stock Manager") ||
        roles.includes("ChargÃ© des Stocks") || roles.includes("Responsable Stock") ||
        roles.includes("System Manager")
    );
    frm.set_df_property("signature_magasin", "read_only", peut_signer_magasin ? 0 : 1);
    frm.set_df_property("magasin_nom", "read_only", 1);
    frm.set_df_property("magasin_date", "read_only", 1);

    // Signature Audit : modifiable Ã  "En attente Audit" pour Auditor
    var peut_signer_audit = ws === "En attente Audit" && roles.includes("Auditor");
    frm.set_df_property("signature_audit", "read_only", peut_signer_audit ? 0 : 1);
    frm.set_df_property("audit_nom", "read_only", 1);
    frm.set_df_property("audit_date", "read_only", 1);

    // Signature DGA : modifiable Ã  "En attente DGA" pour Stock Manager
    var peut_signer_dga = ws === "En attente DGA" && roles.includes("Stock Manager");
    frm.set_df_property("signature_dga", "read_only", peut_signer_dga ? 0 : 1);
    frm.set_df_property("dga_nom", "read_only", 1);
    frm.set_df_property("dga_date", "read_only", 1);
}

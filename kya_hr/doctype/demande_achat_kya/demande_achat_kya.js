// Demande Achat KYA – Client Script
frappe.ui.form.on("Demande Achat KYA", {
    refresh: function(frm) {
        var colors = {
            "Approuvé": "green",
            "Rejeté": "red",
            "Brouillon": "darkgrey"
        };
        if (frm.doc.statut) {
            var color = colors[frm.doc.statut] || "orange";
            frm.page.set_indicator(frm.doc.statut, color);
        }

        // Show palier info
        if (frm.doc.montant_total) {
            var m = frm.doc.montant_total;
            if (m >= 2000000) {
                frm.dashboard.set_headline(
                    __("Palier 3 : approbation Chef + DGA + DG requise"),
                    "red"
                );
            } else if (m >= 100000) {
                frm.dashboard.set_headline(
                    __("Palier 2 : approbation Chef + DGA requise"),
                    "orange"
                );
            } else {
                frm.dashboard.set_headline(
                    __("Palier 1 : approbation Chef seul"),
                    "blue"
                );
            }
        }

        // Control signature field access
        _control_da_signatures(frm);

        // Print button for approved
        if (frm.doc.docstatus === 1 && frm.doc.statut === "Approuvé") {
            frm.add_custom_button(__("Imprimer Bon de Commande"), function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=Demande Achat KYA Officiel"
                    )
                );
            });
        }
    },

    onload: function(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frappe.db.get_value("Employee", {"user_id": frappe.session.user},
                ["name", "employee_name", "department"],
                function(r) {
                    if (r && r.name) {
                        frm.set_value("employee", r.name);
                        frm.set_value("employee_name", r.employee_name);
                        frm.set_value("department", r.department);
                    }
                }
            );
        }
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee,
                ["employee_name", "department", "company"],
                function(r) {
                    if (r) {
                        frm.set_value("employee_name", r.employee_name);
                        frm.set_value("department", r.department);
                        frm.set_value("company", r.company);
                    }
                }
            );
        }
    }
});

// Child table: auto-calculate montant per row
frappe.ui.form.on("Demande Achat Item", {
    quantite: function(frm, cdt, cdn) { _calc_montant_da(frm, cdt, cdn); },
    prix_unitaire: function(frm, cdt, cdn) { _calc_montant_da(frm, cdt, cdn); },
    items_remove: function(frm) { _calc_total_da(frm); }
});

function _calc_montant_da(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "montant",
        (row.quantite || 0) * (row.prix_unitaire || 0));
    _calc_total_da(frm);
}

function _calc_total_da(frm) {
    var total = 0;
    (frm.doc.items || []).forEach(function(r) {
        total += (r.montant || 0);
    });
    frm.set_value("montant_total", total);
}

function _control_da_signatures(frm) {
    var ws = frm.doc.workflow_state || frm.doc.statut;
    var roles = frappe.user_roles || [];

    // Demandeur signature: editable at Brouillon for owner
    var can_sign_demandeur = (ws === "Brouillon")
        && (roles.includes("Employee") || frappe.session.user === frm.doc.owner);
    frm.set_df_property("signature_demandeur", "read_only", can_sign_demandeur ? 0 : 1);
    frm.set_df_property("signataire_demandeur", "read_only", 1);
    frm.set_df_property("date_signature_demandeur", "read_only", 1);

    // Chef signature: editable at "En attente Chef" for Purchase User
    var can_sign_chef = ws === "En attente Chef" && roles.includes("Purchase User");
    frm.set_df_property("signature_chef", "read_only", can_sign_chef ? 0 : 1);
    frm.set_df_property("signataire_chef", "read_only", 1);
    frm.set_df_property("date_signature_chef", "read_only", 1);

    // DGA signature: editable at "En attente Approbation" for Purchase Manager
    var can_sign_dga = ws === "En attente Approbation" && roles.includes("Purchase Manager");
    frm.set_df_property("signature_dga", "read_only", can_sign_dga ? 0 : 1);
    frm.set_df_property("signataire_dga", "read_only", 1);
    frm.set_df_property("date_signature_dga", "read_only", 1);

    // DG signature: editable at "En attente DG" for HR Manager
    var can_sign_dg = ws === "En attente DG" && roles.includes("HR Manager");
    frm.set_df_property("signature_dg", "read_only", can_sign_dg ? 0 : 1);
    frm.set_df_property("signataire_dg", "read_only", 1);
    frm.set_df_property("date_signature_dg", "read_only", 1);
}

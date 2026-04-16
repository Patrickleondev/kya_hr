// Demande d'Achat KYA – Script Client
frappe.ui.form.on("Demande Achat KYA", {
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

        // Bandeau palier d'approbation
        if (frm.doc.montant_total) {
            var m = frm.doc.montant_total;
            if (m >= 2000000) {
                frm.dashboard.set_headline(
                    "Palier 3 : Approbation Chef + DAAF + Directeur Général requise",
                    "red"
                );
            } else if (m >= 100000) {
                frm.dashboard.set_headline(
                    "Palier 2 : Approbation Chef + DAAF + Directeur Général requise",
                    "orange"
                );
            } else {
                frm.dashboard.set_headline(
                    "Palier 1 : Approbation Chef de Département + DAAF requise",
                    "blue"
                );
            }
        }

        // Contrôle des accès signatures
        _control_da_signatures(frm);

        // Bouton impression pour demande approuvée
        if (frm.doc.docstatus === 1 && frm.doc.statut === "Approuvé") {
            frm.add_custom_button("Imprimer le Bon de Commande", function() {
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
        // Remplissage automatique du demandeur connecté
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

// Tableau enfant : calcul automatique du montant par ligne
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

    // Signature demandeur : modifiable au Brouillon pour le propriétaire
    var peut_signer_demandeur = (ws === "Brouillon")
        && (roles.includes("Employee") || frappe.session.user === frm.doc.owner);
    frm.set_df_property("signature_demandeur", "read_only", peut_signer_demandeur ? 0 : 1);
    frm.set_df_property("signataire_demandeur", "read_only", 1);
    frm.set_df_property("date_signature_demandeur", "read_only", 1);

    // Signature Chef : modifiable à "En attente Chef" pour Chef Service
    var peut_signer_chef = ws === "En attente Chef" && (roles.includes("Chef Service") || roles.includes("System Manager"));
    frm.set_df_property("signature_chef", "read_only", peut_signer_chef ? 0 : 1);
    frm.set_df_property("signataire_chef", "read_only", 1);
    frm.set_df_property("date_signature_chef", "read_only", 1);

    // Signature DAAF : modifiable à "En attente DAAF"
    var peut_signer_dga = ws === "En attente DAAF"
        && (roles.includes("DAAF") || roles.includes("Responsable Achats") || roles.includes("System Manager"));
    frm.set_df_property("signature_dga", "read_only", peut_signer_dga ? 0 : 1);
    frm.set_df_property("signataire_dga", "read_only", 1);
    frm.set_df_property("date_signature_dga", "read_only", 1);

    // Signature DG : modifiable à "En attente DG" pour Direction
    var peut_signer_dg = ws === "En attente DG" && (roles.includes("Directeur Général") || roles.includes("System Manager"));
    frm.set_df_property("signature_dg", "read_only", peut_signer_dg ? 0 : 1);
    frm.set_df_property("signataire_dg", "read_only", 1);
    frm.set_df_property("date_signature_dg", "read_only", 1);
}

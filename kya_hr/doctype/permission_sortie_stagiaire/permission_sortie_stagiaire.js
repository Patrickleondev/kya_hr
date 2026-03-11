// Permission de Sortie Stagiaire – Script Client
frappe.ui.form.on("Permission Sortie Stagiaire", {
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

        // Contrôle des champs signature
        _control_pss_signatures(frm);

        // Bouton impression pour permission approuvée
        if (frm.doc.docstatus === 1 && frm.doc.statut === "Approuvé") {
            frm.add_custom_button("Imprimer le Ticket de Sortie", function() {
                window.open(
                    frappe.urllib.get_full_url(
                        "/api/method/frappe.utils.print_format.download_pdf?"
                        + "doctype=" + encodeURIComponent(frm.doc.doctype)
                        + "&name=" + encodeURIComponent(frm.doc.name)
                        + "&format=Ticket Sortie Stagiaire"
                    )
                );
            });
        }
    },

    onload: function(frm) {
        // Remplissage automatique du stagiaire connecté
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
                ["employee_name", "department", "company", "employment_type"],
                function(r) {
                    if (r) {
                        frm.set_value("employee_name", r.employee_name);
                        frm.set_value("department", r.department);
                        frm.set_value("company", r.company);
                        if (r.employment_type && r.employment_type !== "Stage") {
                            frappe.msgprint({
                                title: "Attention",
                                indicator: "orange",
                                message: "Cet employ\u00e9 n'est pas un stagiaire. Veuillez utiliser le formulaire \u00ab Permission de Sortie Employ\u00e9 \u00bb."
                            });
                        }
                    }
                }
            );
        }
    },

    heure_depart: function(frm) { _calc_duree(frm); },
    heure_retour: function(frm) { _calc_duree(frm); }
});

function _calc_duree(frm) {
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

function _control_pss_signatures(frm) {
    var ws = frm.doc.workflow_state || frm.doc.statut;
    var roles = frappe.user_roles || [];

    // Signature stagiaire : modifiable uniquement au Brouillon pour le propriétaire
    var peut_signer_stagiaire = (ws === "Brouillon")
        && (roles.includes("Employee") || frappe.session.user === frm.doc.owner);
    frm.set_df_property("signature_stagiaire", "read_only", peut_signer_stagiaire ? 0 : 1);
    frm.set_df_property("signataire_stagiaire", "read_only", 1);
    frm.set_df_property("date_signature_stagiaire", "read_only", 1);

    // Signature Chef : modifiable à "En attente Chef" pour HR User
    var peut_signer_chef = ws === "En attente Chef" && roles.includes("HR User");
    frm.set_df_property("signature_chef", "read_only", peut_signer_chef ? 0 : 1);
    frm.set_df_property("signataire_chef", "read_only", 1);
    frm.set_df_property("date_signature_chef", "read_only", 1);

    // Signature DG : modifiable à "En attente DG" pour HR Manager
    var peut_signer_dg = ws === "En attente DG" && roles.includes("HR Manager");
    frm.set_df_property("signature_dg", "read_only", peut_signer_dg ? 0 : 1);
    frm.set_df_property("signataire_dg", "read_only", 1);
    frm.set_df_property("date_signature_dg", "read_only", 1);
}

// Permission Sortie Employé – Client Script
frappe.ui.form.on("Permission Sortie Employe", {
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

        // Info bypass si Chef absent (visible pour HR Manager à l'état En attente Chef)
        var ws = frm.doc.workflow_state || frm.doc.statut;
        if (ws === "En attente Chef" && frappe.user_roles.includes("HR Manager")) {
            frm.dashboard.set_headline(
                "Le Chef de Service est absent ? Vous pouvez valider directement via le bouton « Valider (Absence Chef) ».",
                "orange"
            );
        }

        // Info bypass si DGA absent (visible pour HR Manager à l'état En attente DGA)
        if (ws === "En attente DGA" && frappe.user_roles.includes("HR Manager")) {
            frm.dashboard.set_headline(
                "Le DGA est absent ? Vous pouvez valider directement via le bouton « Valider (Absence DGA) ».",
                "orange"
            );
        }

        // Contrôle des champs signature
        _control_pse_signatures(frm);

        // Bouton impression pour permission approuvée
        if (frm.doc.docstatus === 1 && frm.doc.statut === "Approuvé") {
            frm.add_custom_button("Imprimer le Ticket de Sortie", function() {
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
        // Remplissage automatique de l'employé connecté
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
                                title: "Attention",
                                indicator: "orange",
                                message: "Cet employé est un stagiaire. Veuillez utiliser le formulaire « Permission de Sortie Stagiaire »."
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

    // Signature employé : modifiable au Brouillon pour le propriétaire
    var peut_signer_employe = (ws === "Brouillon")
        && (roles.includes("Employee") || frappe.session.user === frm.doc.owner);
    frm.set_df_property("signature_employe", "read_only", peut_signer_employe ? 0 : 1);
    frm.set_df_property("signataire_employe", "read_only", 1);
    frm.set_df_property("date_signature_employe", "read_only", 1);

    // Signature Chef : modifiable à "En attente Chef" pour HR User
    var peut_signer_chef = ws === "En attente Chef" && roles.includes("HR User");
    frm.set_df_property("signature_chef", "read_only", peut_signer_chef ? 0 : 1);
    frm.set_df_property("signataire_chef", "read_only", 1);
    frm.set_df_property("date_signature_chef", "read_only", 1);

    // Signature RH : modifiable à "En attente RH" pour HR Manager
    // OU à "En attente Chef" si bypass (absence Chef → passe directement à En attente RH)
    var peut_signer_rh = (ws === "En attente RH" || ws === "En attente Chef")
        && roles.includes("HR Manager");
    frm.set_df_property("signature_rh", "read_only", peut_signer_rh ? 0 : 1);
    frm.set_df_property("signataire_rh", "read_only", 1);
    frm.set_df_property("date_signature_rh", "read_only", 1);

    // Signature DGA : modifiable à "En attente DGA" pour HR Manager
    var peut_signer_dga = ws === "En attente DGA" && roles.includes("HR Manager");
    frm.set_df_property("signature_dga", "read_only", peut_signer_dga ? 0 : 1);
    frm.set_df_property("signataire_dga", "read_only", 1);
    frm.set_df_property("date_signature_dga", "read_only", 1);
}

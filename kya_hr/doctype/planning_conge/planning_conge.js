// Planning de Congé – Script Client
frappe.ui.form.on("Planning Conge", {
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

        // La RH peut ajouter des commentaires
        if (frappe.user_roles.includes("HR Manager") || frappe.user_roles.includes("HR User")) {
            frm.set_df_property("commentaire_rh", "read_only", 0);
        }
    },

    onload: function(frm) {
        if (frm.is_new()) {
            // Remplissage automatique de l'employé connecté
            if (!frm.doc.employee) {
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
            // Année par défaut
            if (!frm.doc.annee) {
                frm.set_value("annee", new Date().getFullYear());
            }
        }
    },

    employee: function(frm) {
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee,
                ["employee_name", "department", "company", "designation"],
                function(r) {
                    if (r) {
                        frm.set_value("employee_name", r.employee_name);
                        frm.set_value("department", r.department);
                        frm.set_value("company", r.company);
                        frm.set_value("designation", r.designation);
                    }
                }
            );
        }
    }
});

// Tableau enfant : calcul automatique du nombre de jours
frappe.ui.form.on("Planning Conge Periode", {
    date_debut: function(frm, cdt, cdn) { _calc_nb_jours(frm, cdt, cdn); },
    date_fin: function(frm, cdt, cdn) { _calc_nb_jours(frm, cdt, cdn); }
});

function _calc_nb_jours(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (row.date_debut && row.date_fin) {
        var d1 = moment(row.date_debut);
        var d2 = moment(row.date_fin);
        if (d2.isSameOrAfter(d1)) {
            frappe.model.set_value(cdt, cdn, "nb_jours", d2.diff(d1, "days") + 1);
        }
    }
    // Recalcul du total
    var total = 0;
    (frm.doc.periodes || []).forEach(function(r) {
        total += (r.nb_jours || 0);
    });
    frm.set_value("total_jours", total);
}

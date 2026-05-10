// Planning de Congé – Script Client
frappe.ui.form.on("Planning Conge", {
    refresh: function(frm) {
        var couleurs = {
            "Approuvé": "green",
            "Rejeté": "red",
            "Brouillon": "darkgrey"
        };
        if (frm.doc.statut) {
            var couleur = couleurs[frm.doc.statut] || "orange";
            frm.page.set_indicator(frm.doc.statut, couleur);
        }

        if (frappe.user_roles.includes("HR Manager") || frappe.user_roles.includes("HR User")) {
            frm.set_df_property("commentaire_rh", "read_only", 0);
        }

        _refresh_solde(frm);
    },

    onload: function(frm) {
        if (frm.is_new()) {
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
    },

    solde_n1: _refresh_solde,
    jours_acquis: _refresh_solde,
    conges_obligatoires: _refresh_solde,
    jours_monetisation: _refresh_solde,
    total_jours: _refresh_solde
});

function _refresh_solde(frm) {
    var n1 = parseFloat(frm.doc.solde_n1 || 0);
    var acquis = parseFloat(frm.doc.jours_acquis || 0);
    var oblig = parseInt(frm.doc.conges_obligatoires || 0);
    var total = parseInt(frm.doc.total_jours || 0);
    var monet = parseInt(frm.doc.jours_monetisation || 0);

    var dispo = n1 + acquis - oblig;
    var final = dispo - total - monet;

    frm.set_value("solde_disponible", dispo);
    frm.set_value("solde_final", final);

    if (final < 0) {
        frm.dashboard.set_headline_alert(
            "<span style='color:#c0392b'>⚠️ Solde final négatif (" + final.toFixed(1) +
            " j) — vous demandez plus de jours que votre solde disponible.</span>"
        );
    } else {
        frm.dashboard.clear_headline();
    }
}

// Tableau enfant : calcul automatique du nombre de jours
frappe.ui.form.on("Planning Conge Periode", {
    date_debut: function(frm, cdt, cdn) { _calc_nb_jours(frm, cdt, cdn); },
    date_fin: function(frm, cdt, cdn) { _calc_nb_jours(frm, cdt, cdn); },
    periodes_remove: _refresh_total
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
    _refresh_total(frm);
}

function _refresh_total(frm) {
    var total = 0;
    (frm.doc.periodes || []).forEach(function(r) {
        total += (r.nb_jours || 0);
    });
    frm.set_value("total_jours", total);
    _refresh_solde(frm);
}

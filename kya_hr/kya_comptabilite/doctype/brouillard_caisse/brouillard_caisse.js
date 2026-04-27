frappe.ui.form.on("Brouillard Caisse", {
    refresh(frm) {
        // Auto-remplir caissière à partir de la session (nouvelle fiche)
        if (frm.is_new() && !frm.doc.caissiere && frappe.session.user !== "Guest") {
            frappe.db.get_value("Employee", { user_id: frappe.session.user }, ["name", "employee_name", "reports_to"])
                .then(r => {
                    if (r && r.message && r.message.name) {
                        frm.set_value("caissiere", r.message.name);
                    }
                });
        }
        // Reporter le solde final du brouillard de la veille
        if (frm.is_new() && !frm.doc.solde_precedent) {
            frappe.db.get_list("Brouillard Caisse", {
                filters: { docstatus: 1 },
                fields: ["name", "date_brouillard", "solde_final"],
                order_by: "date_brouillard desc",
                limit: 1
            }).then(rows => {
                if (rows && rows.length) {
                    frm.set_value("solde_precedent", rows[0].solde_final);
                    frm.set_value("date_solde_precedent", rows[0].date_brouillard);
                }
            });
        }
    },

    caissiere(frm) {
        if (frm.doc.caissiere) {
            frappe.db.get_value("Employee", frm.doc.caissiere, ["employee_name"])
                .then(r => {
                    if (r && r.message) {
                        frm.set_value("signataire_caissiere", r.message.employee_name);
                        frm.set_value("date_signature_caissiere", frappe.datetime.get_today());
                    }
                });
        }
    },

    solde_precedent(frm) { recompute(frm); },
    lignes_add(frm)      { recompute(frm); },
    lignes_remove(frm)   { recompute(frm); },
});

frappe.ui.form.on("Brouillard Caisse Ligne", {
    entree(frm)  { recompute(frm); },
    sortie(frm)  { recompute(frm); },
    lignes_move(frm) { recompute(frm); },
});

function recompute(frm) {
    let solde = flt(frm.doc.solde_precedent || 0);
    let te = 0, ts = 0;
    (frm.doc.lignes || []).forEach(l => {
        solde += flt(l.entree || 0) - flt(l.sortie || 0);
        frappe.model.set_value(l.doctype, l.name, "solde", solde);
        te += flt(l.entree || 0);
        ts += flt(l.sortie || 0);
    });
    frm.set_value("total_entrees", te);
    frm.set_value("total_sorties", ts);
    frm.set_value("solde_final", flt(frm.doc.solde_precedent || 0) + te - ts);
    frm.refresh_field("lignes");
}

function flt(v) { return parseFloat(v) || 0; }

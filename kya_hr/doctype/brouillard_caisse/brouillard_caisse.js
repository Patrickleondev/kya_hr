// Client Script — Brouillard Caisse (Desk)
// Gestion des signatures, calculs automatiques, bouton web form

frappe.ui.form.on("Brouillard Caisse", {
    refresh(frm) {
        _apply_signature_visibility(frm);

        // Bouton vers web form
        if (!frm.is_new()) {
            frm.add_custom_button(__("Ouvrir Web Form"), () => {
                window.open(`/brouillard-caisse/${frm.doc.name}`, "_blank");
            }, __("Actions"));
        }

        // Bouton Nouveau Brouillard (web form)
        frm.page.add_inner_button(__("Nouveau Brouillard (Web)"), () => {
            window.open("/brouillard-caisse/new", "_blank");
        });
    },

    caissiere(frm) {
        if (frm.doc.caissiere && !frm.doc.signataire_caissiere) {
            frappe.db.get_value("Employee", frm.doc.caissiere, ["employee_name"])
                .then(r => {
                    if (r && r.message) {
                        frm.set_value("signataire_caissiere", r.message.employee_name);
                        frm.set_value("date_signature_caissiere", frappe.datetime.get_today());
                    }
                });
        }
    },

    workflow_state(frm) {
        _apply_signature_visibility(frm);
        _auto_sign_by_state(frm);
    },

    solde_precedent(frm) {
        _recompute(frm);
    },
});

frappe.ui.form.on("Brouillard Caisse Ligne", {
    entree(frm) { _recompute(frm); },
    sortie(frm)  { _recompute(frm); },
    lignes_add(frm) { _recompute(frm); },
    lignes_remove(frm) { _recompute(frm); },
});

function _recompute(frm) {
    const lignes = frm.doc.lignes || [];
    let solde = flt(frm.doc.solde_precedent || 0);
    let te = 0, ts = 0;
    lignes.forEach(l => {
        const e = flt(l.entree || 0);
        const s = flt(l.sortie || 0);
        te += e; ts += s;
        solde += e - s;
        frappe.model.set_value(l.doctype, l.name, "solde", solde);
    });
    frm.set_value("total_entrees", te);
    frm.set_value("total_sorties", ts);
    frm.set_value("solde_final", flt(frm.doc.solde_precedent || 0) + te - ts);
}

function _apply_signature_visibility(frm) {
    const roles = frappe.user_roles || [];
    const state = frm.doc.workflow_state || "Brouillon";
    const isAdmin = roles.includes("Accounts Manager") || roles.includes("System Manager");
    const isComptable = roles.includes("Comptable");
    const isDFC = roles.includes("DFC");

    // Signature comptable : éditable seulement pour Comptable/Admin quand En attente Comptable
    const comptable_editable = isAdmin || (isComptable && state === "En attente Comptable");
    frm.set_df_property("signature_comptable", "read_only", comptable_editable ? 0 : 1);
    frm.set_df_property("signataire_comptable", "read_only", 1);
    frm.set_df_property("date_signature_comptable", "read_only", 1);

    // Signature DFC : éditable seulement pour DFC/Admin quand En attente DFC
    const dfc_editable = isAdmin || (isDFC && state === "En attente DFC");
    frm.set_df_property("signature_dfc", "read_only", dfc_editable ? 0 : 1);
    frm.set_df_property("signataire_dfc", "read_only", 1);
    frm.set_df_property("date_signature_dfc", "read_only", 1);
}

function _auto_sign_by_state(frm) {
    const roles = frappe.user_roles || [];
    const state = frm.doc.workflow_state || "Brouillon";

    if (roles.includes("Comptable") && state === "En attente Comptable" && !frm.doc.signataire_comptable) {
        frappe.db.get_value("Employee", { user_id: frappe.session.user }, ["employee_name"])
            .then(r => {
                if (r && r.message) {
                    frm.set_value("signataire_comptable", r.message.employee_name);
                    frm.set_value("date_signature_comptable", frappe.datetime.get_today());
                }
            });
    }

    if (roles.includes("DFC") && state === "En attente DFC" && !frm.doc.signataire_dfc) {
        frappe.db.get_value("Employee", { user_id: frappe.session.user }, ["employee_name"])
            .then(r => {
                if (r && r.message) {
                    frm.set_value("signataire_dfc", r.message.employee_name);
                    frm.set_value("date_signature_dfc", frappe.datetime.get_today());
                }
            });
    }
}

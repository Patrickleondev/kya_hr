// Copyright (c) 2026, KYA-Energy Group and contributors
frappe.ui.form.on("Sortie Vehicule", {
    refresh(frm) {
        // Indicateur de statut coloré
        const palette = {
            "Brouillon": "gray",
            "Approuvée": "blue",
            "En mission": "orange",
            "Retour confirmé": "green",
            "Annulée": "red",
        };
        if (frm.doc.statut && palette[frm.doc.statut]) {
            frm.dashboard.set_headline_alert(
                `<span class="indicator ${palette[frm.doc.statut]}">${frm.doc.statut}</span>`
            );
        }
        // Bouton "Confirmer le retour" rapide quand en mission
        if (!frm.is_new() && frm.doc.docstatus === 1 && frm.doc.statut === "En mission") {
            frm.add_custom_button(__("Confirmer le retour"), () => {
                frappe.prompt([
                    { fieldname: "km_retour", fieldtype: "Int", label: "Km au retour", reqd: 1 },
                    { fieldname: "carburant_retour_pourcent", fieldtype: "Percent", label: "Carburant retour (%)" },
                    { fieldname: "observations", fieldtype: "Small Text", label: "Observations" }
                ], (values) => {
                    frm.set_value("km_retour", values.km_retour);
                    if (values.carburant_retour_pourcent != null)
                        frm.set_value("carburant_retour_pourcent", values.carburant_retour_pourcent);
                    if (values.observations)
                        frm.set_value("observations", values.observations);
                    frm.set_value("workflow_state", "Retour confirmé");
                    frm.save("Update");
                }, __("Confirmation de retour"), __("Valider"));
            }, __("Actions"));
        }
    },
    vehicle(frm) {
        if (frm.doc.vehicle) {
            frappe.db.get_value("Vehicle", frm.doc.vehicle, ["make", "model"]).then(r => {
                if (r.message) {
                    frm.set_value(
                        "vehicle_make_model",
                        `${r.message.make || ""} ${r.message.model || ""}`.trim()
                    );
                }
            });
        }
    },
    km_depart(frm) { compute_km(frm); },
    km_retour(frm) { compute_km(frm); },
});

function compute_km(frm) {
    if (frm.doc.km_depart && frm.doc.km_retour && frm.doc.km_retour >= frm.doc.km_depart) {
        frm.set_value("km_parcourus", frm.doc.km_retour - frm.doc.km_depart);
    }
}

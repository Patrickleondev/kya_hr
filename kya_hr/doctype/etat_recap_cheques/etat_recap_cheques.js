frappe.ui.form.on("Etat Recap Cheques", {
    refresh(frm) {
        if (frm.is_new() && !frm.doc.redacteur && frappe.session.user !== "Guest") {
            frappe.db.get_value("Employee", { user_id: frappe.session.user }, ["name", "employee_name"])
                .then(r => {
                    if (r && r.message && r.message.name) {
                        frm.set_value("redacteur", r.message.name);
                    }
                });
        }
        // Par défaut: semaine courante (lundi → vendredi)
        if (frm.is_new() && !frm.doc.semaine_du) {
            const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
            const dow = today.getDay() || 7; // 1=lundi, 7=dimanche
            const monday = new Date(today);
            monday.setDate(today.getDate() - (dow - 1));
            const friday = new Date(monday);
            friday.setDate(monday.getDate() + 4);
            frm.set_value("semaine_du", frappe.datetime.obj_to_str(monday).slice(0, 10));
            frm.set_value("semaine_au", frappe.datetime.obj_to_str(friday).slice(0, 10));
        }
    },

    redacteur(frm) {
        if (frm.doc.redacteur) {
            frappe.db.get_value("Employee", frm.doc.redacteur, ["employee_name"])
                .then(r => {
                    if (r && r.message) {
                        frm.set_value("signataire_redacteur", r.message.employee_name);
                        frm.set_value("date_signature_redacteur", frappe.datetime.get_today());
                    }
                });
        }
    },

    lignes_add(frm)    { recompute_erc(frm); },
    lignes_remove(frm) { recompute_erc(frm); },
});

frappe.ui.form.on("Etat Recap Cheques Ligne", {
    montant(frm) { recompute_erc(frm); },
});

function recompute_erc(frm) {
    let t = 0;
    (frm.doc.lignes || []).forEach(l => { t += parseFloat(l.montant || 0); });
    frm.set_value("total_montant", t);
    frm.set_value("nombre_cheques", (frm.doc.lignes || []).length);
}

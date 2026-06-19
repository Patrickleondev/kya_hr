// Planning Conge Equipe — aide à la saisie depuis le Desk (RH / chef)
frappe.ui.form.on("Planning Conge Equipe", {
    refresh(frm) {
        if (frm.doc.equipe && frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Charger les membres de l'équipe"), () => charger_membres(frm));
        }
    },
    equipe(frm) {
        if (frm.doc.equipe && !frm.doc.annee) {
            frm.set_value("annee", new Date().getFullYear());
        }
    },
});

function charger_membres(frm) {
    frappe.call({
        method: "kya_hr.api.planning_equipe.get_membres_equipe",
        args: { equipe: frm.doc.equipe },
        callback(r) {
            const membres = (r.message && r.message.membres) || [];
            if (!membres.length) {
                frappe.msgprint(__("Aucun membre actif trouvé pour cette équipe."));
                return;
            }
            const existants = new Set((frm.doc.lignes || []).map((l) => l.employee));
            let added = 0;
            membres.forEach((m) => {
                if (existants.has(m.name)) return;
                const row = frm.add_child("lignes");
                row.employee = m.name;
                row.employee_name = m.employee_name;
                row.type_conge = "Congé Annuel";
                added++;
            });
            frm.refresh_field("lignes");
            frappe.show_alert({ message: __("{0} membre(s) ajouté(s)", [added]), indicator: "green" });
        },
    });
}

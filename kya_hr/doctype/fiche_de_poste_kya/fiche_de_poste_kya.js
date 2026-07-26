// Fiche de Poste KYA — Client Script (Desk)
// 1) Auto-remplissage depuis la fiche employé.
// 2) Édition partagée : le chef d'équipe (non-RH) ne modifie que les attributions
//    et les compétences clés ; la RH a la main sur tout.
frappe.ui.form.on('Fiche de Poste KYA', {
    refresh(frm) {
        apply_edit_scope(frm);
        if (!frm.is_new()) {
            frm.add_custom_button(__('Aperçu / Imprimer'), () => {
                window.open(
                    `/printview?doctype=${encodeURIComponent('Fiche de Poste KYA')}` +
                    `&name=${encodeURIComponent(frm.doc.name)}` +
                    `&format=${encodeURIComponent('Fiche de Poste KYA')}&no_letterhead=1&_lang=fr`,
                    '_blank');
            });
            frm.add_custom_button(__('Télécharger PDF'), () => {
                window.open(
                    `/api/method/kya_hr.api.print_format.download_pdf` +
                    `?doctype=${encodeURIComponent('Fiche de Poste KYA')}` +
                    `&name=${encodeURIComponent(frm.doc.name)}` +
                    `&format=${encodeURIComponent('Fiche de Poste KYA')}&language=fr`,
                    '_blank');
            });
        }
    },
    employee(frm) {
        if (!frm.doc.employee) return;
        frappe.db.get_value('Employee', frm.doc.employee,
            ['employee_name', 'designation', 'department', 'reports_to']).then(r => {
            const m = r.message || {};
            if (m.employee_name) frm.set_value('employee_name', m.employee_name);
            if (!frm.doc.intitule_poste && m.designation) frm.set_value('intitule_poste', m.designation);
            if (!frm.doc.departement && m.department) frm.set_value('departement', m.department);
            if (!frm.doc.superieur_hierarchique && m.reports_to) {
                frappe.db.get_value('Employee', m.reports_to, 'employee_name').then(rr => {
                    frm.set_value('superieur_hierarchique', (rr.message || {}).employee_name || '');
                });
            }
        });
    }
});

// Champs éditables par le chef ; tout le reste est en lecture seule pour lui.
const CHEF_FIELDS = ['attributions', 'competences_cle'];

function apply_edit_scope(frm) {
    const roles = frappe.user_roles || [];
    const is_rh = roles.some(r => ['Responsable RH', 'HR Manager', 'HR User',
        'System Manager', 'Directeur Général', 'DGA'].includes(r));
    if (is_rh) return; // la RH garde la main sur tout
    // Chef d'équipe (non-RH) : on grise tout sauf sa zone.
    (frm.meta.fields || []).forEach(df => {
        if (['Section Break', 'Column Break'].includes(df.fieldtype)) return;
        if (CHEF_FIELDS.includes(df.fieldname)) return;
        frm.set_df_property(df.fieldname, 'read_only', 1);
    });
    frm.dashboard.set_headline(
        __("Chef d'équipe : vous renseignez les <b>attributions/tâches</b> et les <b>compétences clés</b>. Le reste est géré par la RH."));
}

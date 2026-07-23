// Avenant Contrat KYA — Client Script (Desk)
// Même expérience que KYA Contrat : préparation dans le Desk RH + aperçu intégré.
frappe.ui.form.on('Avenant Contrat KYA', {
    refresh(frm) {
        force_avenant_sidebar();
        render_avenant_preview(frm);

        // Bouton : générer le corps fidèle au modèle (VU + préambule + articles)
        if (!frm.is_new()) {
            frm.add_custom_button(__('Générer le corps (modèle)'), () => {
                frappe.confirm(
                    __('Générer les articles fidèles au modèle KYA à partir des éléments saisis ? Cela remplace les articles actuels.'),
                    () => {
                        frappe.call({
                            method: 'kya_hr.kya_hr.doctype.avenant_contrat_kya.avenant_contrat_kya.generer_corps_doc',
                            args: { name: frm.doc.name, force: 1 },
                            freeze: true, freeze_message: __('Génération…'),
                            callback: (r) => {
                                if (!r.exc) { frappe.show_alert({ message: __('Corps généré'), indicator: 'green' }); frm.reload_doc(); }
                            }
                        });
                    }
                );
            }, __('Document'));

            frm.add_custom_button(__('Aperçu / Imprimer'), () => {
                window.open(preview_url(frm), '_blank');
            }, __('Document'));

            frm.add_custom_button(__('Télécharger PDF'), () => {
                window.open(pdf_url(frm), '_blank');
            }, __('Document'));
        }

        if (frm.is_new()) {
            frm.dashboard.set_headline(
                __('Renseignez les éléments (fonction, lieu, montants…), enregistrez, puis « Générer le corps (modèle) ». L\'aperçu s\'affiche ci-dessous, comme le contrat sera imprimé.'));
        }
    },

    employee(frm) {
        // civilité auto (accord en genre) si vide
        if (frm.doc.employee && !frm.doc.civilite) {
            frappe.db.get_value('Employee', frm.doc.employee, 'gender').then(r => {
                if (r.message) frm.set_value('civilite', r.message.gender === 'Female' ? 'Mme' : 'M.');
            });
        }
    }
});

function preview_url(frm) {
    return `/printview?doctype=${encodeURIComponent('Avenant Contrat KYA')}` +
        `&name=${encodeURIComponent(frm.doc.name)}` +
        `&format=${encodeURIComponent('Avenant Contrat KYA')}` +
        `&no_letterhead=1&trigger_print=0&_lang=fr`;
}
function pdf_url(frm) {
    return `/api/method/kya_hr.api.print_format.download_pdf` +
        `?doctype=${encodeURIComponent('Avenant Contrat KYA')}` +
        `&name=${encodeURIComponent(frm.doc.name)}` +
        `&format=${encodeURIComponent('Avenant Contrat KYA')}&language=fr`;
}

function render_avenant_preview(frm) {
    if (!frm.fields_dict.contract_preview) return;
    if (frm.is_new()) {
        frm.set_df_property('contract_preview', 'options',
            `<div style="border:1px solid #e5e7eb;border-radius:8px;padding:14px 16px;background:#fff8e7;color:#6b4300;">
                <b>Avenant en préparation</b><br>Enregistrez l'avenant pour afficher ici le document complet (en-tête KYA, VU, articles, signatures).
            </div>`);
        return;
    }
    frm.set_df_property('contract_preview', 'options',
        `<div style="border:1px solid #d9dee3;border-radius:8px;overflow:hidden;background:#fff;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 12px;background:#f7f9fb;border-bottom:1px solid #d9dee3;">
                <div style="font-weight:600;color:#1f2937;">Aperçu de l'avenant généré</div>
                <div style="display:flex;gap:8px;">
                    <a class="btn btn-xs btn-default" href="${preview_url(frm)}" target="_blank">Pleine page</a>
                    <a class="btn btn-xs btn-primary" href="${pdf_url(frm)}" target="_blank">Télécharger PDF</a>
                </div>
            </div>
            <iframe src="${preview_url(frm)}" style="width:100%;height:720px;border:0;background:#fff;"></iframe>
        </div>`);
}

function force_avenant_sidebar() {
    if (!frappe.app || !frappe.app.sidebar) return;
    setTimeout(() => {
        if (frappe.app.sidebar.sidebar_title !== 'Espace RH') {
            frappe.app.sidebar.setup('Espace RH');
        }
    }, 150);
}

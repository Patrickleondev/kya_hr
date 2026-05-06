// KYA Contrat - Client Script (Desk)
frappe.ui.form.on('KYA Contrat', {
    refresh(frm) {
        force_kya_contract_sidebar();

        const roles = frappe.user_roles || [];
        const is_rh = roles.includes('Responsable RH') || roles.includes('HR Manager') || roles.includes('System Manager');

        // Le Desk RH sert à préparer, relire, transmettre et archiver.
        // Les signatures se font sur le portail documentaire tokenisé (/kya-contrat).
        [
            'section_sig_employe', 'contrat_lu', 'signature_employe', 'nom_signe_employe', 'date_signature_employe',
            'mention_lu_approuve', 'mention_lu_approuve_image', 'date_mention_lu_approuve', 'signature_employe_ip',
            'section_sig_dg', 'signature_dg', 'nom_dg', 'fonction_dg', 'date_signature_dg', 'signature_dg_ip'
        ].forEach((fieldname) => {
            frm.set_df_property(fieldname, 'hidden', 1);
        });
        if (is_rh && frm.doc.workflow_state === 'Brouillon') {
            frm.dashboard.set_headline(__('Préparez le contrat ici. Le signataire le lira et le signera via le portail envoyé par email.'));
        }

        render_contract_preview(frm);

        if (!frm.is_new() && frm.doc.workflow_state === 'Brouillon') {
            frm.add_custom_button(__('Envoyer au Signataire'), () => {
                frappe.confirm(
                    __('Envoyer le lien sécurisé de signature à ') + frm.doc.employee_email + ' ?',
                    () => {
                        frappe.call({
                            method: 'kya_hr.api.kya_contracts.send_to_signataire',
                            args: { contract_id: frm.doc.name },
                            freeze: true,
                            freeze_message: __('Envoi en cours...'),
                            callback: (r) => {
                                if (!r.exc) {
                                    frappe.show_alert({ message: __('Email envoyé'), indicator: 'green' });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }

        if (frm.doc.pdf_final) {
            frm.add_custom_button(__('Télécharger PDF'), () => {
                window.open(frm.doc.pdf_final, '_blank');
            }, __('Document'));
        } else if (!frm.is_new()) {
            frm.add_custom_button(__('Télécharger PDF'), () => {
                window.open(`/api/method/kya_hr.api.kya_contracts.download_current_pdf?contract_id=${encodeURIComponent(frm.doc.name)}`, '_blank');
            }, __('Document'));
        }

        frm.add_custom_button(__('Aperçu Document'), () => {
            window.open(`/printview?doctype=KYA%20Contrat&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent((frm.doc.contract_type || '').startsWith('Stage') ? 'Contrat de Stage KYA' : 'KYA Contrat PDF')}&no_letterhead=1`, '_blank');
        }, __('Document'));

        if (!frm.is_new() && ['En attente Signature Salarié', 'Signé Salarié', 'En attente DG'].includes(frm.doc.workflow_state)) {
            frm.add_custom_button(__('Ouvrir Portail Signature'), () => {
                frappe.msgprint(__('Le portail est accessible uniquement depuis les liens sécurisés envoyés par email au signataire ou au DG.'));
            });
        }
    },

    contract_type(frm) {
        if (frm.doc.contract_type) {
            frappe.db.get_value('KYA Contract Template',
                { contract_type: frm.doc.contract_type, is_active: 1 }, 'name')
                .then(r => {
                    if (r.message && r.message.name) {
                        frm.set_value('template', r.message.name);
                    }
                });
        }
    },

    duree_mois(frm) {
        if (frm.doc.date_debut && frm.doc.duree_mois) {
            const d = frappe.datetime.add_months(frm.doc.date_debut, frm.doc.duree_mois);
            frm.set_value('date_fin', d);
        }
    },

    date_debut(frm) {
        if (frm.doc.date_debut && frm.doc.duree_mois) {
            const d = frappe.datetime.add_months(frm.doc.date_debut, frm.doc.duree_mois);
            frm.set_value('date_fin', d);
        }
    }
});

function render_contract_preview(frm) {
    if (!frm.fields_dict.contract_preview) return;

    if (frm.is_new()) {
        frm.set_df_property('contract_preview', 'options', `
            <div style="border:1px solid #e5e7eb;border-radius:6px;padding:14px 16px;background:#fff8e7;color:#6b4300;">
                <b>Document en préparation</b><br>
                Enregistrez le contrat pour afficher ici le texte complet avec les articles et les champs du candidat.
            </div>
        `);
        return;
    }

    const print_format = (frm.doc.contract_type || '').startsWith('Stage') ? 'Contrat de Stage KYA' : 'KYA Contrat PDF';
    const print_url = `/printview?doctype=KYA%20Contrat&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent(print_format)}&no_letterhead=1`;
    const pdf_url = `/api/method/kya_hr.api.kya_contracts.download_current_pdf?contract_id=${encodeURIComponent(frm.doc.name)}`;
    frm.set_df_property('contract_preview', 'options', `
        <div style="border:1px solid #d9dee3;border-radius:6px;overflow:hidden;background:#fff;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 12px;background:#f7f9fb;border-bottom:1px solid #d9dee3;">
                <div style="font-weight:600;color:#1f2937;">Aperçu du contrat généré</div>
                <div style="display:flex;gap:8px;align-items:center;">
                    <a class="btn btn-xs btn-default" href="${print_url}" target="_blank">Ouvrir en pleine page</a>
                    <a class="btn btn-xs btn-primary" href="${pdf_url}" target="_blank">Télécharger PDF</a>
                </div>
            </div>
            <iframe src="${print_url}" style="width:100%;height:720px;border:0;background:#fff;"></iframe>
        </div>
    `);
}

function force_kya_contract_sidebar() {
    if (!frappe.app || !frappe.app.sidebar) return;
    setTimeout(() => {
        if (frappe.app.sidebar.sidebar_title !== 'Espace RH') {
            frappe.app.sidebar.setup('Espace RH');
        }
    }, 150);
}

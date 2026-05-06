// KYA Contrat - Client Script (Desk)
frappe.ui.form.on('KYA Contrat', {
    refresh(frm) {
        const roles = frappe.user_roles || [];
        const is_signataire = roles.includes('KYA Signataire Contrat');
        const is_dg = roles.includes('Directeur Général') || roles.includes('System Manager');
        const is_rh = roles.includes('Responsable RH') || roles.includes('HR Manager') || roles.includes('System Manager');

        // Le Desk RH sert à préparer, relire, transmettre et archiver.
        // Les signatures se font sur le portail documentaire tokenisé (/kya-contrat).
        if (!is_signataire) {
            ['section_sig_employe', 'contrat_lu', 'signature_employe', 'nom_signe_employe', 'date_signature_employe'].forEach((fieldname) => {
                frm.set_df_property(fieldname, 'hidden', 1);
            });
        }
        if (!is_dg || frm.doc.workflow_state !== 'En attente DG') {
            ['section_sig_dg', 'signature_dg', 'nom_dg', 'fonction_dg', 'date_signature_dg'].forEach((fieldname) => {
                frm.set_df_property(fieldname, 'hidden', 1);
            });
        }
        if (is_rh && frm.doc.workflow_state === 'Brouillon') {
            frm.dashboard.set_headline(__('Préparez le contrat ici. Le signataire le lira et le signera via le portail envoyé par email.'));
        }

        if (!frm.is_new() && frm.doc.workflow_state === 'Brouillon') {
            frm.add_custom_button(__('Envoyer au Signataire'), () => {
                frappe.confirm(
                    __('Créer le compte signataire et envoyer le contrat par email à ') + frm.doc.employee_email + ' ?',
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
            });
        }

        frm.add_custom_button(__('Aperçu Document'), () => {
            window.open(`/printview?doctype=KYA%20Contrat&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent((frm.doc.contract_type || '').startsWith('Stage') ? 'Contrat de Stage KYA' : 'KYA Contrat PDF')}&no_letterhead=0`, '_blank');
        });

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

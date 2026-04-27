// KYA Contrat — Client Script (Desk)
frappe.ui.form.on('KYA Contrat', {
    refresh(frm) {
        // Bouton "Envoyer au Signataire" (création du compte + email bienvenue)
        if (!frm.is_new() && frm.doc.workflow_state === 'Brouillon') {
            frm.add_custom_button(__('Envoyer au Signataire'), () => {
                frappe.confirm(
                    __('Créer le compte signataire et envoyer le contrat par email à ') + frm.doc.employee_email + ' ?',
                    () => {
                        frappe.call({
                            method: 'kya_hr.api.kya_contracts.send_to_signataire',
                            args: { contract_id: frm.doc.name },
                            freeze: true,
                            freeze_message: __('Envoi en cours…'),
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

        // Aperçu PDF si finalisé
        if (frm.doc.pdf_final) {
            frm.add_custom_button(__('Télécharger PDF'), () => {
                window.open(frm.doc.pdf_final, '_blank');
            });
        }

        // Lien portail
        if (!frm.is_new() && ['Envoyé Signataire', 'Signé Employé'].includes(frm.doc.workflow_state)) {
            frm.add_custom_button(__('Ouvrir Portail Signature'), () => {
                window.open('/kya-contrat?name=' + encodeURIComponent(frm.doc.name), '_blank');
            });
        }
    },

    contract_type(frm) {
        // Sélection auto du template actif
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

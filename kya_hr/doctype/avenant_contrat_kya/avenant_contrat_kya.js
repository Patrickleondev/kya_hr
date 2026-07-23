// Avenant Contrat KYA — Client Script (Desk)
// Même expérience que KYA Contrat : préparation dans le Desk RH + aperçu intégré.
frappe.ui.form.on('Avenant Contrat KYA', {
    refresh(frm) {
        force_avenant_sidebar();
        render_avenant_preview(frm);
        render_signature_status(frm);

        // Signature en ligne : bouton « Envoyer au salarié » (comme le contrat)
        if (!frm.is_new() && frm.doc.workflow_state === 'Brouillon' && !frm.doc.sans_email) {
            frm.add_custom_button(__('Envoyer au salarié (signature en ligne)'), () => {
                if (!frm.doc.employee_email) {
                    frappe.msgprint(__("Renseignez d'abord l'email de l'employé(e)."));
                    return;
                }
                if (!frm.doc.telephone) {
                    frappe.msgprint(__("Renseignez d'abord le téléphone de l'employé(e) (contrôle d'identité)."));
                    return;
                }
                frappe.confirm(
                    __('Envoyer à {0} le lien de signature en ligne de cet avenant ?', [frm.doc.employee_email]),
                    () => {
                        frappe.call({
                            method: 'kya_hr.api.avenant_signature.send_to_signataire',
                            args: { name: frm.doc.name },
                            freeze: true, freeze_message: __('Envoi…'),
                            callback: (r) => {
                                if (!r.exc) {
                                    frappe.show_alert({ message: __('Lien envoyé à l\'employé(e)'), indicator: 'green' });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }).addClass('btn-primary');
        }

        // Renvoyer le lien si l'employé ne l'a pas reçu.
        if (!frm.is_new() && frm.doc.workflow_state === 'En attente Signature Salarié') {
            frm.add_custom_button(__('Renvoyer le lien au salarié'), () => {
                frappe.call({
                    method: 'kya_hr.api.avenant_signature.send_to_signataire',
                    args: { name: frm.doc.name },
                    freeze: true, freeze_message: __('Renvoi…'),
                    callback: (r) => { if (!r.exc) frappe.show_alert({ message: __('Lien renvoyé'), indicator: 'green' }); }
                });
            }, __('Document'));
        }

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
        if (!frm.doc.employee) return;
        // civilité auto (accord en genre) + coordonnées pour la signature en ligne, si vides
        frappe.db.get_value('Employee', frm.doc.employee,
            ['gender', 'personal_email', 'company_email', 'user_id', 'cell_number']).then(r => {
            const m = r.message || {};
            if (!frm.doc.civilite && m.gender) frm.set_value('civilite', m.gender === 'Female' ? 'Mme' : 'M.');
            if (!frm.doc.employee_email) frm.set_value('employee_email', m.personal_email || m.company_email || m.user_id || '');
            if (!frm.doc.telephone) frm.set_value('telephone', m.cell_number || '');
        });
    }
});

function render_signature_status(frm) {
    if (frm.is_new()) return;
    const st = frm.doc.workflow_state || '';
    let html = '', color = '#1a5276', bg = '#eaf3fb';
    if (st === 'En attente Signature Salarié') {
        bg = '#fff8e7'; color = '#7a4600';
        const site = window.location.origin;
        const link = frm.doc.access_token_signataire
            ? `${site}/kya-avenant?name=${encodeURIComponent(frm.doc.name)}&token=${encodeURIComponent(frm.doc.access_token_signataire)}`
            : null;
        html = `<b>⏳ En attente de la signature de l'employé(e).</b> `
            + (frm.doc.phone_confirmed ? 'Identité confirmée. ' : 'Identité pas encore confirmée. ')
            + (link ? `<br><span style="font-size:12px;">Lien du portail : <a href="${link}" target="_blank">${link}</a></span>` : '');
    } else if (st === 'Signé Salarié') {
        bg = '#e8f7ed'; color = '#1d6d3a';
        html = `<b>✓ L'employé(e) a signé.</b> Relisez l'avenant puis cliquez sur <b>« Soumettre au DG »</b> pour la co-signature.`;
    } else if (st === 'En attente DG') {
        bg = '#eaf3fb'; color = '#1a3a52';
        html = `<b>✍️ En attente de la co-signature du Directeur Général.</b> Le DG peut signer via le lien reçu par email, ou ici via l'action <b>« Signer »</b>.`;
    } else if (st === 'Signé') {
        bg = '#e8f7ed'; color = '#1d6d3a';
        html = `<b>✓ Avenant finalisé et signé par les deux parties.</b>` + (frm.doc.pdf_final ? ` Le PDF signé est en pièce jointe.` : '');
    }
    if (html) {
        frm.dashboard.set_headline(`<div style="padding:6px 2px;color:${color};">${html}</div>`);
    }
}

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

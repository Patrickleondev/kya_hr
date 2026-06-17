# -*- coding: utf-8 -*-
"""Boutons desk « Envoyer au fournisseur » sur Bon Commande KYA et Appel Offre KYA.

Crée/MAJ deux Client Script (vue Form) qui ouvrent une boîte de dialogue de
REVUE (destinataire, objet, message éditables) avant l'envoi réel via
kya_hr.api.supplier_mail. Gère les fournisseurs sans email (saisie manuelle /
ignorés). Idempotent — branché dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


BC_SCRIPT = r"""
frappe.ui.form.on('Bon Commande KYA', {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button('📧 Envoyer au fournisseur', () => {
      frappe.call({ method: 'kya_hr.api.supplier_mail.prepare_bc', args: { name: frm.doc.name } })
        .then(r => {
          const m = r.message || {};
          const d = new frappe.ui.Dialog({
            title: 'Envoyer le bon de commande',
            fields: [
              { fieldname: 'to', label: 'Email destinataire', fieldtype: 'Data', reqd: 1, default: m.to,
                description: m.has_email ? 'Vous pouvez modifier l\'adresse avant envoi.'
                  : '⚠️ Aucun email enregistré pour ce fournisseur — saisissez-le ci-dessus.' },
              { fieldname: 'subject', label: 'Objet', fieldtype: 'Data', reqd: 1, default: m.subject },
              { fieldname: 'message', label: 'Message', fieldtype: 'Small Text', default: m.message },
              { fieldname: 'info', fieldtype: 'HTML',
                options: '<small style="color:#666">📎 Le bon de commande (PDF officiel) sera joint automatiquement.</small>' },
            ],
            primary_action_label: 'Envoyer',
            primary_action(v) {
              d.disable_primary_action();
              frappe.call({
                method: 'kya_hr.api.supplier_mail.send_bc',
                args: { name: frm.doc.name, to_email: v.to, subject: v.subject, message: v.message },
              }).then(rr => {
                d.hide();
                frappe.show_alert({ message: 'Envoyé à ' + (rr.message || {}).sent_to, indicator: 'green' });
                frm.reload_doc();
              }).catch(() => d.enable_primary_action());
            },
          });
          d.show();
        });
    }, '📨 Fournisseur');
  },
});
"""

AO_SCRIPT = r"""
frappe.ui.form.on('Appel Offre KYA', {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button('📧 Envoyer aux fournisseurs', () => {
      frappe.call({ method: 'kya_hr.api.supplier_mail.prepare_ao', args: { name: frm.doc.name } })
        .then(r => {
          const m = r.message || {};
          const rows = (m.fournisseurs || []).map((f, i) => `
            <tr data-row="${frappe.utils.escape_html(f.rowname)}">
              <td style="text-align:center"><input type="checkbox" class="ao-chk" ${f.has_email ? 'checked' : ''}></td>
              <td>${frappe.utils.escape_html(f.fournisseur_nom)} ${f.already_sent ? '<span style=\"color:#16a34a\">✓ déjà envoyé</span>' : ''}</td>
              <td><input type="email" class="ao-mail form-control input-sm" value="${frappe.utils.escape_html(f.email || '')}"
                   placeholder="${f.has_email ? '' : 'email manquant'}" style="min-width:200px"></td>
            </tr>`).join('');
          const d = new frappe.ui.Dialog({
            title: 'Envoyer l\'appel d\'offre',
            size: 'large',
            fields: [
              { fieldname: 'subject', label: 'Objet', fieldtype: 'Data', reqd: 1, default: m.subject },
              { fieldname: 'message', label: 'Message', fieldtype: 'Small Text', default: m.message },
              { fieldname: 'list', fieldtype: 'HTML', options:
                '<label class="control-label">Fournisseurs (décochez ou complétez les emails)</label>'
                + '<table class="table table-bordered" style="font-size:12px"><thead><tr>'
                + '<th style="width:40px">✓</th><th>Fournisseur</th><th>Email</th></tr></thead><tbody>'
                + rows + '</tbody></table>'
                + '<small style="color:#666">📎 Le PDF de l\'appel d\'offre sera joint. Les lignes sans email seront ignorées.</small>' },
            ],
            primary_action_label: 'Envoyer aux sélectionnés',
            primary_action(v) {
              const recips = [];
              d.$wrapper.find('tr[data-row]').each(function () {
                const $tr = $(this);
                if (!$tr.find('.ao-chk').is(':checked')) return;
                recips.push({ rowname: $tr.attr('data-row'), email: ($tr.find('.ao-mail').val() || '').trim() });
              });
              if (!recips.length) { frappe.msgprint('Sélectionnez au moins un fournisseur.'); return; }
              d.disable_primary_action();
              frappe.call({
                method: 'kya_hr.api.supplier_mail.send_ao',
                args: { name: frm.doc.name, recipients: JSON.stringify(recips), subject: v.subject, message: v.message },
              }).then(rr => {
                d.hide();
                const s = rr.message || {};
                frappe.show_alert({ message: `Envoyé : ${s.count_sent} · Ignorés (sans email) : ${s.count_skipped}`,
                  indicator: s.count_sent ? 'green' : 'orange' });
                frm.reload_doc();
              }).catch(() => d.enable_primary_action());
            },
          });
          d.show();
        });
    }, '📨 Fournisseurs');
  },
});
"""

SCRIPTS = {
    "BC - Envoyer au fournisseur": ("Bon Commande KYA", BC_SCRIPT),
    "AO - Envoyer aux fournisseurs": ("Appel Offre KYA", AO_SCRIPT),
}


def execute() -> dict:
    out = []
    for name, (dt, script) in SCRIPTS.items():
        if not frappe.db.exists("DocType", dt):
            continue
        existing = frappe.db.get_value("Client Script", {"dt": dt, "name": name}, "name") \
            or frappe.db.get_value("Client Script", {"dt": dt, "view": "Form",
                                                     "name": ["like", name]}, "name")
        if existing:
            doc = frappe.get_doc("Client Script", existing)
            doc.script = script
            doc.enabled = 1
            doc.view = "Form"
            doc.save(ignore_permissions=True)
            out.append(f"updated:{name}")
        else:
            doc = frappe.get_doc({
                "doctype": "Client Script", "name": name,
                "dt": dt, "view": "Form", "enabled": 1, "script": script,
            })
            doc.insert(ignore_permissions=True)
            out.append(f"created:{name}")
    frappe.db.commit()
    print("[setup_supplier_mail_buttons]", out)
    return {"scripts": out}

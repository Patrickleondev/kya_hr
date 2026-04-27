frappe.ui.form.on("Appel Offre KYA", {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.statut !== "Annul\u00e9" && frm.doc.statut !== "Cl\u00f4tur\u00e9") {
            frm.add_custom_button(__("\uD83D\uDCE7 Envoyer aux fournisseurs"), function() {
                frappe.confirm(
                    __("Envoyer l'appel d'offre par email \u00e0 tous les fournisseurs ayant une adresse email ?"),
                    function() {
                        frappe.call({
                            method: "kya_hr.kya_hr.doctype.appel_offre_kya.appel_offre_kya.send_to_suppliers",
                            args: { name: frm.doc.name, only_unsent: 1 },
                            freeze: true,
                            freeze_message: __("Envoi en cours..."),
                            callback: function(r) {
                                if (r.message) {
                                    var msg = __("Envoyé à {0} fournisseur(s)", [r.message.sent]);
                                    if (r.message.skipped_no_email && r.message.skipped_no_email.length) {
                                        msg += "<br>" + __("Sans email (\u00e0 contacter autrement)") + " : " + r.message.skipped_no_email.join(", ");
                                    }
                                    if (r.message.errors && r.message.errors.length) {
                                        msg += "<br><span style='color:#c62828'>" + __("Erreurs") + " : " + r.message.errors.join("<br>") + "</span>";
                                    }
                                    frappe.msgprint({
                                        title: __("R\u00e9sultat envoi"),
                                        message: msg,
                                        indicator: "green"
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("Actions"));

            frm.add_custom_button(__("\uD83D\uDD04 MAJ compteur r\u00e9ponses"), function() {
                frappe.call({
                    method: "kya_hr.kya_hr.doctype.appel_offre_kya.appel_offre_kya.update_reponses",
                    args: { name: frm.doc.name },
                    callback: function(r) {
                        if (r.message !== undefined) {
                            frappe.show_alert({ message: __("R\u00e9ponses: {0}", [r.message]), indicator: "blue" });
                            frm.reload_doc();
                        }
                    }
                });
            }, __("Actions"));
        }

        // Indicator
        if (frm.doc.statut_envoi === "Envoy\u00e9 \u00e0 tous") {
            frm.dashboard.set_headline_alert(
                "<div style='color:#2e7d32'>\u2709 Envoy\u00e9 \u00e0 " + frm.doc.nombre_envois + " fournisseur(s) \u2014 " + (frm.doc.nombre_reponses || 0) + " r\u00e9ponse(s) re\u00e7ue(s)</div>"
            );
        } else if (frm.doc.statut_envoi === "Envoy\u00e9 partiellement") {
            frm.dashboard.set_headline_alert(
                "<div style='color:#e65100'>\u26A0 Envoy\u00e9 partiellement \u2014 certains fournisseurs n'ont pas d'email</div>"
            );
        }
    },

    demandeur: function(frm) {
        if (frm.doc.demandeur) {
            frappe.db.get_value("Employee", frm.doc.demandeur, ["employee_name", "department"], function(r) {
                if (r) {
                    frm.set_value("demandeur_name", r.employee_name);
                    if (r.department) frm.set_value("service", r.department);
                }
            });
        }
    }
});

frappe.ui.form.on("Appel Offre KYA Fournisseur", {
    fournisseur: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.fournisseur) {
            frappe.db.get_value("Supplier", row.fournisseur, ["supplier_name", "email_id", "mobile_no"], function(r) {
                if (r) {
                    frappe.model.set_value(cdt, cdn, "fournisseur_nom", r.supplier_name);
                    if (r.email_id) frappe.model.set_value(cdt, cdn, "email", r.email_id);
                    if (r.mobile_no) frappe.model.set_value(cdt, cdn, "telephone", r.mobile_no);
                }
            });
            // Contact principal
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Dynamic Link",
                    filters: { link_doctype: "Supplier", link_name: row.fournisseur, parenttype: "Contact" },
                    fields: ["parent"],
                    limit: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length) {
                        frappe.db.get_doc("Contact", r.message[0].parent).then(function(c) {
                            var full = (c.first_name || "") + " " + (c.last_name || "");
                            frappe.model.set_value(cdt, cdn, "contact", full.trim());
                            if (!row.email && c.email_ids && c.email_ids.length) {
                                frappe.model.set_value(cdt, cdn, "email", c.email_ids[0].email_id);
                            }
                            if (!row.telephone && c.phone_nos && c.phone_nos.length) {
                                frappe.model.set_value(cdt, cdn, "telephone", c.phone_nos[0].phone);
                            }
                        });
                    }
                }
            });
        }
    }
});

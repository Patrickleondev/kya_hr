// Inventaire KYA — Script Client Desk
// Bouton "Charger Articles" qui pré-remplit depuis Bin ERPNext

frappe.ui.form.on("Inventaire KYA", {
    refresh(frm) {
        if (frm.doc.statut) {
            const cmap = { "Approuvé": "green", "Rejeté": "red", "Brouillon": "grey",
                           "En attente Magasin": "orange" };
            frm.dashboard.clear_headline();
            frm.dashboard.set_headline_alert(
                `<div style="padding:4px 12px;font-weight:600;">
                   État : ${frappe.utils.escape_html(frm.doc.statut)}
                 </div>`,
                cmap[frm.doc.statut] || "blue"
            );
        }

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Charger Articles depuis Magasin"), () => {
                if (!frm.doc.warehouse_filter) {
                    frappe.msgprint(__("Veuillez d'abord choisir un magasin."));
                    return;
                }
                frappe.call({
                    method: "kya_hr.kya_hr.doctype.inventaire_kya.inventaire_kya.load_items_from_warehouse",
                    args: { inventaire_name: frm.doc.name, warehouse: frm.doc.warehouse_filter },
                    freeze: true, freeze_message: __("Chargement des articles…"),
                    callback: r => {
                        if (!r.message || !r.message.length) {
                            frappe.msgprint(__("Aucun article trouvé dans ce magasin."));
                            return;
                        }
                        frm.clear_table("items");
                        r.message.forEach(d => {
                            const row = frm.add_child("items");
                            row.item_code = d.item_code;
                            row.designation = d.designation;
                            row.uom = d.uom;
                            row.warehouse = d.warehouse;
                            row.qte_theorique = d.qte_theorique;
                            row.qte_comptee = d.qte_theorique;
                            row.valuation_rate = d.valuation_rate;
                        });
                        frm.refresh_field("items");
                        frappe.show_alert({ message: __("{0} articles chargés", [r.message.length]),
                                            indicator: "green" });
                    }
                });
            }, __("Actions"));
        }

        if (frm.doc.stock_reconciliation) {
            frm.add_custom_button(__("Voir Stock Reconciliation"), () => {
                frappe.set_route("Form", "Stock Reconciliation", frm.doc.stock_reconciliation);
            }, __("Traçabilité"));
        }
    },

    onload(frm) {
        if (frm.is_new() && !frm.doc.responsable_nom) {
            frappe.db.get_value("Employee",
                { user_id: frappe.session.user }, "employee_name"
            ).then(r => {
                if (r.message && r.message.employee_name) {
                    frm.set_value("responsable_nom", r.message.employee_name);
                }
            });
        }
    }
});

frappe.ui.form.on("Inventaire KYA Item", {
    qte_comptee(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        row.ecart = (row.qte_comptee || 0) - (row.qte_theorique || 0);
        frm.refresh_field("items");
    }
});

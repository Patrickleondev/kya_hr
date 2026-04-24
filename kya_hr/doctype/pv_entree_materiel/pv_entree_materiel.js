// PV Entrée Matériel — Script Client
// Dashboard + contrôle signatures par workflow_state

frappe.ui.form.on("PV Entree Materiel", {
    refresh(frm) {
        // Dashboard coloré
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

        // Lien vers Stock Entry si déjà créé
        if (frm.doc.stock_entry) {
            frm.add_custom_button(__("Voir Stock Entry"), () => {
                frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry);
            }, __("Traçabilité"));
        }

        // Lock/unlock des signatures selon workflow_state + rôles
        const state = frm.doc.workflow_state || frm.doc.statut || "Brouillon";
        const roles = frappe.user_roles || [];
        const rules = {
            signature_livreur:  { states: ["Brouillon"], roles: [] },
            livreur_nom:        { states: ["Brouillon"], roles: [] },
            signature_magasin:  { states: ["En attente Magasin"],
                                  roles: ["Stock Manager","Stock User","System Manager","Chargé des Stocks"] },
        };
        Object.keys(rules).forEach(f => frm.set_df_property(f, "read_only", 1));
        for (const [f, r] of Object.entries(rules)) {
            const stateOk = r.states.includes(state);
            const roleOk = r.roles.length === 0 || r.roles.some(x => roles.includes(x));
            if (stateOk && roleOk) frm.set_df_property(f, "read_only", 0);
        }
    },

    onload(frm) {
        if (frm.is_new() && !frm.doc.livreur_nom && frappe.session.user !== "Administrator") {
            frappe.db.get_value("Employee",
                { user_id: frappe.session.user },
                "employee_name"
            ).then(r => {
                if (r.message && r.message.employee_name) {
                    frm.set_value("livreur_nom", r.message.employee_name);
                    frm.set_value("livreur_date", frappe.datetime.get_today());
                }
            });
        }
    },

    purchase_order(frm) {
        // Auto-pré-remplit items depuis un Purchase Order
        if (!frm.doc.purchase_order) return;
        frappe.db.get_doc("Purchase Order", frm.doc.purchase_order).then(po => {
            frm.set_value("fournisseur", po.supplier);
            frm.clear_table("items");
            (po.items || []).forEach(it => {
                const row = frm.add_child("items");
                row.item_code = it.item_code;
                row.designation = it.item_name;
                row.uom = it.uom;
                row.qte_recue = it.qty;
                row.prix_unitaire = it.rate;
                row.warehouse = it.warehouse;
            });
            frm.refresh_field("items");
        });
    }
});

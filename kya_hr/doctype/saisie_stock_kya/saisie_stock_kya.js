// Saisie Stock KYA — le picker « Magasin » ne propose que les magasins KYA
// (on masque les entrepôts techniques ERPNext : Goods In Transit, Stores, etc.).
frappe.ui.form.on("Saisie Stock KYA", {
	refresh(frm) {
		frm.set_query("magasin", () => ({
			query: "kya_hr.api.stock_kya.magasin_link_query",
		}));
	},
});

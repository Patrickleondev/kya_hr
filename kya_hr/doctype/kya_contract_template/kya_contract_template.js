// Copyright (c) 2026, KYA-Energy Group and contributors
// Confort RH : bouton d'aperçu + rappel des variables. Aucun déploiement n'est
// nécessaire pour créer/modifier un modèle — tout se fait dans ce formulaire.
frappe.ui.form.on("KYA Contract Template", {
	refresh(frm) {
		frm.add_custom_button(__("👁 Aperçu du contrat"), async () => {
			// L'aperçu est rendu côté serveur à partir du document ENREGISTRÉ ;
			// on sauvegarde d'abord si des modifications sont en cours.
			if (frm.is_dirty()) {
				try {
					await frm.save();
				} catch (e) {
					return; // erreur de validation : on laisse Frappe l'afficher
				}
			}
			const r = await frm.call("get_preview");
			if (!r || !r.message) {
				frappe.msgprint(__("Rien à afficher : ajoutez des articles ou un corps HTML."));
				return;
			}
			const d = new frappe.ui.Dialog({
				title: __("Aperçu — {0}", [frm.doc.title || "Modèle"]),
				size: "large",
				fields: [{ fieldtype: "HTML", fieldname: "apercu" }],
			});
			d.fields_dict.apercu.$wrapper.html(
				'<div style="background:#fff;color:#111;padding:26px 30px;border:1px solid #ddd;' +
					'border-radius:6px;font-family:Georgia,\'Times New Roman\',serif;font-size:13px;' +
					'line-height:1.65;max-height:70vh;overflow:auto">' +
					r.message +
					'</div>'
			);
			d.show();
		});

		// Petit garde-fou visuel : prévenir si un article contient une variable
		// inconnue (typo) — elle resterait telle quelle sur le contrat imprimé.
		if ((frm.doc.articles || []).length) {
			const connues = new Set([
				"employe", "civilite", "civilite_longue", "poste", "type_contrat",
				"date_debut", "date_fin", "date_jour", "entreprise", "dg",
			]);
			const inconnues = new Set();
			(frm.doc.articles || []).forEach((a) => {
				(String(a.contenu || "").match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g) || []).forEach((tok) => {
					const nom = tok.slice(1, -1);
					if (!connues.has(nom)) inconnues.add(nom);
				});
			});
			if (inconnues.size) {
				frm.dashboard.set_headline(
					__("⚠️ Variable(s) inconnue(s) : {0} — elles apparaîtront telles quelles. Voir l'aide des variables.",
						[[...inconnues].map((v) => "{" + v + "}").join(", ")])
				);
			}
		}
	},
});

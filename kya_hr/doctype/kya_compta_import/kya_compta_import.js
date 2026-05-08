frappe.ui.form.on('KYA Compta Import', {
	refresh(frm) {
		frm.add_custom_button(__('Ouvrir le tableau de bord'), function () {
			window.open('/comptabilite-dashboard', '_blank');
		});

		if (!frm.is_new() && frm.doc.source_file) {
			frm.add_custom_button(__('Réimporter le fichier'), function () {
				frm.call('reimport_from_source').then(function () {
					frm.save();
				});
			});
		}
	}
});

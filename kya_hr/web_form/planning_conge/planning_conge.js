frappe.ready(function () {
	if (frappe.web_form && frappe.web_form.doc && !frappe.web_form.doc.name) {
		frappe.call({
			method: 'kya_hr.api.get_current_employee',
			async: false,
			callback: function (r) {
				if (r && r.message) {
					var emp = r.message;
					if (emp.employee_id) {
						frappe.web_form.set_value('employee', emp.employee_id);
						if (!emp.is_hr) {
							var $field = $('[data-fieldname="employee"]');
							$field.find('input, select').prop('disabled', true);
							$field.find('.like-disabled-input').css('pointer-events', 'none');
						}
					}
				}
			}
		});
	}

	// Recalcul dynamique du solde côté web form
	function recalc_solde() {
		var doc = frappe.web_form.doc || {};
		var n1 = parseFloat(doc.solde_n1 || 0);
		var acquis = parseFloat(doc.jours_acquis || 0);
		var oblig = parseInt(doc.conges_obligatoires || 0);
		var monet = parseInt(doc.jours_monetisation || 0);

		var total = 0;
		(doc.periodes || []).forEach(function (p) {
			if (p.date_debut && p.date_fin) {
				var d1 = moment(p.date_debut);
				var d2 = moment(p.date_fin);
				if (d2.isSameOrAfter(d1)) {
					p.nb_jours = d2.diff(d1, 'days') + 1;
				}
			}
			total += parseInt(p.nb_jours || 0);
		});

		var dispo = n1 + acquis - oblig;
		var final = dispo - total - monet;

		frappe.web_form.set_value('solde_disponible', dispo);
		frappe.web_form.set_value('solde_final', final);

		// Alerte visuelle si solde final négatif
		var $alert = $('#solde-alert');
		if ($alert.length === 0) {
			$alert = $('<div id="solde-alert" style="margin:10px 0;padding:10px;border-radius:6px;display:none;"></div>');
			$('[data-fieldname="solde_final"]').closest('.form-group').after($alert);
		}
		if (final < 0) {
			$alert.css({background: '#ffebee', color: '#c62828', border: '1px solid #ef9a9a', display: 'block'})
				.html('⚠️ Solde final négatif (' + final.toFixed(1) + ' j) — vous demandez plus de jours que votre solde disponible.');
		} else {
			$alert.hide();
		}
	}

	// Hook recalcul sur changements
	['solde_n1', 'jours_acquis', 'conges_obligatoires', 'jours_monetisation', 'periodes'].forEach(function (f) {
		$(document).on('change', '[data-fieldname="' + f + '"]', recalc_solde);
	});
	$(document).on('change', '.web-form-input, input.input-with-feedback', function () {
		setTimeout(recalc_solde, 200);
	});

	setTimeout(recalc_solde, 500);
});

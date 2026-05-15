frappe.ready(function () {
	// ── 1. Auto-fill employé connecté ───────────────────────────────────────
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
		// Valeur par défaut pour le type de congé
		if (!frappe.web_form.doc.leave_type_par_defaut) {
			frappe.web_form.set_value('leave_type_par_defaut', 'Congé Annuel');
		}
	}

	// ── 2. Recalcul dynamique du solde ───────────────────────────────────────
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
		var final_val = dispo - total - monet;

		frappe.web_form.set_value('solde_disponible', dispo);
		frappe.web_form.set_value('solde_final', final_val);

		var $alert = $('#solde-alert');
		if ($alert.length === 0) {
			$alert = $('<div id="solde-alert" style="margin:10px 0;padding:10px;border-radius:6px;display:none;"></div>');
			$('[data-fieldname="solde_final"]').closest('.form-group').after($alert);
		}
		if (final_val < 0) {
			$alert.css({background: '#ffebee', color: '#c62828', border: '1px solid #ef9a9a', display: 'block'})
				.html('⚠️ Solde final négatif (' + final_val.toFixed(1) + ' j) — vous demandez plus de jours que votre solde disponible.');
		} else {
			$alert.hide();
		}
	}

	// ── 3. Auto-remplissage type_conge dans chaque ligne depuis leave_type_par_defaut ─
	function fill_type_conge_in_rows() {
		var doc = frappe.web_form.doc || {};
		var leave_type = doc.leave_type_par_defaut || 'Congé Annuel';
		(doc.periodes || []).forEach(function (row) {
			if (!row.type_conge) row.type_conge = leave_type;
		});
		$('.grid-row').each(function () {
			var $input = $(this).find('[data-fieldname="type_conge"] input');
			if ($input.length && !$input.val()) $input.val(leave_type);
		});
	}

	// Quand le type par défaut change → propager dans toutes les lignes
	frappe.web_form.on('leave_type_par_defaut', function (field, value) {
		var doc = frappe.web_form.doc || {};
		(doc.periodes || []).forEach(function (row) { row.type_conge = value; });
		fill_type_conge_in_rows();
		recalc_solde();
	});

	// Quand une ligne est ajoutée → remplir type_conge
	$(document).on('click', '.grid-add-row, .btn-open-row', function () {
		setTimeout(fill_type_conge_in_rows, 300);
	});

	// Recalcul sur tout changement
	['solde_n1', 'jours_acquis', 'conges_obligatoires', 'jours_monetisation'].forEach(function (f) {
		frappe.web_form.on(f, recalc_solde);
	});
	$(document).on('change', '[data-fieldname="periodes"] input, [data-fieldname="periodes"] select', function () {
		setTimeout(recalc_solde, 300);
	});
	$(document).on('change', '.web-form-input, input.input-with-feedback', function () {
		setTimeout(recalc_solde, 200);
	});

	// Init
	setTimeout(function () { fill_type_conge_in_rows(); recalc_solde(); }, 600);
});

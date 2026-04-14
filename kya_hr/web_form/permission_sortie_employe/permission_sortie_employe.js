frappe.ready(function () {
	// Auto-remplir l'employé connecté (sauf Admin/RH qui peut saisir manuellement)
	if (frappe.web_form && frappe.web_form.doc && !frappe.web_form.doc.name) {
		frappe.call({
			method: 'kya_hr.api.get_current_employee',
			async: false,
			callback: function (r) {
				if (r && r.message) {
					var emp = r.message;
					if (emp.employee_id) {
						frappe.web_form.set_value('employee', emp.employee_id);
						// RH et Admin peuvent changer ; les autres non
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
});

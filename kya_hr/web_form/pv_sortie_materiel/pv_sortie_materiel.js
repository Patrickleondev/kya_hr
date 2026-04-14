frappe.ready(function () {
	if (frappe.web_form && frappe.web_form.doc && !frappe.web_form.doc.name) {
		frappe.call({
			method: 'kya_hr.api.get_current_employee',
			async: false,
			callback: function (r) {
				if (r && r.message) {
					var emp = r.message;
					if (emp.employee_name) {
						frappe.web_form.set_value('demandeur_nom', emp.employee_name);
						if (!emp.is_hr) {
							var $field = $('[data-fieldname="demandeur_nom"]');
							$field.find('input').prop('disabled', true);
						}
					}
				}
			}
		});
	}
});

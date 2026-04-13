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
});

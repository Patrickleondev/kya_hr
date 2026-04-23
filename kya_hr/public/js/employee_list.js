/**
 * KYA Employee List View customization
 * Auto-filters to show only Stagiaires when accessed from Espace Stagiaires workspace
 */
frappe.listview_settings['Employee'] = Object.assign(
    frappe.listview_settings['Employee'] || {},
    {
        onload: function(listview) {
            var route_options = frappe.route_options || {};
            var sidebar = route_options.sidebar || '';

            if (sidebar && (sidebar.toLowerCase().indexOf('stagiaire') >= 0 || sidebar.toLowerCase().indexOf('espace') >= 0)) {
                listview.filter_area.add([
                    ['Employee', 'employment_type', '=', 'Stage']
                ]);
                listview.page.set_title('Liste des Stagiaires');
            }
        }
    }
);

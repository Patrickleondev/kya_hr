frappe.query_reports["Fiche Gestion Conges"] = {
    filters: [
        {
            fieldname: "year",
            label: __("Année"),
            fieldtype: "Select",
            options: (function () {
                var y = new Date().getFullYear();
                var opts = [];
                for (var i = y; i >= y - 5; i--) opts.push(i);
                return opts.join("\n");
            })(),
            default: new Date().getFullYear(),
            reqd: 1,
        },
        {
            fieldname: "employee",
            label: __("Employé"),
            fieldtype: "Link",
            options: "Employee",
        },
        {
            fieldname: "department",
            label: __("Département"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "leave_type",
            label: __("Type de Congé"),
            fieldtype: "Link",
            options: "Leave Type",
        },
    ],
};

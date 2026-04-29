// Fiche de Gestion des Congés Annuels — Filtres
frappe.query_reports["Fiche Gestion Conges Annuels"] = {
    filters: [
        {
            fieldname: "year",
            label: __("Année"),
            fieldtype: "Int",
            default: new Date().getFullYear(),
            reqd: 1,
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
        {
            fieldname: "employment_type",
            label: __("Type d'emploi"),
            fieldtype: "Link",
            options: "Employment Type",
        },
    ],
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (data && column.fieldname === "restants") {
            if ((data.restants || 0) <= 0) {
                value = `<span style="color:#c0392b;font-weight:600;">${value}</span>`;
            } else if ((data.restants || 0) >= 20) {
                value = `<span style="color:#27ae60;font-weight:600;">${value}</span>`;
            }
        }
        return value;
    },
};

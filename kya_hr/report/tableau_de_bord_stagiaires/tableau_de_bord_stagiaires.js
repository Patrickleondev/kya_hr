frappe.query_reports["Tableau de Bord Stagiaires"] = {
    filters: [
        {
            fieldname: "department",
            label: __("Département"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "gender",
            label: __("Genre"),
            fieldtype: "Select",
            options: "\nMale\nFemale",
        },
        {
            fieldname: "status",
            label: __("Statut"),
            fieldtype: "Select",
            options: "\nActive\nInactive\nLeft",
            default: "Active",
        },
        {
            fieldname: "chart_type",
            label: __("Graphique"),
            fieldtype: "Select",
            options: "Par Département\nGenre\nPrésences",
            default: "Par Département",
        },
    ],
};

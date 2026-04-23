frappe.query_reports["Rapport Présence Stagiaires"] = {
    filters: [
        {
            fieldname: "period",
            label: "Période",
            fieldtype: "Select",
            options: "Journalier\nMensuel",
            default: "Journalier",
            on_change: function () {
                let period = frappe.query_report.get_filter_value("period");
                frappe.query_report.toggle_filter_display("date", period !== "Journalier");
                frappe.query_report.toggle_filter_display("from_date", period !== "Mensuel");
                frappe.query_report.toggle_filter_display("to_date", period !== "Mensuel");
                frappe.query_report.refresh();
            },
        },
        {
            fieldname: "date",
            label: "Date",
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "from_date",
            label: "Du",
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            hidden: 1,
        },
        {
            fieldname: "to_date",
            label: "Au",
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            hidden: 1,
        },
        {
            fieldname: "department",
            label: "Département",
            fieldtype: "Link",
            options: "Department",
        },
    ],
};

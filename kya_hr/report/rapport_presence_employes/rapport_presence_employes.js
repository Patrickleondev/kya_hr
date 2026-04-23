frappe.query_reports["Rapport Présence Employés"] = {
    filters: [
        {
            fieldname: "period",
            label: __("Période"),
            fieldtype: "Select",
            options: "Journalier\nMensuel",
            default: "Journalier",
            reqd: 1,
            on_change: function() {
                let period = frappe.query_report.get_filter_value("period");
                frappe.query_report.toggle_filter_display("date", period !== "Journalier");
                frappe.query_report.toggle_filter_display("from_date", period !== "Mensuel");
                frappe.query_report.toggle_filter_display("to_date", period !== "Mensuel");
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "from_date",
            label: __("Du"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            hidden: 1,
        },
        {
            fieldname: "to_date",
            label: __("Au"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            hidden: 1,
        },
        {
            fieldname: "department",
            label: __("Département"),
            fieldtype: "Link",
            options: "Department",
        },
    ],
};

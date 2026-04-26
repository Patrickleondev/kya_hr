// Filtres dynamiques temps réel — Sorties Matériel par Client/Projet
frappe.query_reports["Sorties Matériel par Client/Projet"] = {
    filters: [
        {
            fieldname: "date_from",
            label: __("Du"),
            fieldtype: "Date",
            default: frappe.datetime.year_start(),
            reqd: 0,
        },
        {
            fieldname: "date_to",
            label: __("Au"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 0,
        },
        {
            fieldname: "client",
            label: __("Client"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "projet",
            label: __("Projet"),
            fieldtype: "Link",
            options: "Project",
        },
        {
            fieldname: "item_code",
            label: __("Article"),
            fieldtype: "Link",
            options: "Item",
        },
        {
            fieldname: "warehouse",
            label: __("Magasin"),
            fieldtype: "Link",
            options: "Warehouse",
        },
        {
            fieldname: "statut",
            label: __("Statut"),
            fieldtype: "Select",
            options: [
                "",
                "Brouillon",
                "En attente Chef",
                "En attente Magasin",
                "En attente Audit",
                "En attente DGA",
                "Approuvé",
                "Rejeté",
            ].join("\n"),
        },
    ],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "statut" && data) {
            const colors = {
                "Approuvé": "green",
                "Rejeté": "red",
                "Brouillon": "gray",
            };
            const c = colors[data.statut] || "blue";
            value = `<span class="indicator-pill ${c}">${data.statut || ""}</span>`;
        }
        return value;
    },
};

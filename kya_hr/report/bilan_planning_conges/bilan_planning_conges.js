// Copyright (c) 2026, KYA-Energy Group and contributors
// For license information, please see license.txt

frappe.query_reports["Bilan Planning Conges"] = {
    filters: [
        {
            fieldname: "annee",
            label: "Année",
            fieldtype: "Int",
            default: new Date().getFullYear(),
            reqd: 1,
        },
        {
            fieldname: "department",
            label: "Département",
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "workflow_state",
            label: "Statut",
            fieldtype: "Select",
            options: [
                "",
                "Brouillon",
                "En attente Chef de Service",
                "En attente DG",
                "Approuvé",
                "Rejeté",
            ].join("\n"),
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "workflow_state" && data) {
            const colors = {
                "Approuvé": "#2e7d32",
                "Rejeté": "#c62828",
                "Brouillon": "#616161",
                "En attente Chef de Service": "#f57c00",
                "En attente DG": "#1976d2",
            };
            const color = colors[data.workflow_state] || "#546e7a";
            value = `<span style="background:${color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;">${data.workflow_state || "—"}</span>`;
        }
        if (column.fieldname === "solde_final" && data && data.solde_final < 0) {
            value = `<span style="color:#c62828;font-weight:700;">${value}</span>`;
        }
        return value;
    },
};

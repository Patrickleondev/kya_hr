frappe.ready(function () {
    var roles = (frappe.boot && frappe.boot.user && frappe.boot.user.roles) || [];
    var isPrivileged = roles.some(function (r) {
        return ["System Manager", "HR Manager", "HR User", "DG", "DGA"].indexOf(r) !== -1;
    });
    var isTeamLead = roles.some(function (r) {
        return ["Chef Equipe", "Chef d'Equipe", "Chef Service"].indexOf(r) !== -1;
    });

    if (isPrivileged) {
        return;
    }

    // UX guard on desk cards for simple employees; server permissions stay authoritative.
    var blockedLabels = [
        "Employee",
        "Espace Stagiaires",
        "KYA Services",
        "Comptabilité",
        "Achat",
        "Stock",
    ];

    if (!isTeamLead) {
        blockedLabels.push("Gestion Équipe");
        blockedLabels.push("Gestion Equipe");
        blockedLabels.push("Dashboard Equipe");
    }

    window.setTimeout(function () {
        var cards = document.querySelectorAll(".standard-sidebar-item, .desk-sidebar-item, .app-icon");
        cards.forEach(function (node) {
            var txt = (node.textContent || "").toLowerCase();
            if (txt.indexOf("espace employ") >= 0) {
                node.style.display = "";
                return;
            }
            var blocked = blockedLabels.some(function (label) {
                return txt.indexOf(label.toLowerCase()) >= 0;
            });
            if (blocked) {
                node.style.display = "none";
            }
        });
    }, 600);
});

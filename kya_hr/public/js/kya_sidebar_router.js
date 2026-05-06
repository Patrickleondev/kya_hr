// Force the intended KYA workspace sidebar for ambiguous DocType routes.
(function () {
    const DOCTYPE_SIDEBARS = {
        'KYA Contrat': 'Espace RH',
        'Permission Sortie Employe': 'Espace RH',
        'Planning Conge': 'Espace RH',
        'Leave Application': 'Espace RH',

        'Permission Sortie Stagiaire': 'Espace Stagiaires',
        'Bilan Fin de Stage': 'Espace Stagiaires',

        'Demande Achat KYA': 'Espace Achats',
        'Bon Commande KYA': 'Espace Achats',
        'Appel Offre KYA': 'Espace Achats',

        'PV Sortie Materiel': 'Espace Stock',
        'PV Entree Materiel': 'Espace Stock',
        'Item': 'Espace Stock',

        'Brouillard Caisse': 'Espace Comptabilité',
        'Etat Recap Cheques': 'Espace Comptabilité',

        'Sortie Vehicule': 'Logistique',
        'Vehicle': 'Logistique',
        'Document Vehicule': 'Logistique',

        'KYA Form': 'KYA Services',
        'KYA Evaluation': 'KYA Services',
        'KYA Form Response': 'KYA Services',

        'Plan Trimestriel': 'Gestion Équipe',
        'Tache Equipe': 'Gestion Équipe',
    };

    function current_doctype() {
        if (!window.frappe || !frappe.get_route) return null;
        const route = frappe.get_route() || [];
        if (['List', 'Form', 'Tree'].includes(route[0])) return route[1];
        return null;
    }

    function force_sidebar() {
        if (!window.frappe || !frappe.app || !frappe.app.sidebar || !frappe.boot) return;
        const doctype = current_doctype();
        const sidebar = DOCTYPE_SIDEBARS[doctype];
        if (!sidebar) return;

        const key = sidebar.toLowerCase();
        if (!frappe.boot.workspace_sidebar_item || !frappe.boot.workspace_sidebar_item[key]) return;
        if (frappe.app.sidebar.sidebar_title === sidebar) {
            frappe.app.sidebar.set_active_workspace_item && frappe.app.sidebar.set_active_workspace_item();
            return;
        }

        frappe.app.sidebar.setup(sidebar);
        frappe.app.sidebar.set_active_workspace_item && frappe.app.sidebar.set_active_workspace_item();
    }

    function schedule_force_sidebar() {
        setTimeout(force_sidebar, 120);
        setTimeout(force_sidebar, 350);
    }

    if (window.frappe && frappe.router) {
        frappe.router.on('change', schedule_force_sidebar);
    }

    $(document).on('form-refresh page-change list-refresh', schedule_force_sidebar);
    $(document).ready(schedule_force_sidebar);
})();
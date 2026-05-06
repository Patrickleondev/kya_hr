// Force the intended KYA workspace sidebar for ambiguous DocType routes.
(function () {
    const STAGIAIRE_WORKSPACE_ROLES = [
        'Stagiaire',
        'Maître de Stage',
        'Responsable des Stagiaires',
        'Responsable RH',
        'HR Manager',
        'System Manager',
        'Directeur Général',
    ];

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

    function has_any_role(roles) {
        const user_roles = (window.frappe && frappe.user_roles) || [];
        return roles.some(role => user_roles.includes(role));
    }

    function can_see_stagiaire_space() {
        return has_any_role(STAGIAIRE_WORKSPACE_ROLES);
    }

    function hide_restricted_workspace_links() {
        if (can_see_stagiaire_space()) return;
        const selectors = [
            '.standard-sidebar-item',
            '.desk-sidebar-item',
            '.sidebar-item',
            '.workspace-sidebar-item',
            '.app-icon',
            'a[href*="espace-stagiaires"]',
            'a[href*="Espace%20Stagiaires"]',
        ];
        document.querySelectorAll(selectors.join(',')).forEach(el => {
            const text = (el.textContent || '').trim().toLowerCase();
            const href = (el.getAttribute && (el.getAttribute('href') || '')) || '';
            if (text.includes('espace stagiaires') || href.toLowerCase().includes('espace-stagiaires')) {
                el.style.display = 'none';
                el.setAttribute('aria-hidden', 'true');
            }
        });
    }

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
        if (sidebar === 'Espace Stagiaires' && !can_see_stagiaire_space()) return;

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
        hide_restricted_workspace_links();
        setTimeout(force_sidebar, 120);
        setTimeout(force_sidebar, 350);
        setTimeout(hide_restricted_workspace_links, 450);
    }

    if (window.frappe && frappe.router) {
        frappe.router.on('change', schedule_force_sidebar);
    }

    $(document).on('form-refresh page-change list-refresh', schedule_force_sidebar);
    $(document).ready(schedule_force_sidebar);
    if (document.body) {
        new MutationObserver(hide_restricted_workspace_links)
            .observe(document.body, { childList: true, subtree: true });
    }
})();

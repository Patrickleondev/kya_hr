// Force the intended KYA workspace sidebar for ambiguous DocType routes.
(function () {
    const STAGIAIRE_WORKSPACE_ROLES = [
        'Maître de Stage',
        'Responsable des Stagiaires',
        'Responsable RH',
        'HR User',
        'HR Manager',
        'System Manager',
        'Directeur Général',
    ];

    const EMPLOYES_WORKSPACE_ROLES = [
        'Chef Service',
        'Supérieur Immédiat',
        'Responsable RH',
        'HR User',
        'HR Manager',
        'Directeur Général',
        'DAAF',
        'Auditeur Interne',
        'Stock User',
        'Purchase User',
        'Responsable Achats',
        'Chargé des Stocks',
        'KYA Destinataire Notif',
        'System Manager',
    ];

    const GESTION_EQUIPE_ROLES = ['Chef d’Équipe', "Chef d'Équipe", 'Chef Service', 'System Manager'];
    const KYA_SERVICES_ROLES = ['KYA Survey Admin', 'System Manager'];

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

    function can_see_employes_space() {
        return has_any_role(EMPLOYES_WORKSPACE_ROLES);
    }

    function can_see_gestion_equipe() {
        return has_any_role(GESTION_EQUIPE_ROLES);
    }

    function can_see_kya_services() {
        return has_any_role(KYA_SERVICES_ROLES);
    }

    function is_simple_self_service_user() {
        const user_roles = (window.frappe && frappe.user_roles) || [];
        return (user_roles.includes('Employee Self Service') || user_roles.includes('Employee') || user_roles.includes('Stagiaire'))
            && !can_see_employes_space()
            && !can_see_stagiaire_space()
            && !can_see_gestion_equipe()
            && !can_see_kya_services();
    }

    function hide_matching_links(terms) {
        const selectors = [
            '.standard-sidebar-item',
            '.desk-sidebar-item',
            '.sidebar-item',
            '.workspace-sidebar-item',
            '.app-icon',
            '.desktop-icon',
            '.module-link',
            'a[href]',
        ];
        document.querySelectorAll(selectors.join(',')).forEach(el => {
            const text = (el.textContent || '').trim().toLowerCase();
            const href = (el.getAttribute && (el.getAttribute('href') || '').toLowerCase()) || '';
            const title = (el.getAttribute && (el.getAttribute('title') || '').toLowerCase()) || '';
            if (terms.some(term => text.includes(term) || href.includes(term) || title.includes(term))) {
                el.style.display = 'none';
                el.setAttribute('aria-hidden', 'true');
            }
        });
    }

    function hide_restricted_workspace_links() {
        if (!can_see_stagiaire_space()) hide_matching_links(['espace stagiaires', 'espace-stagiaires']);
        if (!can_see_employes_space()) hide_matching_links(['espace employés', 'espace employes', 'espace-employes', 'espace-employés']);
        if (!can_see_gestion_equipe()) hide_matching_links(['gestion équipe', 'gestion equipe', 'gestion-equipe']);
        if (!can_see_kya_services()) hide_matching_links(['kya services', 'kya-services']);
        if (is_simple_self_service_user()) {
            hide_matching_links(['espace rh', 'espace-rh', 'espace direction', 'espace-direction']);
        }
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

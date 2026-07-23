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
        'Retour Materiel KYA': 'Espace Stock',
        'Item': 'Espace Stock',

        'Brouillard Caisse': 'Espace Comptabilite',
        'Etat Recap Cheques': 'Espace Comptabilite',

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
        // Sélecteurs Frappe v14/v15/v16 — du plus spécifique au plus large
        const selectors = [
            '.standard-sidebar-item',
            '.desk-sidebar-item',
            '.sidebar-item',
            '.workspace-sidebar-item',
            '.workspace-link',
            '.module-link',
            '.app-icon',
            '.desktop-icon',
            'li.sidebar-item',
            '.sidebar-menu-item',
        ];

        // 1. Cacher les conteneurs de sidebar items (méthode robuste)
        document.querySelectorAll(selectors.join(',')).forEach(el => {
            const text = (el.textContent || '').trim().toLowerCase();
            const href = (el.querySelector('a') || {}).href || '';
            const hrefLower = href.toLowerCase();
            if (terms.some(term => text.startsWith(term) || text.includes(term) || hrefLower.includes(term.replace(/\s/g, '-')))) {
                el.style.display = 'none';
                el.setAttribute('aria-hidden', 'true');
                // Cacher aussi le parent <li> si présent
                if (el.parentElement && el.parentElement.tagName === 'LI') {
                    el.parentElement.style.display = 'none';
                }
            }
        });

        // 2. Cacher les liens directs correspondants
        document.querySelectorAll('a[href]').forEach(el => {
            const href = (el.getAttribute('href') || '').toLowerCase();
            const text = (el.textContent || '').trim().toLowerCase();
            if (terms.some(term => href.includes(term.replace(/\s/g, '-')) || text === term)) {
                const parent = el.closest('.standard-sidebar-item, .sidebar-item, .workspace-sidebar-item, li') || el;
                parent.style.display = 'none';
                parent.setAttribute('aria-hidden', 'true');
            }
        });
    }

    // Injection CSS permanente pour les espaces strictement restreints
    // (fallback si le JS masquage arrive trop tard)
    function inject_restriction_css() {
        if (document.getElementById('kya-sidebar-restrictions')) return;
        const user_roles = (window.frappe && frappe.user_roles) || [];
        const stagiaire_roles = STAGIAIRE_WORKSPACE_ROLES;
        const can_stagiaire = stagiaire_roles.some(r => user_roles.includes(r));
        if (can_stagiaire) return; // a le droit, pas besoin de cacher

        const style = document.createElement('style');
        style.id = 'kya-sidebar-restrictions';
        // Cacher tout item de sidebar dont le lien ou le texte correspond
        style.textContent = [
            'a[href*="espace-stagiaires"]',
            'a[href*="espace_stagiaires"]',
            '.standard-sidebar-item:has(a[href*="stagiaire"])',
            '.sidebar-item:has(a[href*="stagiaire"])',
        ].join(',') + ' { display: none !important; }';
        document.head.appendChild(style);
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
        inject_restriction_css();
        hide_restricted_workspace_links();
        setTimeout(force_sidebar, 120);
        setTimeout(force_sidebar, 350);
        setTimeout(hide_restricted_workspace_links, 450);
        setTimeout(hide_restricted_workspace_links, 900);
    }

    if (window.frappe && frappe.router) {
        frappe.router.on('change', schedule_force_sidebar);
    }

    $(document).on('form-refresh page-change list-refresh', schedule_force_sidebar);
    $(document).ready(function() {
        inject_restriction_css();
        schedule_force_sidebar();
    });
    if (document.body) {
        new MutationObserver(function() {
            hide_restricted_workspace_links();
        }).observe(document.body, { childList: true, subtree: true });
    }
})();

import sys
sys.path.insert(0, '/home/frappe/frappe-bench/apps/frappe')
import frappe

site_name = sys.argv[1] if len(sys.argv) > 1 else 'frontend-test'
frappe.init(site=site_name)
frappe.connect()

print(f'--- Config DAAF & Comptable sur {site_name} ---')

# 1. Créer les rôles manquants
for role_name in ['DAAF', 'Comptable', 'Responsable Achats']:
    if not frappe.db.exists('Role', role_name):
        frappe.get_doc({'doctype': 'Role', 'role_name': role_name}).insert(ignore_permissions=True)
        print(f"Rôle créé : {role_name}")
    else:
        print(f"Rôle existant : {role_name}")

# 2. Mettre à jour le Workflow Achat si il existe
# On cherche le bon nom du workflow
wf_names = ['Achat / Dépense', 'Demande Achat KYA', 'KYA Achat', 'Purchase Request']
for wf_name in wf_names:
    if frappe.db.exists('Workflow', wf_name):
        wf = frappe.get_doc('Workflow', wf_name)
        print(f"\nWorkflow trouvé : {wf_name}")
        print("États actuels :", [s.state for s in wf.states])
        print("Transitions :", [(t.state, t.action, t.next_state, t.allowed) for t in wf.transitions])

        # Injection de la validation DAAF après Chef Service et avant DG
        # Ajouter état si absent
        states_names = [s.state for s in wf.states]
        if 'En attente DAAF' not in states_names:
            wf.append('states', {
                'state': 'En attente DAAF',
                'doc_status': 0,
                'allow_edit': 'DAAF'
            })

        # Reconstruire les transitions pour inclure DAAF
        # Trouver la transition qui saute directement à DG et l'intercepter
        new_transitions = []
        for t in wf.transitions:
            # Si une transition va vers "En attente du DG" depuis Chef Service, on la reroute vers DAAF
            if 'DG' in (t.next_state or '') and ('Chef' in (t.allowed or '') or 'Auditeur' in (t.allowed or '')):
                new_t = {
                    'state': t.state,
                    'action': t.action,
                    'next_state': 'En attente DAAF',
                    'allowed': t.allowed
                }
                new_transitions.append(new_t)
                print(f"  Rerouted: {t.state} → En attente DAAF (was {t.next_state})")
            else:
                new_transitions.append({
                    'state': t.state,
                    'action': t.action,
                    'next_state': t.next_state,
                    'allowed': t.allowed
                })

        # Ajouter transitions DAAF → DG si pas encore là
        existing_next = [(t['state'], t['next_state']) for t in new_transitions]
        dg_states = ['En attente du DG', 'En attente DGA', 'Approuvé']
        dg_next = next((s for s in dg_states if frappe.db.exists('Workflow State', s)), dg_states[0])

        if not any(t['state'] == 'En attente DAAF' for t in new_transitions):
            new_transitions.append({
                'state': 'En attente DAAF',
                'action': 'Approuver',
                'next_state': dg_next,
                'allowed': 'DAAF'
            })
            new_transitions.append({
                'state': 'En attente DAAF',
                'action': 'Rejeter',
                'next_state': 'Rejeté',
                'allowed': 'DAAF'
            })

        wf.transitions = []
        for t in new_transitions:
            wf.append('transitions', t)

        wf.save(ignore_permissions=True)
        print(f"Workflow '{wf_name}' mis à jour avec étape DAAF")

frappe.db.commit()
print('\n--- Terminé ---')

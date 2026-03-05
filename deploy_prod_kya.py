"""
deploy_prod_kya.py — Script maître de déploiement KYA HR
Applique toutes les configurations sur l'instance cible.
Usage: python deploy_prod_kya.py <nom_du_site>
Ex:    python deploy_prod_kya.py frontend
"""
import sys
sys.path.insert(0, '/home/frappe/frappe-bench/apps/frappe')
import frappe

site_name = sys.argv[1] if len(sys.argv) > 1 else 'frontend-test'
frappe.init(site=site_name)
frappe.connect()

print(f'\n{"="*60}')
print(f'  DÉPLOIEMENT KYA HR — Site: {site_name}')
print(f'{"="*60}\n')

# ═══════════════════════════════════════════════
# 1. CRÉATION DES RÔLES
# ═══════════════════════════════════════════════
roles_to_create = [
    'Responsable des Stagiaires',
    'Guérite',
    'Auditeur',
    'DAAF',
    'Comptable',
    'Responsable Achats',
]

print('[ RÔLES ]')
for role_name in roles_to_create:
    if not frappe.db.exists('Role', role_name):
        frappe.get_doc({'doctype': 'Role', 'role_name': role_name}).insert(ignore_permissions=True)
        print(f'  ✓ Créé : {role_name}')
    else:
        print(f'  · Existant : {role_name}')

# Renommer Agent de Sécurité → Guérite
if frappe.db.exists('Role', 'Agent de Sécurité'):
    try:
        frappe.rename_doc('Role', 'Agent de Sécurité', 'Guérite', force=True)
        print('  ✓ Renommé : Agent de Sécurité → Guérite')
    except Exception as e:
        print(f'  ! Renommage ignoré : {e}')

# ═══════════════════════════════════════════════
# 2. WORKFLOW PERMISSION DE SORTIE (STAGIAIRES — 3 NIVEAUX)
# ═══════════════════════════════════════════════
print('\n[ WORKFLOW PERMISSION STAGIAIRE ]')
if frappe.db.exists('Workflow', 'Permission de Sortie'):
    wf = frappe.get_doc('Workflow', 'Permission de Sortie')
    states_present = [s.state for s in wf.states]
    
    for state_def in [
        ('En attente du Supérieur Immédiat', 'Chef Service'),
        ('En attente du Responsable des Stagiaires', 'Responsable des Stagiaires'),
        ('En attente du DG', 'Directeur Général'),
        ('Approuvé', 'System Manager'),
        ('Rejeté', 'System Manager'),
    ]:
        if state_def[0] not in states_present:
            wf.append('states', {'state': state_def[0], 'doc_status': 0, 'allow_edit': state_def[1]})

    wf.transitions = []
    for t in [
        ('Brouillon', 'Soumettre', 'En attente du Supérieur Immédiat', 'Stagiaire'),
        ('En attente du Supérieur Immédiat', 'Approuver', 'En attente du Responsable des Stagiaires', 'Chef Service'),
        ('En attente du Supérieur Immédiat', 'Rejeter', 'Rejeté', 'Chef Service'),
        ('En attente du Responsable des Stagiaires', 'Approuver', 'En attente du DG', 'Responsable des Stagiaires'),
        ('En attente du Responsable des Stagiaires', 'Rejeter', 'Rejeté', 'Responsable des Stagiaires'),
        ('En attente du DG', 'Approuver', 'Approuvé', 'Directeur Général'),
        ('En attente du DG', 'Rejeter', 'Rejeté', 'Directeur Général'),
    ]:
        wf.append('transitions', {'state': t[0], 'action': t[1], 'next_state': t[2], 'allowed': t[3]})

    wf.save(ignore_permissions=True)
    print('  ✓ Permission de Sortie (3 niveaux) configuré')

# ═══════════════════════════════════════════════
# 3. FOOTER EMAIL KYA (ENTREPRISE — pas DG personnel)
# ═══════════════════════════════════════════════
print('\n[ NOTIFICATIONS EMAIL ]')

# Footer générique KYA Energy Group
kya_footer = """
<br>
<hr style="border:none; border-top:2px solid #009688; margin:20px 0;">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="font-family: Arial, sans-serif; font-size: 12px; color: #555;">
  <tr>
    <td width="100" style="vertical-align:middle; padding-right:15px;">
      <img src="https://www.kya-energy.com/wp-content/uploads/2024/02/Logo-10-ans-KYA.png"
           alt="KYA Energy Group" width="90" style="max-width:100%; display:block;">
    </td>
    <td style="vertical-align:middle; border-left:2px solid #009688; padding-left:15px;">
      <p style="margin:0; font-weight:bold; color:#009688; font-size:14px;">KYA-Energy Group</p>
      <p style="margin:2px 0;">08BP 81101 Agoe Nyive, Logopé — Lomé, Togo</p>
      <p style="margin:2px 0;">📞 +228 70 45 34 81 / 99 99 93 80</p>
      <p style="margin:2px 0;">✉️ <a href="mailto:info@kya-energy.com"
             style="color:#0056b3; text-decoration:none;">info@kya-energy.com</a>
         &nbsp;|&nbsp;
         <a href="https://www.kya-energy.com"
             style="color:#0056b3; text-decoration:none;">www.kya-energy.com</a></p>
    </td>
  </tr>
  <tr>
    <td colspan="2" style="padding-top:12px;">
      <img src="https://www.kya-energy.com/wp-content/uploads/2024/02/Affiche-KYA-SOP_Groupe-electrosolaire-1-1024x576.jpg"
           alt="KYA SOP" width="380" style="max-width:100%; display:block;">
    </td>
  </tr>
  <tr>
    <td colspan="2" style="padding-top:8px; font-size:10px; color:#999;">
      Ce message est généré automatiquement par le système RH de KYA-Energy Group.
      Merci de ne pas répondre directement à cet email.
    </td>
  </tr>
</table>
"""

notifications = frappe.get_all('Notification', filters={'name': ['like', 'KYA Notif%']})
updated = 0
for n in notifications:
    doc_n = frappe.get_doc('Notification', n.name)
    link_name = (doc_n.document_type or '').lower().replace(' ', '-')

    # Corps du message en français avec bouton d'action
    body = f"""
    <p style="font-family: Arial, sans-serif; color: #333;">Bonjour,</p>
    <p style="font-family: Arial, sans-serif; color: #333;">
        Une action est requise de votre part concernant le document
        <b>{doc_n.document_type} ({{{{doc.name}}}})</b>.<br>
        État actuel : <span style="color:#ff9800; font-weight:bold;">{{{{doc.workflow_state}}}}</span>
    </p>
    <p>
      <a href="/app/{link_name}/{{{{doc.name}}}}"
         style="display:inline-block; margin-top:10px; padding:10px 22px;
                background-color:#009688; color:#ffffff; text-decoration:none;
                border-radius:5px; font-family:Arial,sans-serif; font-weight:bold;">
        ➜ Accéder au Document
      </a>
    </p>
    {kya_footer}
    """

    doc_n.message = body
    doc_n.save(ignore_permissions=True)
    updated += 1

print(f'  ✓ {updated} notification(s) mise(s) à jour avec le footer KYA entreprise')

# ═══════════════════════════════════════════════
# 4. RESTRICTION DES WORKSPACES
# ═══════════════════════════════════════════════
print('\n[ WORKSPACES ]')
ws_config = [
    ('KYA Stagiaires', ['Stagiaire', 'Responsable des Stagiaires', 'HR Manager', 'HR User', 'System Manager']),
    ('Leaves', ['Employee', 'HR Manager', 'HR User', 'System Manager']),
]
for ws_name, roles in ws_config:
    if frappe.db.exists('Workspace', ws_name):
        ws = frappe.get_doc('Workspace', ws_name)
        ws.public = 0
        ws.roles = []
        for r in roles:
            ws.append('roles', {'role': r})
        ws.save(ignore_permissions=True)
        print(f'  ✓ {ws_name} restreint à : {", ".join(roles[:2])}...')

frappe.db.commit()
print(f'\n{"="*60}')
print('  DÉPLOIEMENT TERMINÉ ✓')
print(f'{"="*60}\n')

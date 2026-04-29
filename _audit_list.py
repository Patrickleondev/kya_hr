import json
files = [
    'kya_hr/doctype/planning_conge/planning_conge.json',
    'kya_hr/doctype/permission_sortie_employe/permission_sortie_employe.json',
    'kya_hr/doctype/permission_sortie_stagiaire/permission_sortie_stagiaire.json',
    'kya_hr/doctype/pv_sortie_materiel/pv_sortie_materiel.json',
    'kya_hr/doctype/demande_achat_kya/demande_achat_kya.json',
]
for f in files:
    d = json.load(open(f, encoding='utf-8'))
    print('===', f)
    print('  title_field:', d.get('title_field'))
    print('  search_fields:', d.get('search_fields'))
    cols = [fld['fieldname'] for fld in d.get('fields', []) if fld.get('in_list_view')]
    print('  in_list_view:', cols)
    has_ws = any(fld.get('fieldname') == 'workflow_state' for fld in d.get('fields', []))
    print('  has workflow_state field:', has_ws)

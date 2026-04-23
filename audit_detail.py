import json, os

for dt in ['pv_sortie_materiel', 'planning_conge', 'bilan_fin_de_stage', 'demande_achat_kya']:
    path = f'kya_hr/doctype/{dt}/{dt}.json'
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    fields = d.get('fields', [])
    print(f'\n=== {dt} ({len(fields)} champs) ===')
    for fn in fields:
        print(f"  {fn['fieldname']:40s} {fn['fieldtype']:20s} {fn.get('label','')}")

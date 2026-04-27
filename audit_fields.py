import json, os

DOCTYPES = [
    'permission_sortie_employe',
    'permission_sortie_stagiaire',
    'pv_sortie_materiel',
    'planning_conge',
    'demande_achat_kya',
    'bilan_fin_de_stage',
    'demande_conge_stagiaire',
]

CRITICAL = ['report_to', 'employee', 'employee_name']
SIG_PATTERNS = ['signature_', 'signataire_', 'date_signature_']

for dt in DOCTYPES:
    path = f'kya_hr/doctype/{dt}/{dt}.json'
    if not os.path.exists(path):
        print(f'  MISSING FILE: {path}')
        continue
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    fields = {fn['fieldname']: fn for fn in d.get('fields', [])}
    sigs = [fn for fn in fields if any(fn.startswith(p) for p in SIG_PATTERNS)]
    missing_critical = [c for c in CRITICAL if c not in fields]
    has_rt = 'OK' if 'report_to' in fields else 'MANQUANT'
    has_emp = 'OK' if 'employee' in fields else 'n/a'
    print(f'\n=== {dt} ===')
    print(f'  report_to : {has_rt}')
    print(f'  employee  : {has_emp}')
    print(f'  Signatures: {sigs}')
    if missing_critical:
        print(f'  MANQUANTS : {missing_critical}')

"""Conversion des modèles de contrats .docx vers fixtures KYA Contract Template.

Lit les fichiers du dossier `D:\\Stage_KYA_Energy\\RH\\Système de gestion des contrats`
et génère 6 fixtures JSON dans
`kya_hr/fixtures/kya_contract_template.json` (un par template).

Usage local :
    python -m kya_hr.maintenance.import_contract_templates

ou directement :
    python kya_hr/maintenance/import_contract_templates.py

Pré-requis :
    pip install mammoth python-docx

Pour les .doc anciens (CDI MASC/FEM), il faut d'abord les ouvrir dans
Word et les enregistrer en .docx, puis relancer le script.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import mammoth
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Mammoth manquant : pip install mammoth") from exc


# Source = dossier RH local. À adapter sur d'autres environnements.
SOURCE_DIR = Path(r"D:\Stage_KYA_Energy\RH\Système de gestion des contrats")
TARGET_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "kya_contract_template.json"
)

# Mapping fichier → métadonnées template KYA
TEMPLATE_SPECS = [
    {
        "file": "CONTRAT DE STAGE ACADEMIQUE.docx",
        "title": "Stage Académique — Standard",
        "contract_type": "Stage Académique",
        "genre_cible": "Tous",
        "version": "RH-ENG-V01",
    },
    {
        "file": "CONTRAT DE STAGE PROFESSIONNEL.docx",
        "title": "Stage Professionnel — Standard",
        "contract_type": "Stage Professionnel",
        "genre_cible": "Tous",
        "version": "RH-ENG-V01",
    },
    {
        "file": "CDD KYA FEM.docx",
        "title": "CDD — Féminin",
        "contract_type": "CDD",
        "genre_cible": "Féminin",
        "version": "RH-ENG-V01",
    },
    {
        "file": "CDD KYA MASC.docx",
        "title": "CDD — Masculin",
        "contract_type": "CDD",
        "genre_cible": "Masculin",
        "version": "RH-ENG-V01",
    },
    {
        "file": "CDI KYA FEM.docx",
        "title": "CDI — Féminin",
        "contract_type": "CDI",
        "genre_cible": "Féminin",
        "version": "RH-ENG-V01",
    },
    {
        "file": "CDI KYA MASC.docx",
        "title": "CDI — Masculin",
        "contract_type": "CDI",
        "genre_cible": "Masculin",
        "version": "RH-ENG-V01",
    },
]

# Remplacement des placeholders littéraux par des variables Jinja.
# L'ordre est important : remplacements longs en premier.
JINJA_SUBSTITUTIONS = [
    # Personne
    (r"Xxxxxxxxxxx", "{{ doc.employee_name }}"),
    (r"M\.\s*Xxxxxxxxxxx", "{{ 'Mme' if doc.sexe == 'Féminin' else 'M.' }} {{ doc.employee_name }}"),
    # Postes / fonctions
    (r"poste de xxxxxxx", "poste de {{ doc.poste or 'xxxxxxx' }}"),
    # Salaire
    (r"de xxxxxxxxx \(chiffre\) francs CFA", "de {{ doc.salaire_mensuel or '____________' }} ({{ doc.salaire_mensuel or '____________' }}) francs CFA"),
    # Dates contrat
    (r"prend effet pour compter du xxxxxxxxx", "prend effet pour compter du {{ frappe.format_date(doc.date_debut) if doc.date_debut else 'xxxxxxxxx' }}"),
    (r"arrive à échéance le\s+xxxxxx", "arrive à échéance le {{ frappe.format_date(doc.date_fin) if doc.date_fin else 'xxxxxx' }}"),
    (r"prend effet au xxxxxx", "prend effet au {{ frappe.format_date(doc.date_debut) if doc.date_debut else 'xxxxxx' }}"),
    (r"arriver à terme le xxxxxxxxx", "arriver à terme le {{ frappe.format_date(doc.date_essai_fin) if doc.date_essai_fin else 'xxxxxxxxx' }}"),
    # Tâches
    (r"xxxxxxxxxxxxxxxxxxxxxxxxx", "{{ doc.taches_resume or 'À préciser' }}"),
]


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value or "template"


def docx_to_html(path: Path) -> str:
    with path.open("rb") as fp:
        result = mammoth.convert_to_html(fp)
    html = result.value or ""
    # Nettoyage XML
    html = re.sub(r"<\?xml[^>]*\?>", "", html)
    # Supprimer les images embarquées en data: URI (logos déjà ajoutés par le print format)
    html = re.sub(r'<img[^>]*src=["\']data:[^"\']+["\'][^>]*/?>', "", html)
    # Supprimer les <table> d'en-tête vides résultantes (logo + slogan)
    html = re.sub(r'<table[^>]*>\s*<thead>\s*<tr>\s*<th[^>]*>\s*<p>\s*</p>\s*</th>.*?</thead>\s*</table>', "", html, flags=re.S)
    return html


def apply_jinja_substitutions(html: str) -> str:
    for pattern, replacement in JINJA_SUBSTITUTIONS:
        html = re.sub(pattern, replacement, html)
    return html


def build_fixtures():
    fixtures = []
    missing = []
    errors = []
    for spec in TEMPLATE_SPECS:
        source = SOURCE_DIR / spec["file"]
        if not source.exists():
            missing.append(spec["file"])
            continue
        try:
            html = docx_to_html(source)
        except Exception as exc:  # fichier corrompu ou format inattendu
            errors.append((spec["file"], str(exc)))
            continue
        html = apply_jinja_substitutions(html)
        fixtures.append({
            "doctype": "KYA Contract Template",
            "name": spec["title"],
            "title": spec["title"],
            "contract_type": spec["contract_type"],
            "genre_cible": spec["genre_cible"],
            "version": spec["version"],
            "is_active": 1,
            "html_body": html,
        })
    return fixtures, missing, errors


def main():
    fixtures, missing, errors = build_fixtures()
    TARGET_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    with TARGET_FIXTURE.open("w", encoding="utf-8") as fp:
        json.dump(fixtures, fp, ensure_ascii=False, indent=2)
    print(f"OK : {len(fixtures)} templates ecrits -> {TARGET_FIXTURE}")
    if missing:
        print("\nFichiers MANQUANTS (.doc a convertir en .docx via Word puis relancer) :")
        for name in missing:
            print(f"  - {name}")
    if errors:
        print("\nFichiers EN ERREUR (corrompus, re-enregistrer depuis Word) :")
        for name, msg in errors:
            print(f"  - {name}: {msg}")


if __name__ == "__main__":
    main()

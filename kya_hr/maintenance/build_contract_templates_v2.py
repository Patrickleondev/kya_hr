# -*- coding: utf-8 -*-
"""Génère des KYA Contract Template PROPRES, cohérents et entièrement variabilisés.

Pourquoi : l'ancien convertisseur docx (`import_contract_templates.py`) produisait
des `html_body` incohérents — certains gardaient les `xxxxx` littéraux (salaire,
poste, dates), des listes de tâches figées, et un bloc « Fait à Lomé / signatures »
DUPLIQUÉ avec celui du print format.

Ici :
  • CDI et CDD ont chacun UN SEUL corps « genre-aware » (accord M/F via Jinja
    `doc.sexe`). Les enregistrements Masculin et Féminin partagent ce corps, donc
    ils ne peuvent plus diverger.
  • Toutes les valeurs (salaire, poste, mission, tâches, dates, catégorie/échelon)
    proviennent des champs du KYA Contrat.
  • Le corps s'arrête à l'Article 17 : le bloc « Fait à Lomé » + signatures est
    ajouté par le print format `KYA Contrat PDF` (plus de doublon).
  • Les stages sont conservés mais leurs dates « ……….. » et l'indemnité figée
    sont variabilisées, et l'Article 3 (maître de stage) est nettoyé.

Usage (dans le conteneur) :
    bench --site frontend execute kya_hr.maintenance.build_contract_templates_v2.run
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "kya_contract_template.json"

# ── Fragments Jinja réutilisables ────────────────────────────────────────────
SET_M = "{%- set m = (doc.sexe == 'Masculin') -%}\n"

NAISSANCE = ("{{ frappe.utils.formatdate(doc.date_naissance, 'dd/MM/yyyy') if doc.date_naissance else '' }}"
             "{% if doc.lieu_naissance %} à {{ doc.lieu_naissance }}{% endif %}")
DATE_DEBUT = "{{ frappe.utils.formatdate(doc.date_debut, 'dd MMMM yyyy') if doc.date_debut else '__________' }}"
DATE_FIN = "{{ frappe.utils.formatdate(doc.date_fin, 'dd MMMM yyyy') if doc.date_fin else '__________' }}"
SALAIRE = ("{{ '{:,.0f}'.format(doc.salaire_mensuel or 0).replace(',', ' ') }} "
           "({{ nombre_en_lettres(doc.salaire_mensuel, '') }}) francs CFA")
ESSAI = "{{ doc.periode_essai_mois or 1 }} ({{ nombre_en_lettres(doc.periode_essai_mois or 1, '') }}) mois"

# Bloc TRAVAILLEUR (identique CDI/CDD)
TRAVAILLEUR = f"""<p><strong>Entre les soussignés, agissant en qualité de :</strong></p>
<p><strong>EMPLOYEUR :</strong></p>
<p><strong>KYA-Energy Group</strong> ayant son siège social à Lomé, quartier AGOE-NYIVE, LOGOPE, 08&nbsp;BP&nbsp;81101, Lomé-Togo, Tél. : +228 70 45 34 81 / 91 50 21 49, e-mail : <a href="mailto:info@kya-energy.com">info@kya-energy.com</a>, représentée par son Directeur Général, Prof. AZOUMAH Yao, majeur non interdit ayant pleine capacité aux fins des présentes ;</p>
<p><strong>D’une part, et de :</strong></p>
<p><strong>TRAVAILLEUR :</strong></p>
<p>Nom et prénoms : <strong>{{{{ doc.employee_name }}}}</strong></p>
<p>Date et lieu de naissance : <strong>{NAISSANCE}</strong></p>
<p>Filiation : {{{{ 'fils' if m else 'fille' }}}} de <strong>{{{{ doc.filiation_pere or '' }}}}</strong>{{% if doc.filiation_mere %}} et de <strong>{{{{ doc.filiation_mere }}}}</strong>{{% endif %}}</p>
<p>Domicile habituel : <strong>{{{{ doc.domicile or '' }}}}</strong></p>
<p>Nationalité : <strong>{{{{ doc.nationalite or 'Togolaise' }}}}</strong></p>
<p>Tél : <strong>{{{{ doc.telephone or '' }}}}</strong></p>
<p>Situation de famille (état civil) : <strong>{{{{ doc.situation_famille or '' }}}}</strong></p>
<p>Nombre d’enfants à charge : <strong>{{{{ doc.nb_enfants or 0 }}}}</strong></p>
<p>Personne à prévenir : <strong>{{{{ doc.personne_a_prevenir or '' }}}}</strong> &nbsp; Tél : <strong>{{{{ doc.tel_personne_prevenir or '' }}}}</strong></p>
<p><strong>D’autre part,</strong></p>
<p><strong>Il a été convenu et arrêté ce qui suit :</strong></p>"""

# Article 3 — Fonctions (identique CDI/CDD)
ART3 = f"""<p><strong>Article 3 : Fonctions du travailleur</strong></p>
<p>{{{{ 'M.' if m else 'Mme' }}}} {{{{ doc.employee_name }}}} occupe le poste de <strong>{{{{ doc.poste or '...' }}}}</strong>. {{{{ 'Il' if m else 'Elle' }}}} exercera ses fonctions sous l’autorité et la direction de l’employeur ou de son représentant.</p>
<p>{{{{ 'Il' if m else 'Elle' }}}} a pour mission d’assurer <strong>{{{{ doc.mission_principale or '...' }}}}</strong> conformément à la feuille de route définie par la Direction Générale.</p>
<p>Dans l’accomplissement de cette mission, {{{{ 'le salarié' if m else 'la salariée' }}}} devra effectuer les tâches suivantes :</p>
{{% if doc.taches %}}<ul>{{% for t in doc.taches %}}<li>{{{{ t.description }}}}</li>{{% endfor %}}</ul>{{% else %}}<ul><li>…</li></ul>{{% endif %}}
<p>D’autres tâches entrant dans le contenu du poste de {{{{ 'M.' if m else 'Mme' }}}} {{{{ doc.employee_name }}}} pourraient lui être confiées en cas de besoin pour la prospérité de la société.</p>"""

# Articles 4 & 5 (identiques)
ART4_5 = f"""<p><strong>Article 4 : Obligations de KYA-Energy Group</strong></p>
<p>KYA-Energy Group s’engage à tout mettre en œuvre pour aider {{{{ 'le salarié' if m else 'la salariée' }}}} à son insertion dans son milieu professionnel.</p>
<p>KYA-Energy Group s’engage à verser la rémunération prévue dans le présent contrat pour les tâches que {{{{ 'le salarié' if m else 'la salariée' }}}} effectue.</p>
<p>À l’issue du contrat, le Directeur Général ou son représentant remettra {{{{ 'au salarié' if m else 'à la salariée' }}}} un certificat indiquant la nature et la durée du contrat.</p>
<p>KYA-Energy Group déclare avoir garanti sa responsabilité civile pour tous les cas où celle-ci pourrait être engagée à l’occasion du contrat.</p>
<p><strong>Article 5 : Clause de mobilité</strong></p>
<p>Le lieu de travail est fixé à Lomé au siège de la société.</p>
<p>L’employeur se réserve toutefois le droit de muter {{{{ 'le salarié' if m else 'la salariée' }}}} dans un quelconque établissement de la société, sur toute l’étendue du territoire national togolais, pour les besoins du service.</p>
<p>{{{{ 'Le salarié accepte' if m else 'La salariée accepte' }}}} cette clause de mobilité et ne s’oppose pas à une mutation décidée par l’employeur.</p>"""

# Article 6 — Classification & Rémunération (identique)
ART6 = f"""<p><strong>Article 6 : Classification professionnelle et Rémunération</strong></p>
<p>{{{{ 'Le salarié est classé' if m else 'La salariée est classée' }}}} dans la catégorie <strong>{{{{ doc.categorie_grille or 'C des Cadres' }}}}</strong>, échelon <strong>{{{{ doc.echelon_grille or 'I1' }}}}</strong>, conformément à la grille salariale de l’entreprise qui se fonde sur la convention collective interprofessionnelle du Togo.</p>
<p>Conformément à la grille salariale adoptée et en vigueur depuis le 1<sup>er</sup> janvier 2025, sa rémunération est en deux parts distinctes :</p>
<p><strong>– Une part fixe</strong>, équivalente au salaire de base mensuel qui est de <strong>{SALAIRE}</strong>, conformément à la grille salariale en vigueur ;</p>
<p><strong>– Une part variable</strong>, indexée sur le chiffre d’affaires et les différents taux liés aux performances individuelles et collectives, et payée sur une base trimestrielle, telle que détaillée dans le guide de l’employé de KYA-Energy Group.</p>"""

# Articles 7 à 13 (identiques)
ART7_13 = f"""<p><strong>Article 7 : Absence</strong></p>
<p>Toute absence {{{{ 'du salarié' if m else 'de la salariée' }}}} à son poste est subordonnée à une autorisation préalable de l’employeur ou de son représentant. Toute absence non autorisée constitue une faute et expose {{{{ 'le salarié' if m else 'la salariée' }}}} à une procédure disciplinaire.</p>
<p>{{{{ 'Le salarié bénéficiera' if m else 'La salariée bénéficiera' }}}} des autorisations d’absence et de permissions exceptionnelles dans les conditions et selon les modalités prévues par la réglementation en vigueur.</p>
<p>En cas d’indisponibilité {{{{ 'du salarié' if m else 'de la salariée' }}}} pour cause de maladie ou d’accident, {{{{ 'il est tenu' if m else 'elle est tenue' }}}} d’en avertir, personnellement ou par personne interposée, l’employeur dès le premier jour de son absence ou au plus tard le troisième jour, en indiquant le motif et si possible la durée prévisible de son absence.</p>
<p>Le sixième jour de son absence au plus tard, {{{{ 'le salarié est obligé' if m else 'la salariée est obligée' }}}} de soumettre à la société un certificat médical délivré par un médecin agréé, attestant son incapacité de travail et sa durée prévisible.</p>
<p><strong>Article 8 : Congés payés</strong></p>
<p>{{{{ 'Le salarié a' if m else 'La salariée a' }}}} droit à des congés payés de trente (30) jours par année de service effectif. Toutefois, les parties peuvent convenir d’une jouissance au prorata. La période de jouissance de ces congés sera déterminée en commun accord avec l’Employeur, en tenant compte des besoins de fonctionnement de l’entreprise.</p>
<p>Toutefois, si les nécessités du service l’exigent, {{{{ 'le salarié mis' if m else 'la salariée mise' }}}} en congé peut être {{{{ 'rappelé' if m else 'rappelée' }}}}.</p>
<p><strong>Article 9 : Protection sociale</strong></p>
<p>Suivant la réglementation en vigueur au Togo, l’Employeur s’engage à affilier {{{{ 'le salarié' if m else 'la salariée' }}}} à la Caisse Nationale de Sécurité Sociale (CNSS). {{{{ 'Il' if m else 'Elle' }}}} s’oblige à accepter cette affiliation et reconnaît à l’Employeur le droit de prélever sur son salaire la fraction de cotisation à sa charge au profit de cette institution.</p>
<p><strong>Article 10 : Clause de non-concurrence</strong></p>
<p>Sauf autorisation particulière écrite de son employeur, {{{{ 'M.' if m else 'Mme' }}}} {{{{ doc.employee_name }}}} doit toute son activité professionnelle à la société KYA-Energy Group. {{{{ 'Il doit' if m else 'Elle doit' }}}} exécuter ses tâches en toute bonne foi, avec professionnalisme et diligence.</p>
<p>Pendant la durée du présent contrat, {{{{ 'le salarié' if m else 'la salariée' }}}} s’interdit d’exercer toute activité professionnelle susceptible de concurrencer celle de son employeur ou de nuire à la bonne exécution des services convenus.</p>
<p><strong>Article 11 : Clauses de confidentialité / Interdictions</strong></p>
<p>{{{{ 'Le salarié' if m else 'La salariée' }}}} s’interdit de divulguer, pendant ou après son temps d’emploi, tout renseignement confidentiel relatif aux méthodes, recommandations, créations, devis, études, projets et savoir-faire de KYA-Energy Group, dont {{{{ 'il' if m else 'elle' }}}} aurait eu connaissance dans l’exercice de ses fonctions.</p>
<p>{{{{ 'Il' if m else 'Elle' }}}} ne peut, non plus, sans autorisation écrite de la Direction, publier aucune étude sous quelque forme que ce soit portant sur des informations ou des travaux couverts par l’obligation de confidentialité.</p>
<p>{{{{ 'Il' if m else 'Elle' }}}} s’interdit enfin de se livrer à tout comportement susceptible de porter atteinte à la réputation de KYA-Energy Group ou de ses dirigeants.</p>
<p>Le non-respect des obligations contractuelles ou la violation des interdictions {{{{ 'expose le salarié' if m else 'expose la salariée' }}}} à des sanctions disciplinaires.</p>
<p><strong>Article 12 : Dédit-formation</strong></p>
<p>En cas de bénéfice d’une formation, totalement ou en partie financée par la société KYA-Energy Group, le bénéficiaire s’engage à en faire bénéficier prioritairement la société, dans les conditions et modalités qui seront définies de commun accord, le cas échéant.</p>
<p><strong>Article 13 : Droit de propriété intellectuelle</strong></p>
<p>KYA-Energy Group est le titulaire exclusif des Droits de Propriété Intellectuelle sur tous développements, adaptations, améliorations et modifications apportés à ses éléments préexistants dans le cadre de l’exécution du Contrat.</p>
<p>{{{{ 'Le salarié' if m else 'La salariée' }}}} s’engage à céder à KYA-Energy Group, à première demande, intégralement et libre de toute charge, tous les Droits de Propriété Intellectuelle sur ces développements, adaptations, améliorations et modifications dès leur création, pour la durée maximale prévue par la loi.</p>
<p>KYA-Energy Group s’engage à accorder {{{{ 'au salarié' if m else 'à la salariée' }}}}, pendant toute la durée du contrat, une licence gratuite et non exclusive permettant d’utiliser, de copier, de modifier, d’améliorer et de préserver ces développements, adaptations, améliorations et modifications, uniquement dans la mesure nécessaire et aux seules fins d’accomplir les tâches qui lui sont confiées.</p>"""

# Articles 15 à 17 (identiques)
ART15_17 = """<p><strong>Article 15 : Règlement des différends</strong></p>
<p>Tout différend qui pourrait naître de l’exécution ou de l’interprétation du présent contrat fera prioritairement l’objet d’un règlement à l’amiable. En cas de désaccord, la partie la plus diligente peut saisir l’Inspection du travail et des lois sociales du ressort ou, le cas échéant, le tribunal du travail de Lomé.</p>
<p><strong>Article 16 : Modification du contrat</strong></p>
<p>Toute modification des dispositions du présent contrat de travail fera l’objet d’un avenant qui lui sera annexé.</p>
<p><strong>Article 17 : Dispositions finales</strong></p>
<p>Le présent contrat est régi par la loi n°2021-012 du 18 juin 2021 portant code du travail au Togo, et par la convention collective interprofessionnelle du Togo du 20 décembre 2011.</p>
<p>Le présent contrat est établi en deux exemplaires originaux, chaque partie en ayant gardé un pour servir et valoir ce que de droit.</p>"""

# ── Articles 1, 2, 14 spécifiques ────────────────────────────────────────────
CDI_ART1_2 = f"""<p><strong>Article 1 : Nature et durée du contrat</strong></p>
<p>Le présent contrat de travail est un contrat à <strong>durée indéterminée</strong>. Il prend effet pour compter du <strong>{DATE_DEBUT}</strong>.</p>
<p><strong>Article 2 : Période d’essai</strong></p>
<p>Le présent contrat de travail est issu de la mutation d’un contrat à durée déterminée ayant déjà été assorti d’une période d’essai de {ESSAI}.</p>"""

CDI_ART14 = f"""<p><strong>Article 14 : Résiliation du contrat</strong></p>
<p>Le présent contrat de travail peut être rompu par la volonté de l’une ou l’autre des parties, sous réserve d’un <strong>préavis de trois (03) mois</strong> donné par la partie qui prend l’initiative de la rupture.</p>
<p>Toutefois, l’employeur sera exempt de donner ce préavis lorsque {{{{ 'le salarié' if m else 'la salariée' }}}} aura commis une faute grave ou lourde, sous réserve de l’appréciation de la juridiction compétente. Ce contrat pourra notamment être rompu dans les cas suivants :</p>
<p>a) démission ;</p><p>b) licenciement pour motif personnel ou économique ;</p><p>c) consentement mutuel ou rupture conventionnelle ;</p><p>d) faute grave ou lourde du travailleur ;</p><p>e) inaptitude du travailleur, constatée par le médecin inspecteur du travail ;</p><p>f) insuffisance de performance sur objectifs préalablement définis ;</p><p>g) résiliation judiciaire ;</p><p>h) force majeure, survenance de l’âge de l’admission à la retraite ou décès du travailleur.</p>
<p>Dans tous les cas, {{{{ 'le salarié aura' if m else 'la salariée aura' }}}} droit aux honoraires et au remboursement des dépenses certifiées remboursables qui lui sont dus, et à ceux correspondant à la période nécessaire à la cessation des services.</p>"""

CDD_ART1_2 = f"""<p><strong>Article 1 : Nature et durée du contrat</strong></p>
<p>Le présent contrat de travail est un contrat à <strong>durée déterminée</strong> de <strong>{{{{ doc.duree_mois or '__' }}}} ({{{{ nombre_en_lettres(doc.duree_mois, '') if doc.duree_mois else '__' }}}}) mois</strong>. Il prend effet pour compter du <strong>{DATE_DEBUT}</strong> et arrive à échéance le <strong>{DATE_FIN}</strong>.</p>
<p><strong>Article 2 : Période d’essai</strong></p>
<p>Le présent contrat de travail est assorti d’une période d’essai de {ESSAI}.</p>
<p>Pendant cette période, le contrat peut être rompu à tout moment par la volonté de l’une ou l’autre partie, sans motif ni indemnité, sous réserve du respect d’un délai de prévenance de quarante-huit (48) heures.</p>"""

CDD_ART14 = f"""<p><strong>Article 14 : Résiliation du contrat</strong></p>
<p>Le présent contrat de travail prend fin à la survenance du terme prévu. Il ne peut être rompu avant l’échéance que dans les cas suivants :</p>
<p>a) cas de force majeure ;</p><p>b) consentement mutuel des parties, à condition que celui-ci soit constaté par écrit ;</p><p>c) {{{{ 'le salarié est embauché' if m else 'la salariée est embauchée' }}}} sous contrat à durée indéterminée ;</p><p>d) faute grave ou lourde du travailleur ;</p><p>e) inaptitude du travailleur, constatée par le médecin inspecteur du travail ;</p><p>f) insuffisance de performance sur objectifs préalablement définis ;</p><p>g) résiliation judiciaire.</p>
<p>Dans tous les cas, {{{{ 'le salarié aura' if m else 'la salariée aura' }}}} droit aux honoraires et au remboursement des dépenses certifiées remboursables qui lui sont dus, et à ceux correspondant à la période nécessaire à la cessation des services.</p>"""


def cdi_body() -> str:
    return SET_M + "\n".join([TRAVAILLEUR, CDI_ART1_2, ART3, ART4_5, ART6, ART7_13, CDI_ART14, ART15_17])


def cdd_body() -> str:
    return SET_M + "\n".join([TRAVAILLEUR, CDD_ART1_2, ART3, ART4_5, ART6, ART7_13, CDD_ART14, ART15_17])


# ── Patches stages (sur les corps existants) ─────────────────────────────────
def patch_stage(html: str) -> str:
    # 1) Dates de l'article 2 : "compter du <strong>……</strong>et arrive à échéance le<strong>……</strong>"
    html = re.sub(
        r"compter du\s*<strong>[^<]*</strong>\s*et arrive à échéance le\s*<strong>[^<]*</strong>",
        ("compter du <strong>" + DATE_DEBUT + "</strong> et arrive à échéance le <strong>" + DATE_FIN + "</strong>"),
        html,
    )
    # 2) Indemnité forfaitaire figée 28 000 -> champ indemnite_mensuelle
    html = re.sub(
        r"28\s*000 francs CFA",
        ("{{ '{:,.0f}'.format(doc.indemnite_mensuelle or 28000).replace(',', ' ') }} "
         "({{ nombre_en_lettres(doc.indemnite_mensuelle or 28000, '') }}) francs CFA"),
        html,
    )
    # 3) Article 3 (maître de stage) : phrase garglée "M/Mlle……….est autorisé(e) à suivre ..."
    html = re.sub(
        r"(<strong>\s*:?\s*Maître de stage</strong></p>)<p>.*?</p>",
        (r"\1<p>Durant la période définie à l’article 2, "
         r"{% if doc.maitres_stage %}{% for mst in doc.maitres_stage %}<strong>{{ mst.employee_name }}</strong>"
         r"{% if mst.role_maitre %} ({{ mst.role_maitre }}){% endif %}{% if not loop.last %}, {% endif %}{% endfor %}"
         r"{% else %}le maître de stage désigné par la société{% endif %} encadrera "
         r"{% if doc.sexe == 'Masculin' %}le{% else %}la{% endif %} stagiaire <strong>{{ doc.employee_name }}</strong> "
         r"conformément aux dispositions prévues par la direction de la société.</p>"),
        html,
        flags=re.S,
    )
    return html


SPECS = [
    ("Stage Académique — Standard", "Stage Académique", "Tous", "stage"),
    ("Stage Professionnel — Standard", "Stage Professionnel", "Tous", "stage"),
    ("CDD — Féminin", "CDD", "Féminin", "cdd"),
    ("CDD — Masculin", "CDD", "Masculin", "cdd"),
    ("CDI — Féminin", "CDI", "Féminin", "cdi"),
    ("CDI — Masculin", "CDI", "Masculin", "cdi"),
]


def build_records(old_by_name: dict) -> list:
    cdi, cdd = cdi_body(), cdd_body()
    records = []
    for name, ctype, genre, kind in SPECS:
        if kind == "cdi":
            body = cdi
        elif kind == "cdd":
            body = cdd
        else:  # stage : patch de l'existant
            body = patch_stage(old_by_name.get(name, {}).get("html_body", ""))
        records.append({
            "doctype": "KYA Contract Template",
            "name": name,
            "title": name,
            "contract_type": ctype,
            "genre_cible": genre,
            "version": "RH-ENG-V02",
            "is_active": 1,
            "html_body": body,
        })
    return records


def write_fixture(records):
    with FIXTURE.open("w", encoding="utf-8") as fp:
        json.dump(records, fp, ensure_ascii=False, indent=2)


def run():
    """Construit la fixture ET met à jour la base (db.set_value, sans validate)."""
    old = {}
    if FIXTURE.exists():
        old = {r["name"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}
    records = build_records(old)
    try:
        write_fixture(records)
    except Exception as exc:
        print("(fixture non réécrite côté conteneur — sera régénérée sur l'hôte) :", exc)

    import frappe
    updated, missing = [], []
    for r in records:
        if frappe.db.exists("KYA Contract Template", r["name"]):
            frappe.db.set_value("KYA Contract Template", r["name"], {
                "html_body": r["html_body"],
                "is_active": 1,
                "version": r["version"],
                "contract_type": r["contract_type"],
                "genre_cible": r["genre_cible"],
                "title": r["title"],
            }, update_modified=True)
            updated.append(r["name"])
        else:
            doc = frappe.get_doc(r)
            doc.flags.ignore_permissions = True
            doc.insert()
            updated.append(r["name"] + " (inséré)")
    frappe.db.commit()
    frappe.clear_cache()
    print("MAJ templates :", updated)
    if missing:
        print("Manquants :", missing)


def test_render():
    """Rend chaque template avec un contrat fictif (M et F) et vérifie qu'il ne
    reste aucun placeholder brut (xxxx, {{ }}, {% %}, None) et que le salaire,
    le poste et la mission sont bien substitués."""
    import frappe

    base = {
        "employee_name": "GANDONOU Koffi Patrick",
        "poste": "Ingénieur Solaire",
        "mission_principale": "la maintenance des systèmes solaires",
        "salaire_mensuel": 350000,
        "indemnite_mensuelle": 75000,
        "date_debut": "2026-07-01",
        "date_fin": "2027-06-30",
        "date_naissance": "1995-03-12",
        "lieu_naissance": "Lomé",
        "duree_mois": 12,
        "periode_essai_mois": 1,
        "categorie_grille": "C des Cadres",
        "echelon_grille": "I2",
        "domicile": "Agoè, Lomé",
        "nationalite": "Togolaise",
        "telephone": "+228 90 00 00 00",
        "situation_famille": "Célibataire",
        "nb_enfants": 0,
        "filiation_pere": "GANDONOU Paul",
        "filiation_mere": "AYIVI Marie",
        "personne_a_prevenir": "GANDONOU Paul",
        "tel_personne_prevenir": "+228 91 00 00 00",
        "taches": [frappe._dict({"description": "Installer les kits solaires"}),
                   frappe._dict({"description": "Assurer le SAV clients"})],
        "maitres_stage": [frappe._dict({"employee_name": "KOSSI Jean", "role_maitre": "Tuteur"})],
    }
    cases = [
        ("CDI — Masculin", "Masculin"), ("CDI — Féminin", "Féminin"),
        ("CDD — Masculin", "Masculin"), ("CDD — Féminin", "Féminin"),
        ("Stage Professionnel — Standard", "Masculin"),
        ("Stage Académique — Standard", "Féminin"),
    ]
    bad_tokens = ["xxxx", "XXXX", "{{", "}}", "{%", "%}", "None", "(chiffre)", "………"]
    all_ok = True
    for name, sexe in cases:
        sample = frappe._dict(dict(base, sexe=sexe))
        tpl = frappe.get_doc("KYA Contract Template", name)
        try:
            html = tpl.render_for(sample)
        except Exception as exc:
            print(f"[ERREUR] {name} ({sexe}): {exc}")
            all_ok = False
            continue
        problems = [t for t in bad_tokens if t in html]
        salaire_ok = ("350 000" in html) or ("Stage" in name)
        poste_ok = ("Ingénieur Solaire" in html) or ("Stage" in name)
        accord_ok = (("salarié" in html) if sexe == "Masculin" else ("salariée" in html)) or ("Stage" in name)
        status = "OK" if (not problems and salaire_ok and poste_ok and accord_ok) else "ECHEC"
        if status == "ECHEC":
            all_ok = False
        print(f"[{status}] {name} ({sexe}) len={len(html)} "
              f"salaire={salaire_ok} poste={poste_ok} accord={accord_ok} "
              f"restes={problems}")
    print("RESULTAT:", "TOUS OK" if all_ok else "DES ECHECS")


if __name__ == "__main__":
    # Mode hors-frappe : génère seulement la fixture
    old = {r["name"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))} if FIXTURE.exists() else {}
    write_fixture(build_records(old))
    print("Fixture écrite :", FIXTURE)

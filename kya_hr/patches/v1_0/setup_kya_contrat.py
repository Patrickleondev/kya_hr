"""Setup KYA Contrat — Workflow, Workflow States/Actions, Role, Templates seed.

Idempotent. Exécuté via patches.txt après installation des DocTypes.
"""
import frappe


WORKFLOW_NAME = "Flux KYA Contrat"
DOCTYPE = "KYA Contrat"

STATES = [
    # Anciens (legacy — conservés pour rétro-compat)
    ("Brouillon", "Pending", 0),
    ("Envoyé Signataire", "Warning", 0),
    ("Signé Employé", "Info", 0),
    ("Signé DG", "Success", 1),
    ("Finalisé", "Success", 1),
    ("Annulé", "Danger", 2),
    # Nouveaux (Flux Contrat KYA — fixture)
    ("En attente Signature Salarié", "Warning", 0),
    ("Signé Salarié", "Info", 0),
    ("En attente DG", "Warning", 0),
    ("Validé", "Success", 1),
    ("RH (revue)", "Info", 1),
    ("Archivé", "Success", 1),
    ("Rejeté", "Danger", 2),
]

ACTIONS = [
    "Envoyer au Signataire", "Signer", "Co-signer", "Finaliser", "Annuler",
    "Envoyer au Salarié", "Soumettre au DG", "Valider", "Rejeter",
    "Marquer revue RH", "Archiver", "Refuser",
]


def execute():
    _ensure_role("KYA Signataire Contrat", desk_access=0)
    _ensure_role("Directeur Général")
    _ensure_role("Responsable RH")
    _ensure_workflow_states()
    _ensure_workflow_actions()
    _disable_legacy_workflow()
    _seed_templates()
    frappe.db.commit()


def _ensure_role(role_name, desk_access=1):
    if not frappe.db.exists("Role", role_name):
        r = frappe.new_doc("Role")
        r.role_name = role_name
        r.desk_access = desk_access
        r.insert(ignore_permissions=True)


def _ensure_workflow_states():
    for state, style, _ in STATES:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(ignore_permissions=True)


def _ensure_workflow_actions():
    for a in ACTIONS:
        if not frappe.db.exists("Workflow Action Master", a):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert(ignore_permissions=True)


def _disable_legacy_workflow():
    """L'ancien workflow 'Flux KYA Contrat' utilisait des noms d'états divergents
    (Envoyé Signataire / Signé Employé / Finalisé). Il est remplacé par le
    fixture 'Flux Contrat KYA' (RH → Salarié → RH → DG). On désactive l'ancien
    pour éviter les conflits de double workflow sur le même DocType.
    """
    if frappe.db.exists("Workflow", "Flux KYA Contrat"):
        try:
            frappe.db.set_value("Workflow", "Flux KYA Contrat", "is_active", 0)
        except Exception:
            pass


# ----- Seed des 5 templates par défaut -----

TPL_STAGE_PRO = """<div>
<p><b>Entre</b></p>
<p><b>KYA-Energy Group</b>, ayant son siège social à Lomé (Togo), 08 BP 81101 AGOENYIVE LOGOPE,
représenté par son Directeur Général <b>{{ doc.nom_dg }}</b>, d'une part ;</p>
<p><b>Et</b></p>
<p>M./Mme <b>{{ doc.employee_name }}</b>, né(e) le {{ frappe.format_date(doc.date_naissance) }},
demeurant à {{ doc.domicile or '...' }},
fils/fille de {{ doc.filiation_pere or '...' }} et de {{ doc.filiation_mere or '...' }},
téléphone : {{ doc.telephone or '...' }},
dénommé(e) « <b>STAGIAIRE</b> », d'autre part ;</p>
<p><i>Il a été convenu et arrêté ce qui suit :</i></p>

<h3>Article 1 — Nature du stage</h3>
<p>KYA-Energy Group accepte de faire bénéficier au stagiaire, sur sa demande,
un <b>stage professionnel</b> au sein de ses services.</p>

<h3>Article 2 — Durée</h3>
<p>La présente convention est prévue pour une durée de <b>{{ doc.duree_mois }} mois</b>.
Elle prend effet à compter du <b>{{ frappe.format_date(doc.date_debut) }}</b>
et arrive à échéance le <b>{{ frappe.format_date(doc.date_fin) }}</b>.</p>

<h3>Article 3 — Maîtres de stage</h3>
<p>Durant la période ci-dessus,
{% for m in doc.maitres_stage %}M./Mme <b>{{ m.employee_name }}</b>{% if not loop.last %}, {% endif %}{% endfor %}
{% if doc.maitres_stage|length > 1 %}sont autorisés{% else %}est autorisé(e){% endif %}
à encadrer le stagiaire conformément aux dispositions internes.</p>

<h3>Article 4 — Fonctions</h3>
<p>Le stagiaire exercera, sous l'autorité de ses maîtres de stage, des tâches
relevant strictement du programme défini par la société.</p>

<h3>Article 5 — Indemnités</h3>
<p>En contrepartie des activités, le stagiaire percevra une indemnité forfaitaire mensuelle de
<b>{{ frappe.format_value(doc.indemnite_mensuelle, {'fieldtype':'Currency'}) }} francs CFA</b>.</p>

<h3>Article 6 — Obligations du stagiaire</h3>
<p>Le stagiaire s'engage à respecter le règlement intérieur, à observer la confidentialité
des informations de l'entreprise, et à se conformer aux directives de ses maîtres de stage.</p>

<h3>Article 7 — Résiliation</h3>
<p>Le présent contrat peut être résilié par chacune des parties moyennant un préavis de 8 jours,
sans indemnité de part ni d'autre.</p>

<h3>Article 8 — Dispositions finales</h3>
<p>Pour tout litige relatif à l'exécution ou à l'interprétation du présent contrat,
les parties conviennent d'avoir recours à un règlement amiable, à défaut duquel
les juridictions compétentes de Lomé seront saisies.</p>
</div>"""

TPL_STAGE_ACAD = TPL_STAGE_PRO.replace("stage professionnel", "stage académique").replace(
    "Article 1 — Nature du stage",
    "Article 1 — Nature du stage</h3>\n<p>Dans le cadre d'une convention avec l'établissement <b>{{ doc.etablissement_scolaire or '...' }}</b>, KYA-Energy Group accepte d'accueillir un stagiaire académique.<h3 style='display:none'>",
)

TPL_CDI = """<div>
<p><b>Entre</b></p>
<p><b>KYA-Energy Group</b>, représenté par son Directeur Général <b>{{ doc.nom_dg }}</b>, d'une part ;</p>
<p><b>Et</b></p>
<p>M./Mme <b>{{ doc.employee_name }}</b>, né(e) le {{ frappe.format_date(doc.date_naissance) }},
demeurant à {{ doc.domicile or '...' }}, ci-après désigné(e) « <b>SALARIÉ</b> », d'autre part.</p>
<p><i>Il a été convenu ce qui suit :</i></p>

<h3>Article 1 — Engagement</h3>
<p>Le salarié est engagé à compter du <b>{{ frappe.format_date(doc.date_debut) }}</b>
en qualité de <b>{{ doc.poste }}</b>, sous contrat à durée indéterminée (CDI).</p>

<h3>Article 2 — Période d'essai</h3>
<p>Le présent contrat est soumis à une période d'essai conformément à la convention collective applicable.</p>

<h3>Article 3 — Rémunération</h3>
<p>Le salarié percevra un salaire mensuel brut de
<b>{{ frappe.format_value(doc.salaire_mensuel, {'fieldtype':'Currency'}) }} francs CFA</b>.</p>

<h3>Article 4 — Lieu de travail</h3>
<p>Le salarié exercera ses fonctions au siège de KYA-Energy Group ou en tout autre lieu désigné par la Direction.</p>

<h3>Article 5 — Obligations</h3>
<p>Le salarié s'engage à exercer ses fonctions avec diligence, à respecter les consignes de la hiérarchie
et à observer la stricte confidentialité des informations de l'entreprise.</p>

<h3>Article 6 — Résiliation</h3>
<p>Le présent contrat peut être rompu par chacune des parties dans les conditions et délais prévus
par le code du travail togolais.</p>

<h3>Article 7 — Dispositions finales</h3>
<p>Pour tout litige, les parties s'efforceront de trouver une solution amiable, à défaut de laquelle
les juridictions compétentes de Lomé seront saisies.</p>
</div>"""

TPL_CDD = TPL_CDI.replace(
    "à durée indéterminée (CDI)",
    "à durée déterminée (CDD) jusqu'au <b>{{ frappe.format_date(doc.date_fin) }}</b>",
).replace(
    "Article 1 — Engagement</h3>\n<p>Le salarié est engagé à compter du <b>{{ frappe.format_date(doc.date_debut) }}</b>",
    "Article 1 — Engagement</h3>\n<p>Le salarié est engagé du <b>{{ frappe.format_date(doc.date_debut) }}</b> au <b>{{ frappe.format_date(doc.date_fin) }}</b>",
)

TPL_PRESTATAIRE = """<div>
<p><b>Entre</b></p>
<p><b>KYA-Energy Group</b>, représenté par son Directeur Général <b>{{ doc.nom_dg }}</b>, ci-après « <b>LE CLIENT</b> », d'une part ;</p>
<p><b>Et</b></p>
<p>M./Mme <b>{{ doc.employee_name }}</b>, demeurant à {{ doc.domicile or '...' }},
ci-après désigné(e) « <b>LE PRESTATAIRE</b> », d'autre part.</p>
<p><i>Il a été convenu ce qui suit :</i></p>

<h3>Article 1 — Objet</h3>
<p>Le Client confie au Prestataire la mission suivante : <b>{{ doc.poste or 'Prestation de services' }}</b>.</p>

<h3>Article 2 — Durée</h3>
<p>La présente prestation prend effet le <b>{{ frappe.format_date(doc.date_debut) }}</b>
et s'achève le <b>{{ frappe.format_date(doc.date_fin) }}</b>.</p>

<h3>Article 3 — Rémunération</h3>
<p>En contrepartie de l'exécution de la mission, le Prestataire percevra la somme forfaitaire de
<b>{{ frappe.format_value(doc.montant_mission, {'fieldtype':'Currency'}) }} francs CFA</b>,
toutes taxes comprises.</p>

<h3>Article 4 — Obligations du Prestataire</h3>
<p>Le Prestataire s'engage à exécuter la mission en personne, dans les règles de l'art,
à respecter les délais convenus et à garantir la confidentialité des informations communiquées.</p>

<h3>Article 5 — Indépendance</h3>
<p>Le Prestataire conserve son entière indépendance et ne saurait être assimilé à un salarié du Client.
Il prend en charge ses propres cotisations sociales et fiscales.</p>

<h3>Article 6 — Résiliation</h3>
<p>Le présent contrat peut être résilié de plein droit en cas de manquement grave de l'une des parties,
après mise en demeure restée sans effet pendant 8 jours.</p>

<h3>Article 7 — Dispositions finales</h3>
<p>Tout litige relatif au présent contrat sera soumis aux juridictions compétentes de Lomé.</p>
</div>"""


def _seed_templates():
    seeds = [
        ("Contrat Stage Professionnel", "Stage Professionnel", TPL_STAGE_PRO),
        ("Contrat Stage Académique", "Stage Académique", TPL_STAGE_ACAD),
        ("Contrat CDI", "CDI", TPL_CDI),
        ("Contrat CDD", "CDD", TPL_CDD),
        ("Contrat Prestataire", "Prestataire", TPL_PRESTATAIRE),
    ]
    for title, ctype, html in seeds:
        if frappe.db.exists("KYA Contract Template", title):
            continue
        frappe.get_doc({
            "doctype": "KYA Contract Template",
            "title": title,
            "contract_type": ctype,
            "version": "RH-ENG-V01",
            "is_active": 1,
            "html_body": html,
        }).insert(ignore_permissions=True)

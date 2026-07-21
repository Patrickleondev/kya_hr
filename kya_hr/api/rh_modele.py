# Copyright (c) 2026, KYA-Energy Group
"""Modèle d'import RH téléchargeable depuis /rh-effectifs.

La RH ne doit pas chercher un fichier : elle télécharge le modèle depuis la
page, le remplit, le réimporte. Les en-têtes correspondent exactement à ce que
lit `rh_parcours_import` ; une ligne d'exemple (identité fictive) montre le
format, un onglet « Légende » explique tout.
"""
import base64
import datetime
import io

import frappe
from frappe import _

_ROLES = {"System Manager", "Responsable RH", "HR Manager", "Assistant(e) RH"}
_BLEU = "0F5C8A"


def build_bytes() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    entete_fill = PatternFill("solid", fgColor=_BLEU)
    entete_font = Font(bold=True, color="FFFFFF", size=11)
    titre_font = Font(bold=True, color=_BLEU, size=14)
    note_font = Font(italic=True, color="64748B", size=10)
    ex_font = Font(color="94A3B8", italic=True)
    thin = Side(style="thin", color="D9E2EC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def entete(ws, cols, ligne):
        for j, c in enumerate(cols, start=1):
            cell = ws.cell(row=ligne, column=j, value=c)
            cell.fill = entete_fill
            cell.font = entete_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border
        ws.row_dimensions[ligne].height = 30

    def largeurs(ws, ws_largeurs):
        for j, w in enumerate(ws_largeurs, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w

    def dv(ws, col, valeurs, first, last):
        d = DataValidation(type="list", formula1='"%s"' % ",".join(valeurs), allow_blank=True)
        d.prompt = "Valeurs possibles : " + ", ".join(valeurs)
        ws.add_data_validation(d)
        d.add("%s%d:%s%d" % (col, first, col, last))

    wb = Workbook()

    ws = wb.active
    ws.title = "Personnel"
    ws.cell(row=1, column=1, value="REGISTRE DU PERSONNEL — une ligne par salarié").font = titre_font
    ws.cell(row=2, column=1,
            value="Obligatoire : Mle, Nom, Prénoms, Date d'embauche. Le reste complète la fiche.").font = note_font
    cols_p = ["Mle", "Nom", "Prénoms", "Sexe", "N° Assurance Sociale", "Nationalité",
              "Statut matrimonial", "Nombre d'enfants", "Date de naissance",
              "Poste occupé", "Département de rattachement", "Qualification",
              "Date d'embauche", "Date de débauchage", "Type de contrat"]
    entete(ws, cols_p, 4)
    ex_p = ["0001", "EXEMPLE", "À remplacer", "M", "000000", "TG", "MARIE", 2,
            datetime.date(1990, 5, 14), "Intitulé du poste", "DST", "Diplôme",
            datetime.date(2020, 1, 6), None, "CDI"]
    for j, v in enumerate(ex_p, start=1):
        c = ws.cell(row=5, column=j, value=v)
        c.font = ex_font
        c.border = border
    largeurs(ws, [10, 16, 18, 7, 14, 10, 16, 9, 15, 22, 16, 14, 14, 15, 14])
    ws.freeze_panes = "A5"
    dv(ws, "D", ["M", "F"], 5, 300)
    dv(ws, "G", ["CELIBATAIRE", "MARIE", "MARIEE", "DIVORCE", "DIVORCEE", "VEUF", "VEUVE"], 5, 300)
    dv(ws, "O", ["CDI", "CDD", "Stagiaire", "Prestataire", "Intérim"], 5, 300)

    ws2 = wb.create_sheet("Evolution carriere")
    ws2.cell(row=1, column=1, value="PARCOURS DE CARRIÈRE — une ligne par évènement").font = titre_font
    ws2.cell(row=2, column=1,
             value="Un évènement = Matricule + Date de début + Nature. Date de fin vide = en cours.").font = note_font
    cols_c = ["Matricule", "Nom & Prénoms", "Date de début", "Date de fin",
              "Type de contrat", "Nombre de renouvellements", "Département",
              "Poste occupé", "Catégorie", "Classe & Échelon", "Salaire de base",
              "Nature de l'évolution", "Motif de l'évolution", "Observation"]
    entete(ws2, cols_c, 4)
    exemples = [
        ["0001", "EXEMPLE À remplacer", datetime.date(2020, 1, 6), None, "CDD", 0, "DSS",
         "Poste à l'embauche", "AM", "", "", "Embauche", "Recrutement initial", ""],
        ["0001", "EXEMPLE À remplacer", datetime.date(2022, 5, 12), None, "CDD", 0, "DST",
         "Nouveau poste après mutation", "C", "", "", "Mutation", "Réorganisation", ""],
        ["0001", "EXEMPLE À remplacer", datetime.date(2024, 1, 1), None, "CDI", 1, "DST",
         "Poste après titularisation", "C", "", "", "Renouvellement", "Passage en CDI", ""],
    ]
    r = 5
    for ex in exemples:
        for j, v in enumerate(ex, start=1):
            c = ws2.cell(row=r, column=j, value=v)
            c.font = ex_font
            c.border = border
        r += 1
    largeurs(ws2, [11, 20, 14, 13, 14, 12, 12, 26, 9, 14, 13, 20, 22, 20])
    ws2.freeze_panes = "A5"
    dv(ws2, "E", ["CDI", "CDD", "Stagiaire", "Prestataire", "Intérim"], 5, 500)
    dv(ws2, "L", ["Embauche", "Promotion", "Mutation", "Renouvellement",
                  "Augmentation salariale", "Rétrogradation", "Fin de contrat"], 5, 500)
    dv(ws2, "I", ["C", "AM", "AE"], 5, 500)

    ws3 = wb.create_sheet("Légende")
    ws3.cell(row=1, column=1, value="COMMENT REMPLIR CE MODÈLE").font = titre_font
    lignes = [
        ("", ""),
        ("Onglet « Personnel »", "Une ligne par salarié. Le registre du personnel."),
        ("Onglet « Evolution carriere »", "Une ligne par évènement (embauche, mutation, promotion…)."),
        ("", ""),
        ("Obligatoire (Personnel)", "Mle, Nom, Prénoms, Date d'embauche."),
        ("Obligatoire (Carrière)", "Matricule, Date de début, Nature de l'évolution."),
        ("", ""),
        ("Nature de l'évolution", "Embauche · Promotion · Mutation · Renouvellement · "
                                  "Augmentation salariale · Rétrogradation · Fin de contrat."),
        ("Type de contrat", "CDI · CDD · Stagiaire · Prestataire · Intérim."),
        ("Sexe", "M ou F."),
        ("Catégorie", "C (cadre) · AM (agent de maîtrise) · AE (agent d'exécution)."),
        ("Date de fin", "À laisser VIDE si l'évènement est en cours. La durée se calcule seule."),
        ("", ""),
        ("À l'import", "Sur /rh-effectifs → « Importer le classeur RH » → Simuler puis Importer."),
        ("Sans risque", "Rien n'est écrasé, aucun doublon : réimportez autant que nécessaire."),
        ("Ne renommez pas les onglets", "Ils doivent rester « Personnel » et « Evolution carriere »."),
        ("Lignes d'exemple", "La ligne grisée « EXEMPLE À remplacer » montre le format : "
                             "SUPPRIMEZ-la (ou écrivez par-dessus) avant d'importer."),
    ]
    for i, (a, b) in enumerate(lignes, start=3):
        ws3.cell(row=i, column=1, value=a).font = Font(bold=True, color=_BLEU)
        ws3.cell(row=i, column=2, value=b).alignment = Alignment(wrap_text=True, vertical="top")
    largeurs(ws3, [34, 80])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@frappe.whitelist()
def telecharger_modele():
    """Renvoie le modèle d'import en base64 pour téléchargement navigateur."""
    if not (_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Réservé aux Ressources Humaines."), frappe.PermissionError)
    data = build_bytes()
    return {"filename": "Modele_Import_RH_KYA.xlsx",
            "content_base64": base64.b64encode(data).decode()}

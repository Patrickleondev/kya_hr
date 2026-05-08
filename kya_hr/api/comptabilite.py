from io import BytesIO

import frappe
from frappe import _


_ALLOWED_ROLES = {"Comptable", "DFC", "DAAF", "Accounts Manager", "System Manager"}


@frappe.whitelist()
def download_template(type_document):
    roles = set(frappe.get_roles(frappe.session.user))
    if not roles.intersection(_ALLOWED_ROLES):
        frappe.throw(_("Accès réservé à la comptabilité."), frappe.PermissionError)

    try:
        from openpyxl import Workbook
    except ImportError:
        frappe.throw(_("La librairie openpyxl est requise pour générer les modèles Excel."))

    workbook = Workbook()
    sheet = workbook.active

    if type_document == "Etat de Salaire":
        sheet.title = "JANVIER"
        rows = [
            ["ETAT DE SALAIRE DU MOIS DE JANVIER 2025"],
            ["N°", "situation matrimoniale", "Nom", "Prénom", "NOM ET PRENOM", "N° matricule", "N° CNSS", "PROFESSION", "CATEGORIE", "ECHELON", "PERIODE DU DEBUT D'ANCIENNETE", "DATE D'EMBAUCHE", "CONTACT", "PERIODE", "SALAIRE DE BASE", "Prime de représentation", "Prime d'ancienneté", "Prime de responsabilité/Fonction", "Indemnité de transport", "Indemnité de logement", "Prime d'astreinte", "Prime de recherche", "TOTAL PRIME", "SAL. BRUT", "RETENUE CNSS PERSONNEL", "Solde après cotisation CNSS", "Abattement unique 28%", "Solde après Abattement", "Personnes à charge", "Solde après déductions", "Base RSTS", "Aperçu barème", "", "RSTS CALCULEE", "IRPP", "Total Retenues", "CNSS", "IRPP", "Prime EPI/Outillage", "Prime de caisse", "Déplacement", "Prime salissure", "Communication", "TOTAL NON IMPOSABLE", "Charge familiale", "NET", "", "", "Autres retenues", "Remboursement prêt", "MUTUELLE", "NET A PAYER", "Charges Patronale", "COTISATION SOCIALE", "NET REEL A PAYER", "50% SALAIRE"],
            [1, "M", "NOM", "PRENOM", "NOM PRENOM", "001", "", "COMPTABLE", "", "", "JANVIER 2025", "", "", "01/01/2025 AU 31/01/2025", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", "", 0, 0, 0, 0, 0, 0, 0, 0],
        ]
    elif type_document == "Grand Livre Général":
        sheet.title = "Grand-livre des comptes"
        rows = [
            ["KYA-ENERGY GROUP", "", "", "", "", "", "", "Grand-livre des comptes", "", "", "", "Période du", "", "2025-01-01"],
            ["", "", "", "", "", "", "", "", "", "", "", "au", "", "2025-12-31"],
            ["Impression provisoire", "", "", "", "", "", "", "Complet", "", "", "", "Tenue de compte : CFA"],
            [],
            ["Date", "C.j", "N° pièce", "", "Libellé écriture", "", "", "Let", "Mouvement débit", "", "", "Mouvement crédit", "", "Solde progressif"],
            ["401100", "", "Fournisseurs"],
            ["2025-01-02", "OD", "1", "", "FRAIS EXEMPLE", "", "", "", 0, "", "", 0, "", 0],
        ]
    elif type_document == "Facture":
        sheet.title = "Feuil1"
        rows = [
            ["", "FACTURE Lomé, le 19 Mars 2025"],
            ["", "N° 015/KEG/DG/03/2025"],
            [],
            ["", "Objet : Fourniture et installation KYA-SOP"],
            [],
            ["", "N°", "Désignation", "Unité", "Qté", "PU HT/HD", "Prix Total HT/HD"],
            ["", 1, "Module PV", "U", 1, 0, 0],
        ]
    else:
        frappe.throw(_("Type de document non pris en charge."))

    for row in rows:
        sheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    frappe.local.response.filename = "modele-{}.xlsx".format(type_document.lower().replace(" ", "-"))
    frappe.local.response.filecontent = stream.getvalue()
    frappe.local.response.type = "binary"

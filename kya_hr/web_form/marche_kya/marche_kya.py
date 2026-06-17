import frappe


def get_context(context):
    """Controller Web Form Fiche Marché KYA.

    La synthèse financière (coût total, écarts, marges) est recalculée côté
    serveur par le contrôleur du DocType `Marche KYA` à la validation ; le
    client_script de la web form la rejoue en direct pour le confort de saisie.
    """
    context.user_roles = frappe.get_roles(frappe.session.user)

import frappe


def get_context(context):
    """Controller Web Form Fiche Client SoP (Solar-on-Plan).

    Selon le mode de paiement (Cash / Tranche / Location), la fiche affiche
    l'échéancier par tranche ou l'état des paiements mensuels (location).
    """
    context.user_roles = frappe.get_roles(frappe.session.user)

"""Utilitaires KYA HR.

Expose `get_kya_email_footer` (référencé par hooks.py comme méthode Jinja)
et le module `approval_guards` (block_self_approval).
"""
from __future__ import annotations


def get_kya_email_footer() -> str:
    """Pied de page HTML standard pour les e-mails KYA-Energy Group.

    Utilisé dans les Email Templates via {{ get_kya_email_footer() }}.
    """
    return (
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid #e0e0e0;'
        'font-size:12px;color:#666;font-family:Arial,sans-serif;line-height:1.5;">'
        '<strong style="color:#00897B;">KYA-Energy Group</strong><br/>'
        "Cet e-mail est généré automatiquement par le système KYA. "
        "Merci de ne pas y répondre directement."
        "</div>"
    )

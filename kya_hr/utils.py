"""
KYA HR — Fonctions utilitaires
"""

KYA_EMAIL_FOOTER_TPL = """
<hr style="border:none; border-top:2px solid #009688; margin:20px 0 10px;">
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="font-family: Arial, sans-serif; font-size: 11px; color: #999;">
  <tr>
    <td width="65" style="vertical-align:middle; padding-right:10px;">
      <img src="{site_url}/assets/kya_hr/images/kya_logo.png"
           alt="KYA-Energy Group" width="55" height="55" border="0"
           style="display:block;">
    </td>
    <td style="vertical-align:middle; border-left:2px solid #009688; padding-left:10px;">
      <b style="color:#009688; font-size:12px;">KYA-Energy Group</b><br>
      08BP 81101 Agoe Nyive, Logop&eacute; &mdash; Lom&eacute;, Togo<br>
      &#x1F4DE; +228 70 45 34 81 &nbsp;|&nbsp;
      <a href="mailto:info@kya-energy.com" style="color:#009688;">info@kya-energy.com</a><br>
      <a href="https://www.kya-energy.com" style="color:#009688;">www.kya-energy.com</a>
    </td>
  </tr>
</table>
"""


def get_kya_email_footer():
    """Retourne le footer HTML KYA avec l'URL du site."""
    import frappe
    site_url = frappe.utils.get_url()
    return KYA_EMAIL_FOOTER_TPL.format(site_url=site_url)

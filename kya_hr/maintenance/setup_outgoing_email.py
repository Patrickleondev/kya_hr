# -*- coding: utf-8 -*-
"""Configuration + diagnostic de l'envoi d'emails (SMTP sortant).

Cause n°1 des « mails qui ne partent pas » (local ET prod) : il n'existe pas de
**compte Email sortant par défaut** (`Email Account` avec `default_outgoing=1`).
Sans lui, `frappe.sendmail` met les messages dans l'Email Queue en statut
**Error** (« Please setup default Email Account from Settings > Email Account »).

Fonctions :
  • setup(...)      : crée/met à jour LE compte sortant par défaut (idempotent)
  • diagnose()      : état des comptes / scheduler / file d'attente
  • flush()         : force l'envoi des emails en attente maintenant
  • send_test(to)   : envoie un email de test immédiatement (now=True)

PROD (exemple — adapter serveur/port/identifiants réels KYA) :
  bench --site <site> execute kya_hr.maintenance.setup_outgoing_email.setup \
    --kwargs "{'email_id':'info@kya-energy.com','password':'XXXX',
               'smtp_server':'smtp.gmail.com','smtp_port':587,'use_tls':1}"
  bench --site <site> execute kya_hr.maintenance.setup_outgoing_email.send_test \
    --kwargs "{'to':'tonadresse@gmail.com'}"
"""
import frappe


ACCOUNT_NAME = "KYA Sortant"


def setup(email_id, password=None, smtp_server="smtp.gmail.com", smtp_port=587,
          use_tls=1, use_ssl=0, login_id=None, display_name="KYA-Energy Group",
          set_default=1):
    """Crée/MAJ le compte Email sortant par défaut. Idempotent."""
    use_tls = int(use_tls)
    use_ssl = int(use_ssl)
    smtp_port = int(smtp_port)

    name = frappe.db.exists("Email Account", {"email_id": email_id}) or \
        frappe.db.exists("Email Account", ACCOUNT_NAME)
    if name:
        acc = frappe.get_doc("Email Account", name)
    else:
        acc = frappe.new_doc("Email Account")
        acc.account_name = ACCOUNT_NAME

    acc.email_id = email_id
    acc.login_id_is_different = 1 if login_id else 0
    if login_id:
        acc.login_id = login_id
    if password is not None:
        acc.password = password
    acc.smtp_server = smtp_server
    acc.smtp_port = smtp_port
    acc.use_tls = use_tls
    acc.use_ssl_for_outgoing = use_ssl
    acc.enable_outgoing = 1
    acc.default_outgoing = int(set_default)
    acc.enable_incoming = 0
    acc.default_incoming = 0
    if display_name:
        acc.add_signature = 0
    acc.flags.ignore_mandatory = True
    acc.flags.ignore_validate = True   # n'essaie pas de se connecter au SMTP à l'enregistrement
    acc.save(ignore_permissions=True)

    # S'assurer qu'il est le SEUL default_outgoing
    if int(set_default):
        for other in frappe.get_all("Email Account",
                                    filters={"default_outgoing": 1, "name": ["!=", acc.name]},
                                    pluck="name"):
            frappe.db.set_value("Email Account", other, "default_outgoing", 0)
    frappe.db.commit()
    print(f"OK — compte sortant '{acc.name}' configuré ({email_id} via {smtp_server}:{smtp_port}, "
          f"tls={use_tls} ssl={use_ssl}, défaut={set_default}).")
    return acc.name


def setup_office365(email_id, password, login_id=None):
    """Raccourci Outlook / Microsoft 365 (l'entreprise utilise Outlook).

    Serveur : smtp.office365.com, port 587, STARTTLS. `login_id` = adresse de
    connexion si différente de l'expéditeur (boîte partagée « Send As »).
    Si le compte a la MFA, créer un « mot de passe d'application » côté Microsoft.
    """
    return setup(email_id=email_id, password=password, login_id=login_id,
                 smtp_server="smtp.office365.com", smtp_port=587,
                 use_tls=1, use_ssl=0)


def diagnose():
    print("=== Comptes Email ===")
    for ea in frappe.get_all("Email Account",
                             fields=["name", "email_id", "default_outgoing",
                                     "enable_outgoing", "smtp_server", "smtp_port",
                                     "use_tls", "use_ssl_for_outgoing"]):
        print(" ", ea)
    has_default = frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1})
    print("\nCompte sortant par défaut OK :", bool(has_default))

    from frappe.utils.scheduler import is_scheduler_inactive
    print("Scheduler inactif :", is_scheduler_inactive())

    print("\n=== Email Queue (5 derniers) ===")
    for q in frappe.get_all("Email Queue", fields=["name", "status", "error"],
                            order_by="creation desc", limit=5):
        print(f"  {q.name} [{q.status}] {(q.error or '')[:140]}")


def flush():
    """Force le traitement de la file d'attente maintenant."""
    from frappe.email.queue import flush as _flush
    _flush()
    frappe.db.commit()
    print("Flush demandé. État :")
    diagnose()


def send_test(to):
    """Envoie un email de test IMMÉDIATEMENT (now=True) pour valider le SMTP."""
    frappe.sendmail(
        recipients=[to],
        subject="✅ Test envoi KYA — " + frappe.utils.now(),
        message="<p>Si vous lisez ceci, l'envoi SMTP fonctionne.</p>",
        now=True,
    )
    print(f"Email de test envoyé à {to} (now=True). Aucune exception = SMTP OK.")

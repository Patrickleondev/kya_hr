"""KYA Contrat — Controller principal.

Lifecycle:
- validate: cohérence dates + sélection auto template + calcul date_fin
- before_submit: vérifier signatures employé + DG
- on_update: générer PDF + envoyer emails finaux quand workflow_state=Finalisé
"""
import frappe
import re
import base64
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate, now_datetime


class KYAContrat(Document):
    # ----- LIFECYCLE -----
    def validate(self):
        self._autofill_from_employee()
        self._default_civilite()
        self._default_civilite_maitres()
        self._select_template()
        self._compute_date_fin()
        self._validate_signatures()

    def _default_civilite_maitres(self):
        """Propose la civilité de chaque maître de stage (sexe + situation de
        famille de sa fiche Employee) si la RH ne l'a pas choisie. Éditable :
        jamais réécrite si déjà renseignée, comme pour le stagiaire."""
        maitres = self.get("maitres_stage") or []
        if not maitres:
            return
        from kya_hr.kya_hr.doctype.kya_contract_template.kya_contract_template import (
            compute_civilite,
        )
        # Employee.marital_status est en anglais ; compute_civilite attend les
        # libellés FR. On traduit pour que « Married » donne bien « Madame ».
        vers_fr = {"married": "Marié(e)", "divorced": "Divorcé(e)",
                   "widowed": "Veuf/Veuve"}
        for m in maitres:
            if m.get("civilite") or not m.get("employee"):
                continue
            infos = frappe.db.get_value(
                "Employee", m.employee, ["gender", "marital_status"], as_dict=True) or {}
            if infos.get("gender"):
                situation = vers_fr.get((infos.get("marital_status") or "").strip().lower())
                m.civilite = compute_civilite(infos.get("gender"), situation)

    def _default_civilite(self):
        """Propose la civilité (Sexe + Situation de famille) si la RH ne l'a pas
        renseignée. S'applique même sans Employee lié (le contrat précède la
        fiche). Jamais réécrite si déjà saisie/corrigée."""
        if self.get("civilite") or not self.sexe:
            return
        from kya_hr.kya_hr.doctype.kya_contract_template.kya_contract_template import (
            compute_civilite,
        )
        self.civilite = compute_civilite(self.sexe, self.situation_famille)

    # ----- AUTO-FILL DEPUIS EMPLOYEE -----
    def _autofill_from_employee(self):
        """Pré-remplit les champs du contrat depuis la fiche Employee.

        Seuls les champs VIDES sont remplis (n'écrase pas une saisie manuelle
        de la RH). Le mapping Employee -> KYA Contrat couvre les infos
        nécessaires au PDF de référence (CONTRAT2.pdf) :
          - telephone, employee_email, date_naissance, sexe, domicile

        Filiation père/mère ne sont pas sur Employee standard ; saisis par
        le signataire dans le portail /kya-contrat lors de la signature.
        """
        if not self.employee:
            return
        # Seuls les champs qui EXISTENT sur Employee HRMS sont demandés (sinon SQL error).
        # personal_phone, place_of_birth, number_of_children sont absents en HRMS v16.
        emp = frappe.db.get_value(
            "Employee",
            self.employee,
            [
                "employee_name", "personal_email", "company_email", "user_id",
                "cell_number",
                "date_of_birth", "gender",
                "current_address", "permanent_address",
                "marital_status",
                "person_to_be_contacted",
                "department", "designation",
            ],
            as_dict=True,
        )
        if not emp:
            return

        if not self.employee_name:
            self.employee_name = emp.get("employee_name") or ""
        if not self.employee_email:
            self.employee_email = (
                emp.get("personal_email") or emp.get("company_email") or emp.get("user_id") or ""
            )
        if not self.telephone:
            self.telephone = emp.get("cell_number") or ""
        if not self.date_naissance and emp.get("date_of_birth"):
            self.date_naissance = emp.get("date_of_birth")
        if not self.sexe and emp.get("gender"):
            gender_map = {"Male": "Masculin", "Female": "Féminin", "Other": "Autre"}
            self.sexe = gender_map.get(emp.get("gender"), emp.get("gender"))
        if not self.domicile:
            self.domicile = emp.get("current_address") or emp.get("permanent_address") or ""

        # Nouveaux champs CDI/CDD — lieu_naissance et nb_enfants restent saisis
        # manuellement par la RH (pas sur Employee HRMS standard)
        if not self.situation_famille and emp.get("marital_status"):
            ms_map = {"Single": "Célibataire", "Married": "Marié(e)",
                      "Divorced": "Divorcé(e)", "Widowed": "Veuf/Veuve"}
            self.situation_famille = ms_map.get(emp.get("marital_status"), emp.get("marital_status"))
        if not self.personne_a_prevenir and emp.get("person_to_be_contacted"):
            self.personne_a_prevenir = emp.get("person_to_be_contacted")
        if not self.poste and emp.get("designation"):
            self.poste = emp.get("designation")
        if not self.departement and emp.get("department"):
            self.departement = emp.get("department")

    def before_submit(self):
        # On submit only when workflow has reached Validé (after DG signature) or via direct submit by HR
        if self.workflow_state not in ("Validé", "RH (revue)", "Archivé"):
            # allow direct submit only for HR Manager / System Manager fast-path
            if not any(r in frappe.get_roles() for r in ("HR Manager", "System Manager")):
                frappe.throw(_("Le contrat doit être signé par les deux parties avant soumission."))

    def on_update_after_submit(self):
        self._maybe_generate_pdf()

    def on_update(self):
        # Détecte transition vers Validé (DG vient de signer) puis génère PDF + emails finaux.
        # Détecte aussi 'En attente DG' pour notifier le DG via lien magique.
        self._maybe_generate_pdf()
        self._maybe_notify_signataire()
        self._maybe_notify_dg()

    def _maybe_notify_signataire(self):
        """Quand le contrat ENTRE dans 'En attente Signature Salarié' (par
        l'action workflow 'Envoyer au Salarié' OU le bouton RH), envoie au
        signataire l'email avec le lien magique.

        C'était la cause du 'mail jamais reçu par le signataire' : seul le
        bouton RH envoyait le mail ; l'action workflow changeait l'état sans
        rien envoyer. On envoie maintenant UNE fois, à l'entrée dans l'état.
        """
        if self.workflow_state != "En attente Signature Salarié":
            return
        # Anti double-envoi : le bouton RH a déjà envoyé.
        if self.flags.get("signataire_email_sent"):
            return
        # N'envoyer qu'à la TRANSITION (pas à chaque save tant qu'on reste dans l'état).
        before = self.get_doc_before_save()
        if before and before.workflow_state == "En attente Signature Salarié":
            return
        try:
            from kya_hr.api.kya_contracts import send_signataire_email
            send_signataire_email(self)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "KYA Contrat — Notification signataire")

    # ----- HELPERS -----
    def _select_template(self):
        if self.template:
            return
        if not self.contract_type:
            return

        # 1. Tentative : type + genre exact
        if self.sexe in ("Masculin", "Féminin"):
            tpl = frappe.db.get_value(
                "KYA Contract Template",
                {
                    "contract_type": self.contract_type,
                    "genre_cible": self.sexe,
                    "is_active": 1,
                },
                "name",
            )
            if tpl:
                self.template = tpl
                return

        # 2. Fallback : type + genre_cible="Tous" (Stage Académique/Professionnel, etc.)
        tpl = frappe.db.get_value(
            "KYA Contract Template",
            {
                "contract_type": self.contract_type,
                "genre_cible": "Tous",
                "is_active": 1,
            },
            "name",
        )
        if tpl:
            self.template = tpl
            return

        # 3. Fallback ultime : n'importe quel template actif pour ce type,
        # SAUF un modèle rédigé pour le genre opposé. Mieux vaut laisser la RH
        # choisir que de sortir « Monsieur » sur le contrat d'une femme : c'est
        # ce repli silencieux qui a produit les contrats au mauvais genre.
        filtres = {"contract_type": self.contract_type, "is_active": 1}
        if self.sexe in ("Masculin", "Féminin"):
            genre_oppose = "Féminin" if self.sexe == "Masculin" else "Masculin"
            filtres["genre_cible"] = ["!=", genre_oppose]
        tpl = frappe.db.get_value("KYA Contract Template", filtres, "name")
        if tpl:
            self.template = tpl

    def get_corps_html(self):
        """Corps du contrat rendu : articles du constructeur RH (variables +
        accord M/F), sinon html_body (mode avancé). Appelé par le print format.
        """
        if not self.template:
            self._select_template()
        if not self.template:
            return ""
        try:
            tpl = frappe.get_doc("KYA Contract Template", self.template)
            return tpl.render_for(self)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "KYA Contrat get_corps_html")
            return ""

    def _compute_date_fin(self):
        if self.contract_type == "CDI":
            return
        if self.date_debut and self.duree_mois and not self.date_fin:
            self.date_fin = add_months(getdate(self.date_debut), int(self.duree_mois))

    def _validate_signatures(self):
        # Si workflow passe en Signé Salarié, exige signature + check lu/approuvé
        if self.workflow_state == "Signé Salarié" and not self.signature_employe:
            frappe.throw(_("La signature du signataire est requise pour passer à 'Signé Salarié'."))
        if self.workflow_state == "Signé Salarié" and not self.contrat_lu:
            frappe.throw(_("Vous devez cocher 'J'ai lu et approuvé' avant de signer."))
        if self.workflow_state in ("Validé", "RH (revue)", "Archivé") and not self.signature_dg:
            frappe.throw(_("La signature du Directeur Général est requise."))

        # Auto-fill nom signé + dates
        if self.signature_employe and not self.nom_signe_employe:
            self.nom_signe_employe = self.employee_name
            self.date_signature_employe = now_datetime()
        if self.signature_dg and not self.date_signature_dg:
            self.date_signature_dg = now_datetime()

    def _maybe_generate_pdf(self):
        if self.workflow_state in ("Validé", "RH (revue)", "Archivé") and not self.pdf_final and self.signature_employe and self.signature_dg:
            try:
                self._generate_and_attach_pdf()
                self._send_final_emails()
            except Exception:
                frappe.log_error(frappe.get_traceback(), "KYA Contrat — Génération PDF")

    def _maybe_notify_dg(self):
        """Quand la RH clique 'Soumettre au DG' (workflow_state -> En attente DG),
        envoyer le lien magique au DG via le helper API."""
        if self.workflow_state != "En attente DG":
            return
        try:
            from kya_hr.api.kya_contracts import notify_dg_after_rh_gateway
            notify_dg_after_rh_gateway(self)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "KYA Contrat — Notification DG")

    def _generate_and_attach_pdf(self):
        from frappe.utils.pdf import get_pdf

        html = frappe.get_print(
            "KYA Contrat",
            self.name,
            print_format="Contrat de Stage KYA" if (self.contract_type or "").lower().startswith("stage") else "KYA Contrat PDF",
            no_letterhead=1,
        )
        html = _sanitize_contract_pdf_html(html)
        pdf_bytes = get_pdf(html)
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"Contrat_{self.name}.pdf",
            "attached_to_doctype": "KYA Contrat",
            "attached_to_name": self.name,
            "content": pdf_bytes,
            "is_private": 1,
        }).insert(ignore_permissions=True)
        self.db_set("pdf_final", file_doc.file_url)

    def _send_final_emails(self):
        if not self.employee_email:
            return
        from kya_hr.utils import kya_email_html
        subject = f"📄 Contrat finalisé — {self.employee_name} — {self.name}"
        if self.date_fin:
            duree_row = ('<tr><td style="padding:6px 0;color:#555555;"><b>Date d\'échéance :</b></td>'
                         '<td style="padding:6px 0;">%s</td></tr>' % frappe.format_date(self.date_fin))
        else:
            duree_row = ('<tr><td style="padding:6px 0;color:#555555;"><b>Durée :</b></td>'
                         '<td style="padding:6px 0;">Indéterminée (CDI)</td></tr>')
        body = (
            "<p>Bonjour <b>%s</b>,</p>"
            "<p>Votre <b>%s</b> chez KYA-Energy Group est désormais signé par les deux "
            "parties et archivé dans notre système.</p>"
            "<p>Vous trouverez en <b>pièce jointe</b> votre exemplaire signé (PDF). "
            "Conservez ce document précieusement.</p>"
            '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" '
            'style="margin:16px 0;font-size:14px;font-family:Arial,Helvetica,sans-serif;">'
            '<tr><td style="padding:6px 0;color:#555555;"><b>Date d\'effet :</b></td>'
            '<td style="padding:6px 0;">%s</td></tr>'
            "%s"
            '<tr><td style="padding:6px 0;color:#555555;"><b>Référence :</b></td>'
            '<td style="padding:6px 0;">%s</td></tr>'
            "</table>"
            "<p>Pour toute question : <a href=\"mailto:rh@kya-energy.com\">rh@kya-energy.com</a></p>"
            "<p style=\"margin-top:18px;\">Bien cordialement,<br><b>Direction des Ressources "
            "Humaines</b><br>KYA-Energy Group</p>"
            % (self.employee_name or "", self.contract_type or "contrat",
               frappe.format_date(self.date_debut), duree_row, self.name)
        )
        message = kya_email_html("Contrat finalisé",
                                 body,
                                 subtitle="%s — Réf. %s" % (self.contract_type or "", self.name))
        attachments = []
        if self.pdf_final:
            fid = frappe.db.get_value("File", {"file_url": self.pdf_final}, "name")
            if fid:
                attachments.append({"fid": fid})

        recipients = [self.employee_email]
        # RH expéditrice (la personne qui a cliqué "Envoyer au signataire")
        if self.rh_sender_email and self.rh_sender_email not in recipients:
            recipients.append(self.rh_sender_email)
        # RH globale (settings)
        rh_email = None
        try:
            rh_email = frappe.db.get_single_value("KYA Dashboard Settings", "rh_email")
        except Exception:
            pass
        if rh_email and rh_email not in recipients:
            recipients.append(rh_email)
        # DG (archive)
        for u in frappe.get_all("Has Role", filters={"role": "Directeur Général", "parenttype": "User"}, fields=["parent"]):
            em = frappe.db.get_value("User", u.parent, "email")
            if em and em not in recipients:
                recipients.append(em)

        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            attachments=attachments,
            now=False,
        )


def _sanitize_contract_pdf_html(html):
    """Remove Desk print chrome/assets that wkhtmltopdf cannot fetch in Docker."""
    html = re.sub(r'<link[^>]+href=["\'](?:https?://[^"\']+)?/assets/[^"\']+["\'][^>]*>', '', html or '', flags=re.I)
    html = re.sub(r'<a[^>]+href=["\']/api/method/frappe\.utils\.print_format\.download_pdf[^"\']*["\'][^>]*>.*?</a>', '', html, flags=re.I | re.S)
    html = html.replace('/assets/frappe/images/signature-placeholder.png', 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==')
    logo_data_uri = _kya_logo_data_uri()
    if logo_data_uri:
        html = re.sub(
            r'(src=["\'])(?:https?://[^"\']+)?(?:/assets/kya_hr/images/(?:kya_logo|logo_kya)\.png|/files/(?:logo_kya|vrai)\.png)(["\'])',
            lambda match: f"{match.group(1)}{logo_data_uri}{match.group(2)}",
            html,
            flags=re.I,
        )
    return html


def _kya_logo_data_uri():
    for filename in ("kya_logo.png", "logo_kya.png"):
        try:
            path = frappe.get_app_path("kya_hr", "public", "images", filename)
            with open(path, "rb") as logo_file:
                encoded = base64.b64encode(logo_file.read()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
        except Exception:
            continue
    return ""

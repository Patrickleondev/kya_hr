"""KYA Contrat — Controller principal.

Lifecycle:
- validate: cohérence dates + sélection auto template + calcul date_fin
- before_submit: vérifier signatures employé + DG
- on_update: générer PDF + envoyer emails finaux quand workflow_state=Finalisé
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate, now_datetime


class KYAContrat(Document):
    # ----- LIFECYCLE -----
    def validate(self):
        self._select_template()
        self._compute_date_fin()
        self._validate_signatures()

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
        self._maybe_notify_dg()

    # ----- HELPERS -----
    def _select_template(self):
        if self.template:
            return
        tpl = frappe.db.get_value(
            "KYA Contract Template",
            {"contract_type": self.contract_type, "is_active": 1},
            "name",
        )
        if tpl:
            self.template = tpl

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
            no_letterhead=0,
        )
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
        subject = f"📄 Contrat finalisé — {self.employee_name} — {self.name}"
        message = frappe.render_template(
            """
            <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
              <div style="background:linear-gradient(135deg,#f7a800 0%,#e07b00 100%); padding:24px; color:#fff; text-align:center;">
                <h2 style="margin:0;">✅ Contrat Finalisé</h2>
                <p style="margin:6px 0 0 0; opacity:0.95;">{{ doc.contract_type }} — Réf. {{ doc.name }}</p>
              </div>
              <div style="padding:24px 28px;">
                <p>Bonjour <b>{{ doc.employee_name }}</b>,</p>
                <p>Votre <b>{{ doc.contract_type }}</b> chez KYA-Energy Group est désormais
                signé par les deux parties et archivé dans notre système.</p>
                <p>Vous trouverez en <b>pièce jointe</b> votre exemplaire signé (PDF).
                Conservez ce document précieusement.</p>
                <table style="width:100%; margin:18px 0; border-collapse:collapse; font-size:14px;">
                  <tr><td style="padding:6px 0; color:#555;"><b>Date d'effet :</b></td>
                      <td style="padding:6px 0;">{{ frappe.format_date(doc.date_debut) }}</td></tr>
                  {% if doc.date_fin %}
                  <tr><td style="padding:6px 0; color:#555;"><b>Date d'échéance :</b></td>
                      <td style="padding:6px 0;">{{ frappe.format_date(doc.date_fin) }}</td></tr>
                  {% else %}
                  <tr><td style="padding:6px 0; color:#555;"><b>Durée :</b></td>
                      <td style="padding:6px 0;">Indéterminée (CDI)</td></tr>
                  {% endif %}
                  <tr><td style="padding:6px 0; color:#555;"><b>Référence :</b></td>
                      <td style="padding:6px 0;"><code>{{ doc.name }}</code></td></tr>
                </table>
                <p style="font-size:13px; color:#666; border-top:1px solid #eee; padding-top:14px; margin-top:20px;">
                  Cet email a été envoyé automatiquement par la plateforme KYA-Energy Group.<br>
                  Pour toute question : <a href="mailto:rh@kya-energy.com">rh@kya-energy.com</a>
                </p>
                <p style="margin-top:20px;">Bien cordialement,<br><b>Direction des Ressources Humaines</b><br>KYA-Energy Group</p>
              </div>
            </div>
            """,
            {"doc": self, "frappe": frappe},
        )
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

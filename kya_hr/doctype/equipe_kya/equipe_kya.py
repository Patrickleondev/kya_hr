import frappe
from frappe.model.document import Document


class EquipeKYA(Document):
    def before_save(self):
        self.update_membres_count()

    def update_membres_count(self):
        count = frappe.db.count("Employee", {
            "custom_kya_equipe": self.name,
            "status": "Active",
        })
        self.nombre_membres = count

    def on_update(self):
        # Si le chef d'équipe change, s'assurer qu'il a le rôle Chef Service
        if self.chef_equipe and self.has_value_changed("chef_equipe"):
            user_id = frappe.db.get_value("Employee", self.chef_equipe, "user_id")
            if user_id and not frappe.db.exists("Has Role", {"parent": user_id, "role": "Chef Service"}):
                frappe.msgprint(
                    f"L'employé {self.chef_equipe_name} n'a pas le rôle 'Chef Service'. "
                    "Pensez à le lui attribuer pour qu'il puisse gérer son équipe.",
                    alert=True,
                )

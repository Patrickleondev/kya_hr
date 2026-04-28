// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Permission Sortie Employe'] = frappe.listview_settings['Permission Sortie Employe'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Permission Sortie Employe'].onload;
  frappe.listview_settings['Permission Sortie Employe'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouvelle Permission Sortie'), () => {
      window.open('/permission-sortie-employe/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();

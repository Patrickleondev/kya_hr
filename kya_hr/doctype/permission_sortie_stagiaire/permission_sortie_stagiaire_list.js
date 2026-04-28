// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Permission Sortie Stagiaire'] = frappe.listview_settings['Permission Sortie Stagiaire'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Permission Sortie Stagiaire'].onload;
  frappe.listview_settings['Permission Sortie Stagiaire'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouvelle Permission Sortie'), () => {
      window.open('/permission-sortie-stagiaire/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();

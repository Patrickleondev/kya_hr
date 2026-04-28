// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Planning Conge'] = frappe.listview_settings['Planning Conge'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Planning Conge'].onload;
  frappe.listview_settings['Planning Conge'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouveau Planning Conge'), () => {
      window.open('/planning-conge/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();

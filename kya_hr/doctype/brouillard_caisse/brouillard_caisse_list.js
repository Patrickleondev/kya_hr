// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Brouillard Caisse'] = frappe.listview_settings['Brouillard Caisse'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Brouillard Caisse'].onload;
  frappe.listview_settings['Brouillard Caisse'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouveau Brouillard'), () => {
      window.open('/brouillard-caisse/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();

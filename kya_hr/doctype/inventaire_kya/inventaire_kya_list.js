// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Inventaire KYA'] = frappe.listview_settings['Inventaire KYA'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Inventaire KYA'].onload;
  frappe.listview_settings['Inventaire KYA'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouvel Inventaire'), () => {
      window.open('/inventaire-kya/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();

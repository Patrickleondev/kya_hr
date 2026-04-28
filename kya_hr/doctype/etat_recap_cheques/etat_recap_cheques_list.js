// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Etat Recap Cheques'] = frappe.listview_settings['Etat Recap Cheques'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Etat Recap Cheques'].onload;
  frappe.listview_settings['Etat Recap Cheques'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouvel Etat Recap'), () => {
      window.open('/etat-recap/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();

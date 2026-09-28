// Copyright (c) 2026, rayan aouf and contributors
// For license information, please see license.txt

// Calculation lives in Client Script "Customer Satisfaction Survey"
// so it can be edited from the ERPNext desk UI.

frappe.ui.form.on("Customer Satisfaction Survey", {
	refresh(frm) {
		frm.trigger("source_type");
	},
	source_type(frm) {
		const labels = {
			Client: __("Customer"),
			Partner: __("Partner"),
			Employee: __("Employee"),
		};
		frm.set_df_property("customer_name", "label", labels[frm.doc.source_type] || __("Nom & Prénom"));
	},
});

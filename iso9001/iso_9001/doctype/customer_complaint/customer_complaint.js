frappe.ui.form.on("Customer Complaint", {
	refresh(frm) {
		frm.trigger("source_type");
	},
	source_type(frm) {
		const labels = {
			Client: __("Customer"),
			Partner: __("Partner"),
			Employee: __("Employee"),
		};
		frm.set_df_property("customer", "label", labels[frm.doc.source_type] || __("Customer"));
	},
});

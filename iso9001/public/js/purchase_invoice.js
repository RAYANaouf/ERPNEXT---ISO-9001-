frappe.ui.form.on("Purchase Invoice", {
	refresh(frm) {
		const comparison = "Supplier Offer Comparison";
		if (frm.doc.docstatus !== 1 || !frappe.model.can_create(comparison)) {
			return;
		}

		frm.add_custom_button(
			__("Create Offer Comparison"),
			async () => {
				const { message } = await frappe.call({
					method: "iso9001.iso_9001.doctype.supplier_offer_comparison.supplier_offer_comparison.create_offer_comparison",
					type: "POST",
					args: { purchase_invoice: frm.doc.name },
					freeze: true,
				});
				frappe.set_route("Form", comparison, message);
			},
			__("Actions")
		);
	},
});

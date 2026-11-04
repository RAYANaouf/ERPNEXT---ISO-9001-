frappe.ui.form.on("Employe Complaint", {
	onload(frm) {
		const hr_roles = ["System Manager", "HR Manager", "HR User"];
		const is_hr = hr_roles.some((role) => frappe.user.has_role(role));

		frm.set_df_property("employee", "read_only", !is_hr || !frm.is_new());
		// Keep the old category readable on historical records.
		if (frm.doc.category !== "Employee") {
			frm.set_df_property(
				"category",
				"options",
				frm.fields_dict.category.df.options
					.split("\n")
					.filter((category) => category !== "Employee")
					.join("\n")
			);
		}

		if (frm.is_new() && !frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}

		if (frm.is_new() && !frm.doc.employee) {
			return frappe
				.xcall(
					"iso9001.iso_9001.doctype.employe_complaint.employe_complaint.get_current_employee"
				)
				.then((employee) => {
					if (employee && frm.is_new() && !frm.doc.employee) {
						return frm.set_value("employee", employee);
					}
					if (!employee && !is_hr) {
						frappe.msgprint(__("Your user account is not linked to an active employee."));
					}
				});
		}
	},
});

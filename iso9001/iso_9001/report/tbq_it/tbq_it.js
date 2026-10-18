// Copyright (c) 2026, rayan aouf and contributors
// For license information, please see license.txt

frappe.query_reports["TBQ IT"] = {
	filters: [
		{
			fieldname: "year",
			label: __("Année"),
			fieldtype: "Int",
			reqd: 1,
			default: frappe.datetime.str_to_obj(
				frappe.datetime.add_months(frappe.datetime.get_today(), -1)
			).getFullYear(),
		},
		{
			fieldname: "month",
			label: __("Mois"),
			fieldtype: "Select",
			reqd: 1,
			options: "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12",
			default: String(
				frappe.datetime.str_to_obj(
					frappe.datetime.add_months(frappe.datetime.get_today(), -1)
				).getMonth() + 1
			),
		},
	],
};

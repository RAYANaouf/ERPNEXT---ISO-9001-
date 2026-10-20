# Copyright (c) 2026, rayan aouf and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.assign_to import add, set_status
from frappe.model.document import Document


def activity_report_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return ""

	monthly_condition = (
		"`tabActivity Report`.`doc_type` != 'Weekly Report' or "
		if _can_view_monthly_reports(user)
		else ""
	)
	return f"""(
		{monthly_condition}(
			`tabActivity Report`.`doc_type` = 'Weekly Report'
			and exists (
			select 1
			from `tabActivity Report Attendee` attendee
			inner join `tabEmployee` employee on employee.name = attendee.employee
			where attendee.parent = `tabActivity Report`.`name`
				and attendee.parenttype = 'Activity Report'
				and attendee.parentfield = 'attendance_list'
				and attendee.present = 1
				and employee.user_id = {frappe.db.escape(user)}
			)
		)
	)"""


def activity_report_has_permission(doc, ptype=None, user=None, **kwargs):
	if ptype == "create" or doc.is_new():
		return None

	user = user or frappe.session.user
	if frappe.db.get_value("Activity Report", doc.name, "doc_type") != "Weekly Report":
		return None if _can_view_monthly_reports(user) else False

	if ptype == "share":
		return False

	return _is_present_attendee(doc.name, user)


def _is_present_attendee(report_name, user):
	return bool(
		frappe.db.sql(
			"""
			select 1
			from `tabActivity Report Attendee` attendee
			inner join `tabEmployee` employee on employee.name = attendee.employee
			where attendee.parent = %s
				and attendee.parenttype = 'Activity Report'
				and attendee.parentfield = 'attendance_list'
				and attendee.present = 1
				and employee.user_id = %s
			limit 1
			""",
			(report_name, user),
		)
	)


def _can_view_monthly_reports(user):
	return bool({"System Manager", "Stock Manager"}.intersection(frappe.get_roles(user)))


class ActivityReport(Document):
	def check_permission(self, permtype="read", permlevel=None):
		if (
			permtype != "create"
			and not self.is_new()
			and frappe.session.user != "Administrator"
			and frappe.db.get_value("Activity Report", self.name, "doc_type") == "Weekly Report"
			and not _is_present_attendee(self.name, frappe.session.user)
		):
			frappe.throw(_("Only employees marked present can access this Activity Report."), frappe.PermissionError)

		return super().check_permission(permtype, permlevel)

	def on_update(self):
		previous = self.get_doc_before_save()
		previous_pairs = self._task_responsibles(previous.task_list) if previous else set()
		current_pairs = self._task_responsibles(self.task_list)

		for task, employee in previous_pairs - current_pairs:
			self._remove_report_assignment(task, employee)

		for task, employee in current_pairs:
			if frappe.db.get_value("Task", task, "status") in ("Completed", "Cancelled"):
				continue

			user = frappe.db.get_value("Employee", employee, "user_id")
			if not user:
				frappe.throw(
					_("Set a User ID for employee {0} before assigning this task.").format(
						frappe.bold(employee)
					)
				)
			if frappe.db.exists(
				"ToDo",
				{
					"reference_type": "Task",
					"reference_name": task,
					"allocated_to": user,
					"status": "Open",
				},
			):
				continue

			add(
				{
					"doctype": "Task",
					"name": task,
					"assign_to": [user],
					"description": self._assignment_description(employee),
				}
			)

	@staticmethod
	def _task_responsibles(rows):
		return {
			(row.task_link, row.responsible_employee)
			for row in rows
			if row.task_link and row.responsible_employee
		}

	def _remove_report_assignment(self, task, employee):
		assignment = frappe.db.get_value(
			"ToDo",
			{
				"reference_type": "Task",
				"reference_name": task,
				"status": "Open",
				"description": self._assignment_description(employee),
			},
			["name", "allocated_to"],
			as_dict=True,
		)
		if assignment:
			set_status(
				"Task",
				task,
				todo=assignment.name,
				assign_to=assignment.allocated_to,
				status="Cancelled",
			)

	def _assignment_description(self, employee):
		return f"Activity Report {self.name}, responsible employee {employee}"

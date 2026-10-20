# Copyright (c) 2026, rayan aouf and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form.assign_to import add, set_status
from frappe.model.document import Document


class ActivityReport(Document):
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

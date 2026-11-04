# Copyright (c) 2026, rayan aouf and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


HR_ROLES = {"System Manager", "HR Manager", "HR User"}


def _employee_for_user(user):
	return frappe.db.get_value(
		"Employee", {"user_id": user, "status": "Active"}, "name"
	)


def _is_hr(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(HR_ROLES.intersection(frappe.get_roles(user)))


@frappe.whitelist()
def get_current_employee():
	return _employee_for_user(frappe.session.user)


def employee_complaint_query_conditions(user=None):
	user = user or frappe.session.user
	if _is_hr(user):
		return ""

	employee = _employee_for_user(user)
	if not employee:
		return "1=0"

	return "`tabEmploye Complaint`.employee = {0}".format(frappe.db.escape(employee))


def employee_complaint_has_permission(doc, ptype=None, user=None, **kwargs):
	user = user or frappe.session.user
	if _is_hr(user):
		return True

	employee = _employee_for_user(user)
	if ptype == "create":
		return bool(employee)
	if ptype in ("read", "write", "submit", "select") and employee and doc:
		# Use the saved identity for existing records, including permission checks on
		# a document received from the client with a modified employee field.
		owner_employee = (
			frappe.db.get_value("Employe Complaint", doc.name, "employee")
			if not doc.is_new()
			else doc.get("employee")
		)
		return owner_employee == employee
	return False


class EmployeComplaint(Document):
	def before_insert(self):
		employee = _employee_for_user(frappe.session.user)
		if not employee and not _is_hr():
			frappe.throw(_("Your user account is not linked to an active employee."))

		if not _is_hr():
			self.employee = employee
			self.date = nowdate()
		else:
			self.employee = self.employee or employee
			self.date = self.date or nowdate()

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and self.employee != previous.employee:
			frappe.throw(_("The employee who submitted a complaint cannot be changed."))
		if previous and getdate(self.date) != getdate(previous.date):
			frappe.throw(_("The complaint date cannot be changed."))

		if (
			previous
			and previous.get("workflow_state") not in (None, "", "Draft")
			and not _is_hr()
		):
			for fieldname in ("category", "subject", "details", "attachment"):
				if self.get(fieldname) != previous.get(fieldname):
					frappe.throw(_("A submitted complaint can no longer be edited."))

	def before_update_after_submit(self):
		self.validate()

	def before_cancel(self):
		self.validate()

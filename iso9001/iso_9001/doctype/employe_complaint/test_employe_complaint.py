# Copyright (c) 2026, rayan aouf and Contributors
# See license.txt

import json
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.model.workflow import get_transitions, has_approval_access

from iso9001.iso_9001.doctype.employe_complaint import employe_complaint as complaint


class ComplaintForTest(complaint.EmployeComplaint):
	"""Exercise the controller without connecting to or modifying a site."""

	def __init__(self, previous=None, **values):
		self.__dict__.update(
			doctype="Employe Complaint",
			name="EMP-REC-TEST",
			employee="EMP-ONE",
			date="2026-10-21",
			workflow_state="Draft",
			category="Payroll",
			subject="Incorrect payroll",
			details="Please review the payroll calculation.",
			attachment=None,
			owner="employee@example.test",
		)
		self.__dict__.update(values)
		self._previous = previous

	def is_new(self):
		return self._previous is None

	def get_doc_before_save(self):
		return self._previous

	def check_permission(self, *args, **kwargs):
		return None


class TransitionForTest(frappe._dict):
	def as_dict(self):
		return dict(self)


class TestEmployeComplaint(unittest.TestCase):
	def setUp(self):
		self.user = "employee@example.test"
		self.roles = {self.user: ["Employee"], "hr@example.test": ["HR Manager"]}
		self.employees = {self.user: "EMP-ONE"}
		self.db = SimpleNamespace(
			get_value=Mock(return_value="EMP-ONE"), escape=Mock(return_value="'EMP-ONE'")
		)
		for patcher in (
			patch.object(frappe.local, "flags", frappe._dict(in_test=False), create=True),
			patch.object(frappe, "session", frappe._dict(user=self.user)),
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "get_roles", side_effect=lambda user=None: self.roles.get(user or frappe.session.user, [])),
			patch.object(frappe, "throw", side_effect=frappe.ValidationError),
			patch.object(complaint, "_", side_effect=lambda text: text),
			patch.object(complaint, "_employee_for_user", side_effect=lambda user: self.employees.get(user)),
			patch.object(complaint, "nowdate", return_value="2026-10-21"),
		):
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_employee_can_submit_their_saved_complaint(self):
		doc = ComplaintForTest(previous=ComplaintForTest())
		self.assertTrue(complaint.employee_complaint_has_permission(doc, "submit", self.user))

	def test_client_cannot_impersonate_another_complaint_owner(self):
		self.db.get_value.return_value = "EMP-TWO"
		doc = ComplaintForTest(previous=ComplaintForTest(), employee="EMP-ONE")
		self.assertFalse(complaint.employee_complaint_has_permission(doc, "read", self.user))

	def test_unlinked_account_cannot_create_or_list_complaints(self):
		self.assertFalse(complaint.employee_complaint_has_permission(ComplaintForTest(), "create", "unlinked@example.test"))
		self.assertEqual(complaint.employee_complaint_query_conditions("unlinked@example.test"), "1=0")

	def test_employee_list_is_limited_to_their_employee_record(self):
		self.assertEqual(complaint.employee_complaint_query_conditions(self.user), "`tabEmploye Complaint`.employee = 'EMP-ONE'")
		self.db.escape.assert_called_once_with("EMP-ONE")

	def test_hr_can_access_complaints_without_an_employee_link(self):
		self.assertTrue(complaint.employee_complaint_has_permission(ComplaintForTest(), "read", "hr@example.test"))
		self.assertEqual(complaint.employee_complaint_query_conditions("hr@example.test"), "")

	def test_new_complaint_uses_the_authenticated_employee_and_today(self):
		doc = ComplaintForTest(employee="EMP-TWO", date="2000-01-01")
		doc.before_insert()
		self.assertEqual((doc.employee, doc.date), ("EMP-ONE", "2026-10-21"))

	def test_dates_from_database_and_client_are_equivalent(self):
		doc = ComplaintForTest(previous=ComplaintForTest(date=date(2026, 10, 21)))
		doc.validate()

	def test_original_employee_and_date_cannot_be_changed(self):
		for values in ({"employee": "EMP-TWO"}, {"date": "2026-10-20"}):
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				ComplaintForTest(previous=ComplaintForTest(), **values).validate()

	def test_submitted_content_is_protected_on_update_after_submit(self):
		doc = ComplaintForTest(previous=ComplaintForTest(workflow_state="Submitted"), subject="Changed")
		with self.assertRaises(frappe.ValidationError):
			doc.before_update_after_submit()

	def test_employee_can_correct_a_draft(self):
		ComplaintForTest(previous=ComplaintForTest(), subject="Corrected subject").validate()

	def test_workflow_allows_self_submission_and_each_hr_role(self):
		root = Path(complaint.__file__).parents[3]
		workflow_data = next(doc for doc in json.loads((root / "fixtures/workflow.json").read_text()) if doc.get("document_type") == "Employe Complaint")
		workflow = frappe._dict(
			workflow_state_field="workflow_state",
			transitions=[TransitionForTest(t) for t in workflow_data["transitions"]],
		)
		doc = ComplaintForTest(previous=ComplaintForTest())
		transitions = get_transitions(doc, workflow=workflow)
		self.assertEqual([t["action"] for t in transitions], ["Submit Complaint"])
		self.assertTrue(has_approval_access(self.user, doc, transitions[0]))
		for role in ("HR User", "HR Manager", "System Manager"):
			with self.subTest(role=role):
				self.roles[self.user] = [role]
				doc.workflow_state = "Submitted"
				self.assertIn("Take in Charge", [t["action"] for t in get_transitions(doc, workflow=workflow)])
				self.assertTrue(any(s["state"] == "Submitted" and s["allow_edit"] == role for s in workflow_data["states"]))

	def test_employee_can_read_response_but_not_internal_notes(self):
		meta = json.loads(Path(complaint.__file__).with_suffix(".json").read_text())
		fields = {field["fieldname"]: field for field in meta["fields"]}
		perms = [perm for perm in meta["permissions"] if perm["role"] == "Employee"]
		read_levels = {perm.get("permlevel", 0) for perm in perms if perm.get("read")}
		write_levels = {perm.get("permlevel", 0) for perm in perms if perm.get("write")}
		self.assertIn(fields["mg_action"]["permlevel"], read_levels)
		self.assertNotIn(fields["mg_action"]["permlevel"], write_levels)
		self.assertNotIn(fields["internal_notes"]["permlevel"], read_levels)

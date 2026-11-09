import frappe
from frappe.model.document import Document


class TBQITSettings(Document):
	def validate(self):
		days = set()
		for row in self.weekly_schedule:
			if row.day_of_week in days:
				frappe.throw(f"Le jour {row.day_of_week} apparaît plusieurs fois dans l'horaire.")
			days.add(row.day_of_week)

			if not row.is_working_day:
				continue

			if not row.start_time or not row.end_time:
				frappe.throw(f"Indique les heures de début et de fin pour {row.day_of_week}.")
			if str(row.start_time) == str(row.end_time):
				frappe.throw(f"Les heures de début et de fin doivent être différentes pour {row.day_of_week}.")

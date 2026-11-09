# Copyright (c) 2026, rayan aouf and contributors
# For license information, please see license.txt

"""Indicateurs TBQ du processus SUPPORT IT (ISO 9001 §9.1).

Période par défaut : mois civil précédent (revue mensuelle).
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, time as datetime_time, timedelta

import frappe
from frappe.utils import (
	add_days,
	add_months,
	cint,
	flt,
	get_datetime,
	get_first_day,
	get_last_day,
	get_quarter_ending,
	get_quarter_start,
	getdate,
	get_time,
	now_datetime,
)

IT_PROJECT_NAME = "SUPPORT IT"
ISSUE_PANNE = "Panne ERP"
ISSUE_SUPPORT = "Support"
CLOSED_SUPPORT = ("Resolved", "Closed")
CLOSED_TASK = ("Completed",)
CANCELLED_TASK = ("Cancelled", "Template")
WEEK_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

BACKUP_NAME_RE = re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})")


def get_period(filters=None):
	filters = _as_dict(filters)
	if filters.get("from_date") and filters.get("to_date"):
		return getdate(filters["from_date"]), getdate(filters["to_date"])
	if filters.get("year") and filters.get("month"):
		start = date(cint(filters["year"]), cint(filters["month"]), 1)
		end = get_last_day(start)
		return getdate(start), getdate(end)
	prev = add_months(getdate(), -1)
	return get_first_day(prev), get_last_day(prev)


def compute_kpis(filters=None):
	start, end = get_period(filters)
	disponibilite = _kpi_disponibilite(start, end)
	sauvegardes = _kpi_sauvegardes(start, end)
	demandes = _kpi_demandes(start, end)
	evolutions = _kpi_evolutions(start, end)
	formations = _kpi_formations(start, end)
	return {
		"period_start": start,
		"period_end": end,
		"disponibilite": disponibilite,
		"sauvegardes": sauvegardes,
		"demandes": demandes,
		"evolutions": evolutions,
		"formations": formations,
	}


@frappe.whitelist()
def card_disponibilite(filters=None):
	kpi = compute_kpis(filters)["disponibilite"]
	return _card(kpi["value"], "Percent", ["List", "Issue"], {"issue_type": ISSUE_PANNE})


@frappe.whitelist()
def card_sauvegardes(filters=None):
	kpi = compute_kpis(filters)["sauvegardes"]
	return _card(kpi["value"], "Percent", ["query-report", "TBQ IT"])


@frappe.whitelist()
def card_demandes(filters=None):
	kpi = compute_kpis(filters)["demandes"]
	return _card(kpi["value"], "Percent", ["List", "Issue"], {"issue_type": ISSUE_SUPPORT})


@frappe.whitelist()
def card_evolutions(filters=None):
	kpi = compute_kpis(filters)["evolutions"]
	projects = _project_names()
	options = {"project": projects[0]} if projects else None
	return _card(kpi["value"], "Percent", ["List", "Task"], options)


@frappe.whitelist()
def card_formations(filters=None):
	kpi = compute_kpis(filters)["formations"]
	return _card(kpi["value"], "Float", ["List", "Training Plan"])


def after_migrate():
	for title, method in (
		("horaires TBQ IT", ensure_it_schedule),
		("champs de panne ERP", ensure_issue_outage_fields),
		("tableau de bord TBQ IT", install_dashboard),
	):
		try:
			method()
		except Exception:
			frappe.log_error(title=f"SUPPORT IT — {title}")


def ensure_it_schedule():
	if not frappe.db.exists("DocType", "TBQ IT Settings"):
		return

	settings = frappe.get_single("TBQ IT Settings")
	if settings.setup_complete and settings.weekly_schedule:
		return

	if not settings.weekly_schedule:
		for day in WEEK_DAYS:
			settings.append(
				"weekly_schedule",
				{
					"day_of_week": day,
					"is_working_day": 1,
					"start_time": "06:00:00",
					"end_time": "20:00:00",
				},
			)
	settings.setup_complete = 1
	settings.save(ignore_permissions=True)


def ensure_issue_outage_fields():
	if not frappe.db.exists("DocType", "Issue"):
		return

	role_read_only = 'eval:frappe.session.user != "Administrator" && !frappe.user.has_role("Support Team") && !frappe.user.has_role("System Manager")'
	fields = [
		{
			"fieldname": "custom_it_panne_section",
			"fieldtype": "Section Break",
			"label": "Horaires réels de la panne (IT)",
			"insert_after": "resolution_time",
			"depends_on": 'eval:doc.issue_type == "Panne ERP"',
		},
		{
			"fieldname": "custom_it_panne_debut_reel",
			"fieldtype": "Datetime",
			"label": "Début réel de la panne",
			"insert_after": "custom_it_panne_section",
			"depends_on": 'eval:doc.issue_type == "Panne ERP"',
			"read_only_depends_on": role_read_only,
		},
		{
			"fieldname": "custom_it_panne_retablissement_reel",
			"fieldtype": "Datetime",
			"label": "Rétablissement réel",
			"insert_after": "custom_it_panne_debut_reel",
			"depends_on": 'eval:doc.issue_type == "Panne ERP"',
			"read_only_depends_on": role_read_only,
		},
	]

	for definition in fields:
		filters = {"dt": "Issue", "fieldname": definition["fieldname"]}
		name = frappe.db.get_value("Custom Field", filters, "name")
		if name:
			custom_field = frappe.get_doc("Custom Field", name)
			custom_field.update(definition)
			custom_field.module = "ISO 9001"
			custom_field.save(ignore_permissions=True)
		else:
			frappe.get_doc(
				{
					"doctype": "Custom Field",
					"dt": "Issue",
					"module": "ISO 9001",
					**definition,
				}
			).insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Issue")


def validate_issue_outage_times(doc, method=None):
	if doc.doctype != "Issue":
		return

	fields = ("custom_it_panne_debut_reel", "custom_it_panne_retablissement_reel")
	before = doc.get_doc_before_save() if not doc.is_new() else None
	changed = any(
		(doc.get(fieldname) or None) != ((before.get(fieldname) or None) if before else None)
		for fieldname in fields
	)
	roles = set(frappe.get_roles())
	can_manage_times = frappe.session.user == "Administrator" or bool(
		roles.intersection({"Support Team", "System Manager"})
	)
	if changed and not can_manage_times:
		frappe.throw(
			"Seule l'équipe IT (rôle Support Team) ou un administrateur système peut modifier les horaires réels d'une panne ERP.",
			frappe.PermissionError,
		)

	start = doc.get(fields[0])
	end = doc.get(fields[1])
	if end and not start:
		frappe.throw("Renseigne le début réel de la panne avant son rétablissement.")
	if start and get_datetime(start) > now_datetime():
		frappe.throw("Le début réel de la panne ne peut pas être dans le futur.")
	if end and get_datetime(end) > now_datetime():
		frappe.throw("Le rétablissement réel ne peut pas être dans le futur.")
	if start and end and get_datetime(end) <= get_datetime(start):
		frappe.throw("Le rétablissement réel doit être après le début réel de la panne.")


def install_dashboard():
	from frappe.modules.export_file import write_document_file
	from frappe.modules.import_file import import_file_by_path
	from frappe.utils.dashboard import sync_dashboards

	report_json = frappe.get_app_path("iso9001", "iso_9001", "report", "tbq_it", "tbq_it.json")
	workspace_json = frappe.get_app_path(
		"iso9001", "iso_9001", "workspace", "support_it", "support_it.json"
	)
	if os.path.exists(report_json):
		import_file_by_path(report_json, force=True)
	sync_dashboards(app="iso9001")
	if os.path.exists(workspace_json):
		import_file_by_path(workspace_json, force=True)
	ensure_it_project()
	frappe.db.commit()
	if frappe.db.exists("Workspace", "SUPPORT IT"):
		write_document_file(frappe.get_doc("Workspace", "SUPPORT IT"), "ISO 9001")
	return "SUPPORT IT dashboard installed"


def ensure_it_project():
	existing = frappe.db.get_value("Project", {"project_name": IT_PROJECT_NAME}, "name")
	if existing:
		_link_example_tasks(existing)
		_fix_example_panne()
		return existing

	company = frappe.defaults.get_global_default("company") or frappe.db.get_value(
		"Company", {"is_group": 0}, "name"
	)
	if not company:
		return None

	doc = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": IT_PROJECT_NAME,
			"status": "Open",
			"is_active": "Yes",
			"company": company,
			"expected_start_date": "2026-09-01",
			"notes": "Projet de suivi des évolutions ERP du processus SUPPORT IT (ISO 9001).",
		}
	)
	doc.insert(ignore_permissions=True)
	_link_example_tasks(doc.name)
	_fix_example_panne()
	return doc.name


def _link_example_tasks(project):
	if not project:
		return
	names = frappe.get_all("Task", filters={"subject": ["like", "%EXEMPLE IT%"]}, pluck="name")
	for name in names:
		if frappe.db.get_value("Task", name, "project") != project:
			frappe.db.set_value("Task", name, "project", project, update_modified=False)


def _fix_example_panne():
	name = frappe.db.get_value(
		"Issue",
		{"issue_type": ISSUE_PANNE, "subject": ["like", "%EXEMPLE IT%"]},
		"name",
	)
	if not name:
		return
	current = flt(frappe.db.get_value("Issue", name, "resolution_time"))
	if current:
		return
	frappe.db.set_value("Issue", name, "resolution_time", 2 * 3600, update_modified=False)


def _kpi_disponibilite(start, end):
	schedule, holiday_list = _get_work_schedule()
	service_intervals = _service_intervals(start, end, schedule, holiday_list)
	planned = sum((interval_end - interval_start).total_seconds() / 3600 for interval_start, interval_end in service_intervals)
	panne_hours = _panne_hours(start, end, service_intervals)
	available = max(planned - panne_hours, 0)
	value = _ratio(available, planned)
	return {
		"indicator": "Taux de disponibilité ERP",
		"formula": "((Heures de service prévues − panne pendant ces heures) / Heures de service prévues) × 100",
		"frequency": "Mensuelle",
		"target": "≥ 98 %",
		"target_value": 98,
		"value": value,
		"numerator": round(available, 2),
		"denominator": round(planned, 2),
		"unit": "%",
		"source": f"Issue Type « {ISSUE_PANNE} »",
		"conforme": value >= 98 if value is not None else False,
		"detail": f"{round(panne_hours, 2)} h de panne pendant le service / {round(planned, 2)} h prévues",
	}


def _kpi_sauvegardes(start, end):
	planned = (getdate(end) - getdate(start)).days + 1
	ok_days, source = _backup_days(start, end)
	value = _ratio(ok_days, planned)
	return {
		"indicator": "Taux de sauvegardes réussies",
		"formula": "(Sauvegardes réussies / Sauvegardes prévues) × 100",
		"frequency": "Mensuelle",
		"target": "100 %",
		"target_value": 100,
		"value": value,
		"numerator": ok_days,
		"denominator": planned,
		"unit": "%",
		"source": source,
		"conforme": value >= 100 if value is not None else False,
		"detail": f"{ok_days} / {planned}",
	}


def _kpi_demandes(start, end):
	filters = {
		"issue_type": ISSUE_SUPPORT,
		"opening_date": ["between", [start, end]],
	}
	total = frappe.db.count("Issue", filters)
	closed_filters = dict(filters)
	closed_filters["status"] = ["in", CLOSED_SUPPORT]
	closed = frappe.db.count("Issue", closed_filters)
	value = _ratio(closed, total)
	return {
		"indicator": "Taux de demandes utilisateurs traitées",
		"formula": "(Demandes clôturées / Demandes reçues) × 100 — anomalies, demandes d'assistance et accompagnement utilisateurs",
		"frequency": "Mensuelle",
		"target": "≥ 90 %",
		"target_value": 90,
		"value": value,
		"numerator": closed,
		"denominator": total,
		"unit": "%",
		"source": f"Issue Type « {ISSUE_SUPPORT} »",
		"conforme": value >= 90 if value is not None else False,
		"detail": f"{closed} clôturée(s) / {total} reçue(s)",
	}


def _kpi_evolutions(start, end):
	projects = _project_names()
	filters = {}
	if projects:
		filters["project"] = ["in", projects]
	else:
		filters["subject"] = ["like", "%EXEMPLE IT%"]
	tasks = frappe.get_all(
		"Task",
		filters=filters,
		fields=["name", "status", "creation", "exp_start_date", "completed_on"],
	)
	start, end = getdate(start), getdate(end)
	in_period = []
	for task in tasks:
		if task.status in CANCELLED_TASK:
			continue
		dates = [getdate(value) for value in (task.exp_start_date, task.completed_on, task.creation) if value]
		if any(start <= day <= end for day in dates):
			in_period.append(task)
	planned = len(in_period)
	done = len([task for task in in_period if task.status in CLOSED_TASK])
	value = _ratio(done, planned)
	return {
		"indicator": "Taux de réalisation des évolutions ERP",
		"formula": "(Évolutions livrées / Évolutions planifiées) × 100 — rapports, fonctions, applications",
		"frequency": "Mensuelle",
		"target": "≥ 80 %",
		"target_value": 80,
		"value": value,
		"numerator": done,
		"denominator": planned,
		"unit": "%",
		"source": f"Tâche / Projet « {IT_PROJECT_NAME} »",
		"conforme": value >= 80 if value is not None else False,
		"detail": f"{done} livrée(s) / {planned} planifiée(s)",
	}


def _kpi_formations(start, end):
	q_start = get_quarter_start(start)
	q_end = get_quarter_ending(start)
	count = cint(
		frappe.db.sql(
			"""
			select count(*)
			from `tabTraining Plan Item` tpi
			inner join `tabTraining Plan` tp on tp.name = tpi.parent
			where tpi.scheduled_date between %s and %s
			  and (
			  	ifnull(tpi.training_topic, '') like %s
			  	or ifnull(tpi.training_topic, '') like %s
			  	or ifnull(tpi.training_topic, '') like %s
			  )
			""",
			(q_start, q_end, "%ERP%", "%IT%", "%ISO%"),
		)[0][0]
	)
	return {
		"indicator": "Formations IT / ERP réalisées",
		"formula": "Nombre de sessions de formation ERP réalisées dans la période",
		"frequency": "Trimestrielle",
		"target": "≥ 1 / trimestre",
		"target_value": 1,
		"value": flt(count),
		"numerator": count,
		"denominator": 1,
		"unit": "session(s)",
		"source": "Training Plan Item (sujet ERP / IT / ISO)",
		"conforme": count >= 1,
		"detail": f"{count} session(s) du {q_start} au {q_end}",
	}


def _get_work_schedule():
	settings = frappe.get_single("TBQ IT Settings")
	schedule = {}
	for row in settings.weekly_schedule:
		if not row.is_working_day or row.day_of_week not in WEEK_DAYS:
			continue
		schedule[WEEK_DAYS.index(row.day_of_week)] = (get_time(row.start_time), get_time(row.end_time))
	return schedule, settings.holiday_list


def _service_intervals(start, end, schedule, holiday_list=None):
	period_start = datetime.combine(getdate(start), datetime_time.min)
	period_end = datetime.combine(add_days(getdate(end), 1), datetime_time.min)
	intervals = []
	day = getdate(start) - timedelta(days=1)
	last_day = getdate(end)
	while day <= last_day:
		work_time = schedule.get(day.weekday())
		if work_time and not (
			holiday_list and frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": day})
		):
			start_time, end_time = work_time
			service_start = datetime.combine(day, start_time)
			service_end = datetime.combine(day, end_time)
			if service_end <= service_start:
				service_end += timedelta(days=1)
			interval_start = max(service_start, period_start)
			interval_end = min(service_end, period_end)
			if interval_end > interval_start:
				intervals.append((interval_start, interval_end))
		day = add_days(day, 1)
	intervals.sort()
	merged = []
	for interval_start, interval_end in intervals:
		if merged and interval_start <= merged[-1][1]:
			merged[-1] = (merged[-1][0], max(merged[-1][1], interval_end))
		else:
			merged.append((interval_start, interval_end))
	return merged


def _panne_hours(start, end, service_intervals):
	issues = frappe.get_all(
		"Issue",
		filters={"issue_type": ISSUE_PANNE},
		fields=[
			"name",
			"opening_date",
			"opening_time",
			"resolution_time",
			"status",
			"modified",
			"sla_resolution_date",
			"custom_it_panne_debut_reel",
			"custom_it_panne_retablissement_reel",
		],
	)
	hours = 0.0
	now = now_datetime()
	for issue in issues:
		opened = issue.custom_it_panne_debut_reel
		closed = issue.custom_it_panne_retablissement_reel
		if opened:
			opened = get_datetime(opened)
			if closed:
				closed = get_datetime(closed)
			else:
				closed = (
					get_datetime(issue.modified)
					if issue.status in CLOSED_SUPPORT
					else now
				)
		else:
			# Keep historical Issues measurable until IT fills in their actual outage times.
			opened = _opening_datetime(issue.opening_date, issue.opening_time)
			if not opened:
				continue
			if flt(issue.resolution_time):
				closed = opened + timedelta(seconds=flt(issue.resolution_time))
			else:
				closed = _issue_end_datetime(issue, now)

		if not closed or closed <= opened:
			continue
		for interval_start, interval_end in service_intervals:
			downtime_start = max(opened, interval_start)
			downtime_end = min(closed, interval_end)
			if downtime_end > downtime_start:
				hours += (downtime_end - downtime_start).total_seconds() / 3600
	return hours


def _issue_end_datetime(issue, now):
	if issue.sla_resolution_date:
		return get_datetime(issue.sla_resolution_date)
	if issue.status in CLOSED_SUPPORT:
		return get_datetime(issue.modified)
	return now


def _opening_datetime(opening_date, opening_time):
	if not opening_date:
		return None
	time_part = "00:00:00"
	if opening_time:
		if hasattr(opening_time, "total_seconds"):
			time_part = str(timedelta(seconds=int(opening_time.total_seconds())))
		else:
			time_part = str(opening_time)
	try:
		return get_datetime(f"{opening_date} {time_part}")
	except Exception:
		return get_datetime(opening_date)


def _backup_days(start, end):
	days = set()
	source_parts = []

	job_names = frappe.get_all(
		"Scheduled Job Type",
		or_filters={"method": ["like", "%backup%"], "name": ["like", "%backup%"]},
		pluck="name",
	)
	if job_names:
		logs = frappe.get_all(
			"Scheduled Job Log",
			filters={
				"scheduled_job_type": ["in", job_names],
				"status": "Complete",
				"creation": ["between", [start, f"{end} 23:59:59"]],
			},
			fields=["creation"],
		)
		for log in logs:
			days.add(getdate(log.creation))
		if logs:
			source_parts.append("Scheduled Job Log (backup)")

	backup_path = frappe.get_site_path("private", "backups")
	file_days = set()
	if os.path.isdir(backup_path):
		for fname in os.listdir(backup_path):
			match = BACKUP_NAME_RE.search(fname)
			if not match:
				continue
			try:
				file_day = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
			except ValueError:
				continue
			if getdate(start) <= file_day <= getdate(end):
				file_days.add(file_day)
		if file_days:
			source_parts.append("fichiers private/backups")
			days |= file_days

	if not source_parts:
		source_parts.append("aucune preuve de sauvegarde sur la période")

	return len(days), " + ".join(source_parts)


def _project_names():
	return frappe.get_all("Project", filters={"project_name": IT_PROJECT_NAME}, pluck="name")


def _ratio(numerator, denominator):
	if not denominator:
		return None
	return round(flt(numerator) / flt(denominator) * 100, 2)


def _card(value, fieldtype, route, route_options=None):
	payload = {
		"value": flt(value) if value is not None else 0,
		"fieldtype": fieldtype,
		"route": route,
	}
	if route_options:
		clean = {k: v for k, v in route_options.items() if v}
		if clean:
			payload["route_options"] = clean
	return payload


def _as_dict(filters):
	if not filters:
		return {}
	if isinstance(filters, str):
		return frappe.parse_json(filters) or {}
	return dict(filters)

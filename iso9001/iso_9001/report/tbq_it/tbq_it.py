# Copyright (c) 2026, rayan aouf and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from iso9001.iso_9001.it_kpi import compute_kpis


def execute(filters=None):
	kpis = compute_kpis(filters)
	columns = get_columns()
	data = []
	chart_values = []
	for key in ("disponibilite", "sauvegardes", "demandes", "evolutions", "formations"):
		row = kpis[key]
		result = row["value"]
		data.append(
			{
				"indicator": row["indicator"],
				"formula": row["formula"],
				"frequency": row["frequency"],
				"target": row["target"],
				"result": result,
				"detail": row["detail"],
				"conformite": _("Conforme") if row["conforme"] else _("Non conforme"),
				"source": row["source"],
			}
		)
		chart_values.append(result if result is not None else 0)

	message = _(
		"Période {0} – {1}. Revue mensuelle ISO 9001 §9.1 (mois précédent par défaut)."
	).format(kpis["period_start"], kpis["period_end"])

	chart = {
		"data": {
			"labels": [
				_("Disponibilité"),
				_("Sauvegardes"),
				_("Demandes"),
				_("Évolutions"),
				_("Formations"),
			],
			"datasets": [{"name": _("Résultat"), "values": chart_values}],
		},
		"type": "bar",
	}
	return columns, data, message, chart


def get_columns():
	return [
		{"label": _("Indicateur"), "fieldname": "indicator", "fieldtype": "Data", "width": 280},
		{"label": _("Formule"), "fieldname": "formula", "fieldtype": "Data", "width": 360},
		{"label": _("Fréquence"), "fieldname": "frequency", "fieldtype": "Data", "width": 110},
		{"label": _("Cible"), "fieldname": "target", "fieldtype": "Data", "width": 120},
		{"label": _("Résultat"), "fieldname": "result", "fieldtype": "Float", "width": 100},
		{"label": _("Détail"), "fieldname": "detail", "fieldtype": "Data", "width": 220},
		{"label": _("Conformité"), "fieldname": "conformite", "fieldtype": "Data", "width": 130},
		{"label": _("Preuve"), "fieldname": "source", "fieldtype": "Data", "width": 240},
	]

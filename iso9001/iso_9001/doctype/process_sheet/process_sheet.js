// Copyright (c) 2026, rayan aouf and contributors
// For license information, please see license.txt

const IT_INDICATORS = [
	{
		indicator: "Taux de disponibilité ERP",
		calculation_formula: "(Heures d'accessibilité ERP / Heures de travail prévues) × 100",
		target: "≥ 98 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Taux de sauvegardes réussies",
		calculation_formula: "(Sauvegardes réussies / Sauvegardes prévues) × 100",
		target: "100 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Taux de demandes utilisateurs traitées",
		calculation_formula: "(Demandes clôturées / Demandes reçues) × 100 — anomalies, demandes d'assistance et accompagnement utilisateurs",
		target: "≥ 90 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Taux de réalisation des évolutions ERP",
		calculation_formula: "(Évolutions livrées / Évolutions planifiées) × 100 — rapports, fonctions, applications",
		target: "≥ 80 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Formations IT / ERP réalisées",
		calculation_formula: "Nombre de sessions de formation ERP réalisées dans la période",
		target: "≥ 1 / trimestre",
		frequency: "Trimestrielle",
	},
];

function load_it_indicators(frm) {
	if (frm.doc.process_name !== "SUPPORT IT") return;
	if (frm.doc.indicators && frm.doc.indicators.length) return;

	IT_INDICATORS.forEach((item) => {
		let row = frm.add_child("indicators");
		row.indicator = item.indicator;
		row.calculation_formula = item.calculation_formula;
		row.target = item.target;
		row.frequency = item.frequency;
	});
	frm.refresh_field("indicators");
}

frappe.ui.form.on("Process sheet", {
	onload_post_render: function (frm) {
		load_it_indicators(frm);
	},
	process_name: function (frm) {
		if (frm.doc.process_name === "SUPPORT IT") {
			if (!frm.doc.indicators || !frm.doc.indicators.length) {
				load_it_indicators(frm);
			}
		}
	},
});

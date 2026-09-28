// Copyright (c) 2026, rayan aouf and contributors
// For license information, please see license.txt

const IT_INDICATORS = [
	{
		indicator: "Taux de disponibilité ERP / réseau",
		calculation_formula: "(Temps de fonctionnement / Temps total prévu) × 100",
		target: "≥ 98 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Nombre de pannes majeures",
		calculation_formula: "Nombre de pannes bloquantes (ERP, serveur, réseau) sur la période",
		target: "≤ 3 / mois",
		frequency: "Mensuelle",
	},
	{
		indicator: "Délai moyen de rétablissement (MTTR)",
		calculation_formula: "(Somme des durées d'arrêt / Nombre de pannes)",
		target: "≤ 4 heures",
		frequency: "Mensuelle",
	},
	{
		indicator: "Taux de sauvegardes réussies",
		calculation_formula: "(Nombre de sauvegardes réussies / Nombre de sauvegardes planifiées) × 100",
		target: "100 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Nombre d'incidents de sécurité",
		calculation_formula: "Nombre d'incidents de sécurité (accès non autorisé, virus, perte de données)",
		target: "0 incident majeur",
		frequency: "Mensuelle",
	},
	{
		indicator: "Taux de réalisation des mises à jour / maintenances",
		calculation_formula: "(Mises à jour réalisées / Mises à jour planifiées) × 100",
		target: "100 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Taux de traitement des demandes IT",
		calculation_formula: "(Demandes clôturées dans le délai / Demandes reçues) × 100",
		target: "≥ 90 %",
		frequency: "Mensuelle",
	},
	{
		indicator: "Réalisation du test PRA / continuité d'activité",
		calculation_formula: "Test du plan de reprise réalisé selon la planification annuelle",
		target: "1 test / an conforme",
		frequency: "Annuelle",
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

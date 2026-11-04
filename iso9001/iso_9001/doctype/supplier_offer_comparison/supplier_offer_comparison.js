(() => {
	const criteria = ["price", "delivery", "quality", "payment"];

	function showScores(frm) {
		const result = frm.get_field("scoring_summary")?.$wrapper;
		if (!result) return;
		result.empty();
		const weights = criteria.map((key) => Number(frm.doc[`${key}_weight`] || 0));
		if (weights.reduce((sum, weight) => sum + weight, 0) !== 100 ||
			weights.some((weight) => !Number.isInteger(weight) || weight < 0 || weight > 100)) {
			$("<p>").text(__("The weights must be between 0 and 100 and add up to 100%.")).appendTo(result);
			return;
		}

		const offers = (frm.doc.offers || []).map((offer, index) => {
			const points = criteria.map((key) => Number.parseInt(offer[`${key}_rating`], 10) || 0);
			const complete = weights.every((weight, index) => !weight || points[index]);
			return {
				name: offer.supplier_name || __("Offer {0}", [index + 1]),
				score: complete ? weights.reduce((sum, weight, index) => sum + weight * points[index], 0) / 5 : null,
			};
		});

		const scores = $("<ul>").addClass("mb-2").appendTo(result);
		offers.forEach(({ name, score }) => {
			const formatted = score === null
				? __("Rating incomplete")
				: `${format_number(score, null, Number.isInteger(score) ? 0 : 1)} / 100`;
			$("<li>").text(`${name} · ${formatted}`).appendTo(scores);
		});

		if (!offers.length || offers.some(({ score }) => score === null)) {
			$("<p>").text(__("Rate all weighted criteria for each offer to see the recommendation.")).appendTo(result);
			return;
		}

		const best = Math.max(...offers.map(({ score }) => score));
		const winners = offers.filter(({ score }) => score === best).map(({ name }) => name);
		const label = winners.length === 1 ? __("Recommended supplier") : __("Tied for first place");
		$("<p>").append($("<strong>").text(label), ` · ${winners.join(", ")}`).appendTo(result);
	}

	const scoringEvents = (suffix) => Object.fromEntries(
		criteria.map((key) => [`${key}_${suffix}`, showScores])
	);

	frappe.ui.form.on("Supplier Offer Comparison", {
		...scoringEvents("weight"),
		refresh(frm) {
			if (frm.doc.__onload?.invoice_cancelled) {
				frm.set_read_only();
				frm.disable_save();
				frm.refresh_fields();
				frm.set_intro(
					__("The comparison is read-only because the purchase invoice was cancelled."),
					"orange"
				);
			}
			showScores(frm);
		},
	});

	frappe.ui.form.on("Supplier Comparison Offer", {
		...scoringEvents("rating"),
		supplier_name: showScores,
		offers_add: showScores,
		offers_remove: showScores,
	});
})();

# Copyright (c) 2025, rayan aouf and contributors
# For license information, please see license.txt

import re

from frappe.model.document import Document

# Q6 (customer_duration) is demographic, not a satisfaction rating.
SCORED_FIELDS = (
	"overall_satisfaction",
	"quality_price_ratio",
	"sales_team_performance",
	"product_satisfaction",
	"service_reactivity",
	"future_relationship",
	"recommendation_probability",
)


def _normalize_option(text):
	if not text:
		return ""
	cleaned = re.sub(r"[^\w\sàâäéèêëïîôùûüçÀÂÄÉÈÊËÏÎÔÙÛÜÇ'’/-]", " ", str(text), flags=re.UNICODE)
	return " ".join(cleaned.split()).lower()


def answer_score(value, options):
	"""Map a select answer to 0-100. First option = 100, last option = 0."""
	if not value or not options:
		return None

	opts = [opt for opt in str(options).split("\n") if opt]
	if len(opts) < 2:
		return None

	idx = None
	if value in opts:
		idx = opts.index(value)
	else:
		normalized = _normalize_option(value)
		for i, opt in enumerate(opts):
			if _normalize_option(opt) == normalized:
				idx = i
				break

	if idx is None:
		return None

	return ((len(opts) - 1 - idx) / (len(opts) - 1)) * 100


def classify_satisfaction(score):
	if score >= 85:
		return "Très satisfait", "Maintenir et renforcer la relation"
	if score >= 70:
		return "Satisfait à peu près", "Suivi normal"
	if score >= 60:
		return "Peu satisfait", "Actions d'amélioration exigées"
	return "Insatisfait", "Actions correctives exigées"


class CustomerSatisfactionSurvey(Document):
	def validate(self):
		self.calculate_satisfaction_score()

	def calculate_satisfaction_score(self):
		scores = []
		for fieldname in SCORED_FIELDS:
			df = self.meta.get_field(fieldname)
			if not df:
				continue
			score = answer_score(self.get(fieldname), df.options)
			if score is not None:
				scores.append(score)

		if not scores:
			self.satisfaction_score = 0
			self.satisfaction_level = ""
			self.recommended_action = ""
			return

		total = int(round(sum(scores) / len(scores)))
		self.satisfaction_score = total
		self.satisfaction_level, self.recommended_action = classify_satisfaction(total)

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

DOCTYPE = "Supplier Offer Comparison"
INVOICE = "Purchase Invoice"
SCORING_CRITERIA = ("price", "delivery", "quality", "payment")


class SupplierOfferComparison(Document):
	def onload(self):
		self.set_onload(
			"invoice_cancelled", frappe.db.get_value(INVOICE, self.purchase_invoice, "docstatus") == 2
		)

	def before_insert(self):
		invoice = get_submitted_invoice(self.purchase_invoice)
		self.company = invoice.company
		self.invoice_date = invoice.posting_date

		if not self.offers:
			self.append(
				"offers",
				{
					"supplier_name": invoice.supplier_name or invoice.supplier,
					"price": invoice.grand_total,
					"currency": invoice.currency,
				},
			)

	def validate(self):
		previous = self.get_doc_before_save()
		if previous:
			invoice_date = getdate(self.invoice_date) if self.invoice_date else None
			previous_date = getdate(previous.invoice_date) if previous.invoice_date else None
			if (
				self.purchase_invoice != previous.purchase_invoice
				or self.company != previous.company
				or invoice_date != previous_date
			):
				frappe.throw(_("The source invoice details cannot be changed."))

			self.check_invoice_is_editable()

		if not 1 <= len(self.offers) <= 3:
			frappe.throw(_("Enter between one and three supplier offers."))

		self.validate_scoring_weights()

	def get_scoring_weights(self):
		return {criterion: cint(self.get(f"{criterion}_weight")) for criterion in SCORING_CRITERIA}

	def validate_scoring_weights(self):
		weights = self.get_scoring_weights().values()
		if sum(weights) != 100 or any(not 0 <= weight <= 100 for weight in weights):
			frappe.throw(_("The weights must be between 0 and 100 and add up to 100%."))

	def get_scoring_result(self):
		weights = self.get_scoring_weights()
		scores = []
		has_ratings = False
		for offer in self.offers:
			points = {key: cint((offer.get(f"{key}_rating") or "")[:1]) for key in weights}
			has_ratings |= any(points.values())
			if any(weight and not points[key] for key, weight in weights.items()):
				scores.append(None)
			else:
				scores.append(sum(weight * points[key] for key, weight in weights.items()) / 5)

		winners = []
		if scores and None not in scores:
			best = max(scores)
			winners = [offer.supplier_name for offer, score in zip(self.offers, scores) if score == best]

		return {"weights": weights, "scores": scores, "winners": winners, "has_ratings": has_ratings}

	def on_trash(self):
		self.check_invoice_is_editable()

	def check_invoice_is_editable(self):
		if frappe.db.get_value(INVOICE, self.purchase_invoice, "docstatus") != 1:
			frappe.throw(_("The comparison is read-only because the purchase invoice was cancelled."))


@frappe.whitelist(methods=["POST"])
def create_offer_comparison(purchase_invoice: str) -> str:
	invoice = get_submitted_invoice(purchase_invoice)

	# A locking read sees the comparison created by a request that just released the invoice lock.
	existing = frappe.db.get_value(DOCTYPE, {"purchase_invoice": invoice.name}, for_update=True)
	if existing:
		frappe.get_doc(DOCTYPE, existing).check_permission("read")
		return existing

	return frappe.get_doc({"doctype": DOCTYPE, "purchase_invoice": invoice.name}).insert().name


def get_submitted_invoice(name):
	if not name:
		frappe.throw(_("A purchase invoice is required."))

	invoice = frappe.get_doc(INVOICE, name, for_update=True)
	invoice.check_permission("read")
	if not invoice.docstatus.is_submitted():
		frappe.throw(_("Create the comparison from a submitted purchase invoice."))

	return invoice

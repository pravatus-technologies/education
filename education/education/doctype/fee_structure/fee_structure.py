# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import json
import frappe
from frappe import _

from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt


class FeeStructure(Document):
	def validate(self):
		self.calculate_total()
		# self.validate_discount()

	def calculate_total(self):
		"""Calculates total amount."""
		self.total_amount = 0
		for d in self.components:
			self.total_amount += d.amount

	def validate_discount(self):
		for component in self.components:

			if component.discount > 100:
				frappe.throw(
					_("Discount cannot be greater than 100%  in row {0}").format(component.idx)
				)


@frappe.whitelist()
def get_amount_distribution_based_on_fee_plan(
	components, total_amount=0, fee_plan="Monthly"
):

	total_amount = flt(total_amount)
	components = json.loads(components)

	month_list = [
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December",
	]

	month_dict = {
		"Monthly": {"month_list": month_list, "amount": 1 / 12},
		"Quarterly": {
			"month_list": ["April", "July", "October", "January"],
			"amount": 1 / 4,
		},
		"Semi-Annually": {"month_list": ["April", "October"], "amount": 1 / 2},
		"Annually": {"month_list": ["April"], "amount": 1},
	}

	month_list_and_amount = month_dict[fee_plan]

	per_component_amount = {}
	for component in components:
		per_component_amount[component.get("fees_category")] = component.get(
			"amount"
		) * month_list_and_amount.get("amount")

	amount = sum(per_component_amount.values())

	final_month_list = []
	for month in month_list_and_amount.get("month_list"):
		date = frappe.utils.data.get_first_day(month)
		final_month_list.append({"month": month, "due_date": date, "amount": amount})
	return {"distribution": final_month_list, "per_component_amount": per_component_amount}


@frappe.whitelist()
def make_fee_schedule(
	source_name, dialog_values, per_component_amount, target_doc=None
):

	dialog_values = json.loads(dialog_values)
	per_component_amount = json.loads(per_component_amount)

	student_groups = dialog_values.get("student_groups")
	monthly_distribution = [
		month.get("due_date") for month in dialog_values.get("distribution", [])
	]

	for date in monthly_distribution:
		doc = get_mapped_doc(
			"Fee Structure",
			source_name,
			{
				"Fee Structure": {
					"doctype": "Fee Schedule",
				},
				"Fee Component": {"doctype": "Fee Component"},
			},
		)
		doc.due_date = date
		amount_per_month = 0

		for component in doc.components:
			component.amount = per_component_amount.get(component.fees_category)
			amount_per_month += component.amount
		# amount_per_month will be the total amount for each Fee Structure
		doc.total_amount = amount_per_month

		for group in student_groups:
			fee_schedule_student_group = doc.append("student_groups", {})
			fee_schedule_student_group.student_group = group.get("student_group")

		doc.save()

	return len(monthly_distribution)
	# return doc

	# create fee schedule for

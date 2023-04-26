from odoo import models, fields, api,_
from odoo.exceptions import UserError


class InvoiceBillWiz(models.TransientModel):
    _name = 'invoice.bill.wiz'
    _description = 'Invoice Bill WIz'
    
    inv_details_visibility_line = fields.One2many('vendor.invoice.detail', 'inv_bill_wiz_id', 'Invoice Details')
    bill_details_visibility_line = fields.One2many('vendor.bill.detail', 'bill_bill_wiz_id', 'Bill Details')
from odoo import models, fields, api,_
from odoo.exceptions import UserError


class VendorInvoiceDetail(models.TransientModel):
    _name = 'vendor.invoice.detail'
    _description = 'Vendor Invoice Detail'

    vendor_id = fields.Many2one('res.partner','Name')
    invoice_name = fields.Many2one('account.move',string="Invoices",copy=False)
    vendor_amount = fields.Float("Amount")
    released = fields.Boolean('Released')
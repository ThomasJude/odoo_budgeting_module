from odoo import models, fields, api,_
from odoo.exceptions import UserError


class VendorInvoiceDetail(models.TransientModel):
    _name = 'vendor.invoice.detail'
    _description = 'Vendor Invoice Detail'

    vendor_id = fields.Many2one('res.partner','Name')
    invoice_name = fields.Many2one('account.move',string="Invoices",copy=False)
    vendor_amount_invoiced = fields.Float("inv Amount")
    vendor_amount_released = fields.Float("rel Amount")
    released = fields.Boolean('Released')

    user_released = fields.Many2one('user.line.released', string='User Released')
    vendor_released = fields.Many2one('vendor.line.released', string='Vendor Released')
    user_invoiced = fields.Many2one('user.line', string='User invoiced')
    vendor_invoiced = fields.Many2one('vendor.line', string='Vendor invoiced')

    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    partial_due_amount = fields.Float("Partial Due Amount")
    partial_paid_amount = fields.Float("Partial Paid Amount")
from odoo import models, fields, api,_
from odoo.exceptions import UserError


class VendorInvoiceDetail(models.TransientModel):
    _name = 'user.invoice.detail'
    _description = 'User Invoice Detail'

    user_id = fields.Many2one('res.users','Name')
    invoice_name = fields.Many2one('account.move',string="Invoices",copy=False)
    user_amount = fields.Float("Amount")
    released = fields.Boolean("Released")

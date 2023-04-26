from odoo import models, fields, api,_
from odoo.exceptions import UserError


class InvoiceVisibilityWiz(models.TransientModel):
    _name = 'invoice.visibility.wiz'
    _description = 'Invoice Visibility WIz'
    
    invoice_details_visibility_line = fields.One2many('vendor.invoice.detail', 'inv_visibility_wiz_id', 'Invoice Details')

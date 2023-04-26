from odoo import models, fields, api,_
from odoo.exceptions import UserError


class UserInvoiceVisibilityWiz(models.TransientModel):
    _name = 'user.invoice.visibility.wiz'
    _description = 'User Invoice Visibility WIz'
    
    user_invoice_details_visibility_line = fields.One2many('user.invoice.detail', 'user_inv_visibility_wiz_id', 'Invoice Details')

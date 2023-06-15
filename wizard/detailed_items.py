from odoo import models, fields, api,_
from odoo.exceptions import UserError

class DetailedItems(models.TransientModel):
    _name = 'detailed.items'

    name = fields.Text(string='Description', readonly=False)
    user_id = fields.Many2one('res.users', 'User')
    vendor_id = fields.Many2one('res.partner','Vendor')
    invoice_id = fields.Many2one('account.move',string="Invoices",copy=False)
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    item = fields.Many2one('product.template','Item')
    amount = fields.Float('Amount')
    main_product_name = fields.Char("Product Name")
    user_check = fields.Boolean("user_check")


from odoo import models, fields, api,_
from odoo.exceptions import UserError

class VendorBillItems(models.TransientModel):
    _name = 'vendor.bill.items'


    vendor_id = fields.Many2one('res.partner','Vendor')
    bill_id = fields.Many2one('account.move',string="Invoices",copy=False)
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    name = fields.Many2one('product.template','Item')
    description = fields.Text("Description")
    amount = fields.Float('Amount')



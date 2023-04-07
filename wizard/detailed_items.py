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
    # check_released=fields.Boolean(compute='_get_released_value')
    # is_vendor = fields.Boolean('is_vendor')
    # is_user = fields.Boolean('is_user')

    # @api.constrains('vendor_id',"user_id")
    # def check_user_type(self):
    #     print("inside user check function")
    #     for rec in self:
    #         if rec.vendor_id:
    #             rec.is_vendor = True
    #             rec.is_user = False
    #         elif rec.user_id:
    #             rec.is_vendor = False
    #             rec.is_user = True





    # @api.depends('bucket_type_id')
    # def _get_released_value(self):
    #     for rec in self:
    #         invoiced_bucket = self.env['bucket'].sudo().search(
    #             [('bucket_type_id', '=', rec.bucket_type_id.id),
    #              ('bucket_status', '=', 'released')])
    #         if invoiced_bucket:
    #             rec.check_released = True
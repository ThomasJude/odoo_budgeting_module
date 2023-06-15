from odoo import models, fields, api,_
from odoo.exceptions import UserError


class VendorBillDetail(models.TransientModel):
    _name = 'vendor.bill.detail'
    _description = 'Vendor Bill Detail'

    vendor_id = fields.Many2one('res.partner','Name')
    bill_name = fields.Many2one('account.move',string="Bills",copy=False)
    refund_bill_name = fields.Many2one('account.move',string="Refund Bills",copy=False)
    vendor_amount_bill = fields.Float("Bill Amount")
    vendor_amount_paid = fields.Float("Bill Paid Amount")
    vendor_bill_amount_refunded = fields.Float("Bill Refunded Amount")
    vendor_line_released_id = fields.Many2one('vendor.line.released', string='Vendor Released')
    bill_paid = fields.Boolean('Paid')
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    bill_bill_wiz_id = fields.Many2one('invoice.bill.wiz',string="inv/bill wiz Id",copy=False)
    vendor_line_released_from_user_bucket_id = fields.Many2one('vendor.line.released.inside.user', string='Vendor Released from User Bucket')
    debit = fields.Boolean('Debit')



    def show_billed_items(self):
        for record in self:
            fetch_bills = self.env['account.move'].sudo().search([('id', '=', record.bill_name.id)])
            if fetch_bills.state == 'posted' and fetch_bills.invoice_line_ids:
                for move_line_product in fetch_bills.invoice_line_ids:
                    if move_line_product.product_id:
                        vendor_id = self.env["product.supplierinfo"].sudo().search([('product_tmpl_id','=',move_line_product.product_id.product_tmpl_id.id)],limit=1,order="id desc")
                        vendor_id = vendor_id.partner_id
                    else:
                        vendor_id = self.vendor_id
                    existing_bill_item = self.env['vendor.bill.items'].sudo().search([('bill_id','=',record.bill_name.id),('vendor_id','=',record.vendor_id.id),('bucket_type_id','=',record.bucket_type_id.id),('name','=',move_line_product.product_id.product_tmpl_id.id)])
                    if not existing_bill_item and record.vendor_id.id == vendor_id.id:
                        if move_line_product.product_id:
                            record_vals = dict(
                                bill_id=record.bill_name.id,
                                bucket_type_id=record.bucket_type_id.id,
                                vendor_id=record.vendor_id.id,
                                name=move_line_product.product_id.product_tmpl_id.id,
                                amount=move_line_product.price_subtotal
                            )
                        else:
                            record_vals = dict(
                                bill_id=record.bill_name.id,
                                bucket_type_id=record.bucket_type_id.id,
                                vendor_id=record.vendor_id.id,
                                description=move_line_product.name,
                                amount=move_line_product.price_subtotal
                            )
                        self.env['vendor.bill.items'].sudo().create(record_vals)
                    elif existing_bill_item and record.vendor_id.id == vendor_id.id:
                        total = 0
                        for product in fetch_bills.invoice_line_ids:
                            if product.product_id.product_tmpl_id.id == move_line_product.product_id.product_tmpl_id.id:
                                total += product.price_subtotal
                        existing_bill_item.write({'amount':total})
            domain = [('vendor_id', '=', record.vendor_id.id), ('bucket_type_id', '=', record.bucket_type_id.id),
                      ('bill_id', '=', record.bill_name.id)]

            vals = {
                'name': _('Show Bill Items'),
                'type': 'ir.actions.act_window',
                'domain': domain,
                'view_type': 'form',
                'view_mode': 'tree',
                'target':'new',
                'res_model': 'vendor.bill.items',
            }
            return vals



    def see_payments(self):
        for record in self:
            action = self.env.ref('odoo_budgeting_module.action_show_custom_payments').sudo().read()[0]
            domain = [('ref', '=',record.bill_name.name)]  # Replace 'field_name' with the actual field name and self.field_value with your dynamic value
            action.update({'domain': domain})
            return action
from odoo import models, fields, api,_
from odoo.exceptions import UserError


class VendorBillDetail(models.TransientModel):
    _name = 'vendor.bill.detail'
    _description = 'Vendor Bill Detail'

    vendor_id = fields.Many2one('res.partner','Name')
    bill_name = fields.Many2one('account.move',string="Bills",copy=False)
    vendor_amount_bill = fields.Float("Bill Amount")
    vendor_amount_paid = fields.Float("Bill Paid Amount")
    vendor_line_released_id = fields.Many2one('vendor.line.released', string='Vendor Released')
    bill_paid = fields.Boolean('Paid')
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')



    def show_billed_items(self):
        print("SVVVVVVVVVVBBBBBBBBBB")
        for record in self:
            fetch_bills = self.env['account.move'].sudo().search([('id', '=', record.bill_name.id)])
            if fetch_bills.state == 'posted' and fetch_bills.invoice_line_ids:
                # if record.invoice_line_ids:
                for move_line_product in fetch_bills.invoice_line_ids:
                    vendor_id = self.env["product.supplierinfo"].sudo().search([('product_tmpl_id','=',move_line_product.product_id.product_tmpl_id.id)],limit=1,order="id desc")
                    existing_bill_item = self.env['vendor.bill.items'].sudo().search([('bill_id','=',record.bill_name.id),('vendor_id','=',record.vendor_id.id),('bucket_type_id','=',record.bucket_type_id.id),('name','=',move_line_product.product_id.product_tmpl_id.id)])
                    # vendor_line_released_id = self.search([('vendor_id','=',vendor_id.partner_id.id)
                    print("XXXXXXXXXXXXXXXXXXXXXXXX",record.vendor_id.id,vendor_id.partner_id.id,existing_bill_item)
                    if not existing_bill_item and record.vendor_id.id == vendor_id.partner_id.id:
                        record_vals = dict(
                            bill_id=record.bill_name.id,
                            bucket_type_id=record.bucket_type_id.id,
                            vendor_id=record.vendor_id.id,
                            name=move_line_product.product_id.product_tmpl_id.id,
                            amount=move_line_product.price_subtotal
                        )
                        print("inside create")
                        self.env['vendor.bill.items'].sudo().create(record_vals)
                    elif existing_bill_item and record.vendor_id.id == vendor_id.partner_id.id:
                        total = 0
                        for product in fetch_bills.invoice_line_ids:
                            if product.product_id.product_tmpl_id.id == move_line_product.product_id.product_tmpl_id.id:
                                total += product.price_subtotal
                            print("SCXCCCCC",total)
                        existing_bill_item.write({'amount':total})
            domain = [('vendor_id', '=', record.vendor_id.id), ('bucket_type_id', '=', record.bucket_type_id.id),
                      ('bill_id', '=', record.bill_name.id)]

            vals = {
                'name': _('Show Bill Items'),
                'type': 'ir.actions.act_window',
                'domain': domain,
                'view_type': 'form',
                'view_mode': 'tree',
                # 'target':'new',
                'res_model': 'vendor.bill.items',
            }
            return vals
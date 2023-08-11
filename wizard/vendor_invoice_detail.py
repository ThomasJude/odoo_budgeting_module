from odoo import models, fields, api,_
from odoo.exceptions import UserError


class VendorInvoiceDetail(models.TransientModel):
    _name = 'vendor.invoice.detail'
    _description = 'Vendor Invoice Detail'

    vendor_id = fields.Many2one('res.partner','Name')
    invoice_name = fields.Many2one('account.move',string="Invoices",copy=False)
    vendor_amount_invoiced = fields.Float("Invoiced Amount")
    vendor_amount_released = fields.Float("Released Amount")
    released = fields.Boolean('Released')

    user_released = fields.Many2one('user.line.released', string='User Released')
    vendor_released = fields.Many2one('vendor.line.released', string='Vendor Released')
    user_invoiced = fields.Many2one('user.line', string='User invoiced')
    vendor_invoiced = fields.Many2one('vendor.line', string='Vendor invoiced')

    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    partial_due_amount = fields.Float("Partial Due Amount")
    partial_paid_amount = fields.Float("Partial Paid Amount")
    refunded_amount = fields.Float('Refunded Amount')
    refunded_invoice_name = fields.Many2one('account.move',string="Refund Invoices",copy=False)
    inv_bill_wiz_id = fields.Many2one('invoice.bill.wiz',string="inv/bill wiz Id",copy=False)
    inv_visibility_wiz_id = fields.Many2one('invoice.visibility.wiz',string="inv wiz Id",copy=False)
    
    
    def show_detailed_items(self):
        for rec in self:
            invoice = self.env['account.move'].sudo().search([('id','=',rec.invoice_name.id)])
            if invoice.state == 'posted' and invoice.inv_budget_line:
                for inv_budget_line in invoice.inv_budget_line:
                    if inv_budget_line.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                        if inv_budget_line.product_id_budget:
                            record_vals = dict(
                                invoice_id = rec.invoice_name.id,
                                bucket_type_id = inv_budget_line.bucket_type_id.id,
                                vendor_id = rec.vendor_id.id,
                                item = inv_budget_line.product_id_budget.id,
                                amount = inv_budget_line.amount
                            )
                            existing_item = self.env['detailed.items'].sudo().search(
                                [('invoice_id', '=', rec.invoice_name.id), ('vendor_id', '=', rec.vendor_id.id),
                                 ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('item', '=', inv_budget_line.product_id_budget.id)])
                            if existing_item:
                                total = 0
                                for inv_budget_line_items in invoice.inv_budget_line:
                                    if inv_budget_line_items.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line_items.bucket_type_id.id == rec.bucket_type_id.id:
                                        if inv_budget_line_items.product_id_budget.id == existing_item.item.id:
                                            total += inv_budget_line_items.amount
                                for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                    if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                        if product_remaining_budget_line.product_id_budget.id == existing_item.item.id:
                                            total += product_remaining_budget_line.amount
                                existing_item.write({'amount': total})
                            else:
                                self.env['detailed.items'].sudo().create(record_vals)
                        else:
                            if inv_budget_line.name:
                                record_vals = dict(
                                    invoice_id=rec.invoice_name.id,
                                    bucket_type_id=inv_budget_line.bucket_type_id.id,
                                    vendor_id=rec.vendor_id.id,
                                    name=inv_budget_line.name,
                                    amount=inv_budget_line.amount
                                )
                                existing_item = self.env['detailed.items'].sudo().search(
                                    [('invoice_id', '=', rec.invoice_name.id), ('vendor_id', '=', rec.vendor_id.id),
                                     ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                     ('name', '=', inv_budget_line.name)])
                                if existing_item:
                                    total = 0
                                    for inv_budget_line_items in invoice.inv_budget_line:
                                        if inv_budget_line_items.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line_items.bucket_type_id.id == rec.bucket_type_id.id:
                                            if inv_budget_line_items.name == existing_item.name:
                                                total += inv_budget_line_items.amount
                                    for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                        if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                            if product_remaining_budget_line.name == existing_item.name:
                                                total += product_remaining_budget_line.amount
                                    existing_item.write({'amount': total})
                                else:
                                    self.env['detailed.items'].sudo().create(record_vals)

                for product_remaining_budget_line in invoice.product_remaining_budget_line:
                    if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                        if product_remaining_budget_line.product_id_budget:
                            record_vals_rem = dict(
                                invoice_id = rec.invoice_name.id,
                                bucket_type_id = product_remaining_budget_line.bucket_type_id.id,
                                vendor_id = rec.vendor_id.id,
                                item = product_remaining_budget_line.product_id_budget.id,
                                amount = product_remaining_budget_line.amount
                            )
                            existing_item_rem = self.env['detailed.items'].sudo().search(
                                [('invoice_id', '=', rec.invoice_name.id), ('vendor_id', '=', rec.vendor_id.id),
                                 ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                 ('item', '=', product_remaining_budget_line.product_id_budget.id)])
                            if existing_item_rem:
                                total = 0
                                for inv_budget_line_items in invoice.inv_budget_line:
                                    if inv_budget_line_items.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line_items.bucket_type_id.id == rec.bucket_type_id.id:
                                        if inv_budget_line_items.product_id_budget.id == existing_item_rem.item.id:
                                            total += inv_budget_line_items.amount
                                for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                    if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                        if product_remaining_budget_line.product_id_budget.id == existing_item_rem.item.id:
                                            total += product_remaining_budget_line.amount
                                existing_item_rem.write({'amount': total})
                            else:
                                self.env['detailed.items'].sudo().create(record_vals_rem)
                        else:
                            if product_remaining_budget_line:
                                record_vals_rem = dict(
                                    invoice_id=rec.invoice_name.id,
                                    bucket_type_id=product_remaining_budget_line.bucket_type_id.id,
                                    vendor_id=rec.vendor_id.id,
                                    name=product_remaining_budget_line.prod_remaining_id.name,
                                    amount=product_remaining_budget_line.amount
                                )
                            existing_item_rem = self.env['detailed.items'].sudo().search(
                                [('invoice_id', '=', rec.invoice_name.id), ('vendor_id', '=', rec.vendor_id.id),
                                 ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                 ])
                            if existing_item_rem:
                                total = 0
                                for inv_budget_line_items in invoice.inv_budget_line:
                                    if inv_budget_line_items.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line_items.bucket_type_id.id == rec.bucket_type_id.id:
                                        if inv_budget_line_items == existing_item_rem:
                                            total += inv_budget_line_items.amount
                                for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                    if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                        if product_remaining_budget_line.prod_remaining_id.id == existing_item_rem.invoice_id.id:
                                            total += product_remaining_budget_line.amount
                                existing_item_rem.write({'amount': total})
                            else:
                                self.env['detailed.items'].sudo().create(record_vals_rem)

                    domain = [('vendor_id','=',rec.vendor_id.id),('bucket_type_id','=',rec.bucket_type_id.id),('invoice_id','=',rec.invoice_name.id)]

            vals = {
                'name': _('Detailed Items'),
                'type': 'ir.actions.act_window',
                # "type": "ir.actions.client",
                'domain':domain,
                'view_type': 'form',
                'view_mode': 'tree',
                'target':'new',
                'res_model': 'detailed.items',
            }
            return vals

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class UserInvoiceDetail(models.TransientModel):
    _name = 'user.invoice.detail'
    _description = 'User Invoice Detail'

    user_id = fields.Many2one('res.users','Name')
    invoice_name = fields.Many2one('account.move',string="Invoices",copy=False)

    user_released = fields.Many2one('user.line.released',string = 'User Released')
    vendor_released = fields.Many2one('vendor.line.released',string = 'Vendor Released')

    user_invoiced = fields.Many2one('user.line', string='User invoiced')
    vendor_invoiced = fields.Many2one('vendor.line', string='Vendor invoiced')

    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    user_amount_released = fields.Float("Released Amount")
    user_amount_invoiced = fields.Float("Invoiced Amount")
    released = fields.Boolean("Released")

    partial_due_amount = fields.Float("Partial Due Amount")
    partial_paid_amount = fields.Float("Partial Paid Amount")
    refunded_amount = fields.Float('Refunded Amount')
    refunded_invoice_name = fields.Many2one('account.move',string="Refund Invoices",copy=False)
    
    def show_detailed_items(self):
        for rec in self:
            invoice = self.env['account.move'].sudo().search([('id','=',rec.invoice_name.id)])
            if invoice.state == 'posted' and invoice.inv_budget_line:
                for inv_budget_line in invoice.inv_budget_line:
                    if inv_budget_line.budget_user_id.id == rec.user_id.id and inv_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                        if inv_budget_line.product_id_budget:
                            record_vals = dict(
                                invoice_id = rec.invoice_name.id,
                                bucket_type_id = inv_budget_line.bucket_type_id.id,
                                user_id = rec.user_id.id,
                                item = inv_budget_line.product_id_budget.id,
                                amount = inv_budget_line.amount
                            )
                            # print("if product in inv budget line",record_vals)
                            existing_item = self.env['detailed.items'].sudo().search(
                                [('invoice_id', '=', rec.invoice_name.id), ('user_id', '=', rec.user_id.id),
                                 ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('item', '=', inv_budget_line.product_id_budget.id)])
                            if existing_item:
                                total = 0
                                for inv_budget_line in invoice.inv_budget_line:
                                    if inv_budget_line.budget_user_id.id == rec.user_id.id and inv_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                        if inv_budget_line.product_id_budget.id == existing_item.item.id:
                                            total += inv_budget_line.amount
                                for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                    if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                        if product_remaining_budget_line.product_id_budget.id == existing_item.item.id:
                                            total += product_remaining_budget_line.amount
                                existing_item.write({'amount':total})
                            else:
                                self.env['detailed.items'].sudo().create(record_vals)
                        else:
                            if inv_budget_line.name:
                                record_vals = dict(
                                    invoice_id=rec.invoice_name.id,
                                    bucket_type_id=inv_budget_line.bucket_type_id.id,
                                    user_id=rec.user_id.id,
                                    name=inv_budget_line.name,
                                    amount=inv_budget_line.amount
                                )
                                existing_item = self.env['detailed.items'].sudo().search(
                                    [('invoice_id', '=', rec.invoice_name.id), ('user_id', '=', rec.user_id.id),
                                     ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                     ('name', '=', inv_budget_line.name)])
                                if existing_item:
                                    total = 0
                                    for inv_budget_line in invoice.inv_budget_line:
                                        if inv_budget_line.budget_user_id.id == rec.user_id.id and inv_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                            if inv_budget_line.name == existing_item.name:
                                                total += inv_budget_line.amount
                                    for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                        if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                            if product_remaining_budget_line.name == existing_item.name:
                                                total += product_remaining_budget_line.amount
                                    existing_item.write({'amount': total})
                                    # new_amount = existing_name.amount + inv_budget_line.amount
                                    # existing_name.write({'amount': new_amount})
                                else:
                                    self.env['detailed.items'].sudo().create(record_vals)
                            # print("if name in inv budget line",record_vals)

                for product_remaining_budget_line in invoice.product_remaining_budget_line:
                    if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                        if product_remaining_budget_line.product_id_budget:
                            record_vals_remain = dict(
                                invoice_id = rec.invoice_name.id,
                                bucket_type_id = product_remaining_budget_line.bucket_type_id.id,
                                user_id = rec.user_id.id,
                                item = product_remaining_budget_line.product_id_budget.id,
                                amount = product_remaining_budget_line.amount
                            )
                            existing_name_remain = self.env['detailed.items'].sudo().search(
                                [('invoice_id', '=', rec.invoice_name.id), ('user_id', '=', rec.user_id.id),
                                 ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                 ('item', '=', product_remaining_budget_line.product_id_budget.id)])
                            if existing_name_remain:
                                total = 0
                                for inv_budget_line in invoice.inv_budget_line:
                                    if inv_budget_line.budget_user_id.id == rec.user_id.id and inv_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                        if inv_budget_line.product_id_budget.id == existing_name_remain.item.id:
                                            total += inv_budget_line.amount
                                for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                    if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                        if product_remaining_budget_line.product_id_budget.id == existing_name_remain.item.id:
                                            total += product_remaining_budget_line.amount
                                existing_name_remain.write({'amount': total})

                            else:
                                self.env['detailed.items'].sudo().create(record_vals_remain)
                            # print("if product in remaining budget line",record_vals_remain)

                        else:
                            if product_remaining_budget_line.name:
                                record_vals_remain = dict(
                                    invoice_id=rec.invoice_name.id,
                                    bucket_type_id=product_remaining_budget_line.bucket_type_id.id,
                                    user_id=rec.user_id.id,
                                    name=product_remaining_budget_line.name,
                                    amount=product_remaining_budget_line.amount
                                )

                                existing_name_remain = self.env['detailed.items'].sudo().search(
                                    [('invoice_id', '=', rec.invoice_name.id), ('user_id', '=', rec.user_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('name', '=', product_remaining_budget_line.name)])
                                if existing_name_remain:
                                    total = 0
                                    for inv_budget_line in invoice.inv_budget_line:
                                        if inv_budget_line.budget_user_id.id == rec.user_id.id and inv_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                            if inv_budget_line.name == existing_name_remain.name:
                                                total += inv_budget_line.amount
                                    for product_remaining_budget_line in invoice.product_remaining_budget_line:
                                        if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.bucket_type_id.id:
                                            if product_remaining_budget_line.name == existing_name_remain.name:
                                                total += product_remaining_budget_line.amount
                                    print("EXISTING NAME TOTAL",total)
                                    existing_name_remain.write({'amount': total})
                                else:
                                    self.env['detailed.items'].sudo().create(record_vals_remain)
                            # print("if name in remaining budget line",record_vals)

                    # else:
                    #     record_vals = dict(
                    #         invoice_id=rec.bucket_type_id.id,
                    #         bucket_type_id=fixed_reduction_lines.bucket_type_id.id,
                    #         userr_id=rec.vendor_id.id,
                    #     )
                    # self.env['detailed.items'].sudo().create()
        domain = [('user_id', '=', rec.user_id.id), ('bucket_type_id', '=', rec.bucket_type_id.id),('invoice_id', '=', rec.invoice_name.id)]

        vals = {
            'name': _('Show Detailed Items'),
            'type': 'ir.actions.act_window',
            'domain':domain,
            'view_type': 'form',
            'view_mode': 'tree',
            # 'target':'new',
            'res_model': 'detailed.items',
        }
        return vals

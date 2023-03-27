# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class Bucket(models.Model):
    _name = "bucket"
    
    name = fields.Char(string='Name')
    bucket_amount = fields.Float(string='Bucket Amount')
    # user_type = fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    bucket_status = fields.Selection([('invoiced','Invoiced'),('released','Released')], "Bucket Status")
    bucket_type_id = fields.Many2one('bucket.type','Bucket Type')
    vendor_line = fields.One2many('vendor.line', 'vendor_line_bucket_id', 'Vendor Details')
    
    @api.constrains('user_type','bucket_status','bucket_type_id')
    def bucket_user_type_status(self):
        total = 0
        for record in self:
            obj = self.env['bucket'].search([('bucket_status','=',record.bucket_status),('id','!=',record.id),('bucket_type_id','=',record.bucket_type_id.id)])
            if obj:
                raise UserError(_('There is already a bucket exist with same bucket status and bucket type'))
            
            
            
class VendorLine(models.Model):
    _name = "vendor.line"
    
    vendor_id = fields.Many2one('res.partner','Vendors')
    vendor_line_bucket_id = fields.Many2one('bucket','bucket')

    def fetch_vendor_bills_details(self):
        # all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
        #     [('budget_inv_vendor_ids.id', '=', self.vendor_id.id), ('released', '=', False)])
        # all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
        #     [('budget_inv_remaining_vendor_ids.id', '=', self.vendor_id.id), ('released', '=', False)])
        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])

        all_invoices = []
        for invoice_line in all_vendor_invoice_lines:
            all_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_invoices.append(remaining_inv_line.prod_remaining_id)
        rem_duplicate_invoice_no_set = set(all_invoices)
        final_invoice_no = list(rem_duplicate_invoice_no_set)
        for invoices in final_invoice_no:
            total_vendor_amount = 0.0
            total_amount_inv = 0.0
            total_amount_rel = 0.0
            for inv_budget_line in invoices.inv_budget_line:
                # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                    total_amount_inv += inv_budget_line.amount
            for product_remaining_budget_line in invoices.product_remaining_budget_line:
                # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                    total_amount_rel += product_remaining_budget_line.amount

            total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
            existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('vendor_id','=',self.vendor_id.id)])
            if not existing_record:
                create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id":self.vendor_id.id,'invoice_name':invoices.id,'vendor_amount':total_vendor_amount_per_invoice})
        return {
            'name': _('Show In Detail'),
            'domain': [('vendor_id', '=', self.vendor_id.id)],
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target':'new',
            'res_model': 'vendor.invoice.detail',
        }
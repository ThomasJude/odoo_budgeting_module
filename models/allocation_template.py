# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

class AllocationTemplate(models.Model):
    _name = "allocation.template"
    
    name = fields.Char(string='Name',copy=True)
    allocation_temp_line = fields.One2many('allocation.template.line', 'allocation_temp_id', 'Allocation Template',copy=True)
    is_default_temp= fields.Boolean(string='Default Template',default=False,copy=True)
    allocate_sub_bucket = fields.One2many('suballocate.template.line','sub_allocated_id','Sub Bucket Template')

    @api.constrains('name')
    def _check_name_duplicacy(self):
        allocatetemplate = self.env['allocation.template'].search([('name', '=', self.name), ('id', '!=', self.id)])
        if allocatetemplate:
            self.name = allocatetemplate.name + '(copy)'

    @api.constrains('allocation_temp_line')
    def _constrains_allocation_temp(self):
        for allocate in self:
            exist_allocate_list = []
            for line in allocate.allocation_temp_line:
                if line.bucket_type.id in exist_allocate_list:
                    raise ValidationError(_('Bucket Type should be one per line.'))
                exist_allocate_list.append(line.bucket_type.id)
        if not self.allocation_temp_line or len(self.allocation_temp_line) == 0:
            raise ValidationError("You must add at least one template details.")


    @api.model_create_multi
    def create(self, vals_list):
        rec = super(AllocationTemplate, self).create(vals_list)
        if rec.allocation_temp_line:
            for val in rec.allocation_temp_line:
                values = val.bucket_type.id
                bucket_id = self.env['bucket.type'].sudo().search([('complete_name', 'like', val.bucket_type.name),
                                                           ('id', '!=', val.bucket_type.id)])
                print(bucket_id,"bucketidd")
                for val_cr in bucket_id:
                    if val_cr:
                        sub_val = {'bucket_type':val.bucket_type.id,
                                   'sub_bucket_type':val_cr.id,
                                   'assignable_status':val.assignable_status,
                                   'allocate_user_id':val.allocate_user_id.id,
                                   'allocate_percent':0,
                                   'sub_allocated_id':rec.id}
                        self.env['suballocate.template.line'].create(sub_val)
        return rec


    def write(self, vals):
        get_products = self.env["product.template"].sudo().search([('remaining_allocation_temp','=',self.id)])
        res = super(AllocationTemplate,self).write(vals)
        for rec1 in get_products:
            rec1.remaining_allocation_temp_data_val()
        return res


    @api.constrains('is_default_temp')
    def allocation_temp_is_default_temp(self):
        total = 0
        for record in self:
            obj = self.env['allocation.template'].search([('id','!=',record.id),('is_default_temp','=',True)])
            if obj:
                if record.is_default_temp:
                    raise UserError(_('There is already a Default allocation template exist'))

    @api.constrains('allocate_sub_bucket')
    def total_percentage_val_sub(self):
        if self.allocation_temp_line:
            for lines in self.allocation_temp_line:
                if self.allocate_sub_bucket:
                    sub_bucket = []
                    for sub_bucket_list in self.allocate_sub_bucket:
                        sub_bucket.append(sub_bucket_list.bucket_type.id)
                    if lines.bucket_type.id in sub_bucket:
                        total = 0
                        res = self.env['suballocate.template.line'].search([('bucket_type','=',lines.bucket_type.id),('sub_allocated_id','=',self.id)])
                        for res_total in res:
                            total += res_total.allocate_percent
                        if total != 100:
                            raise UserError(_("Sub Bucket Total Percentage should be 100"))


    @api.constrains('allocation_temp_line')
    def total_percentage_val(self):
        total = 0
        sub_total = 0
        if self.allocation_temp_line:
            for lines in self.allocation_temp_line:
                if lines.allocate_percent:
                    total += lines.allocate_percent
            if total!=100:
                raise UserError(_("Total Percentage should be 100"))

class AllocationTemplateLine(models.Model): 
    _name = "allocation.template.line"   

    bucket_type = fields.Many2one('bucket.type',string='Bucket Type',domain="[('sub_buckettype', '=', False)]")
    allocate_percent = fields.Integer("%",default=0 )
    assignable_status = fields.Selection([('assigned','Assigned'),
                                          ('unassigned','Unassigned'),
                                          ('assignable_at_inv','Assignable At Time of Invoice')
                                          ],"Assignable Status",default= "unassigned")
    allocate_user_id = fields.Many2one('res.partner',string='Name')
    product_id = fields.Many2one('product.template',string='Product')
    desc = fields.Text(string='Description', readonly=False)
    allocation_temp_id= fields.Many2one('allocation.template',string='Allocation Template Id')
    is_vendor = fields.Boolean(string='Is Vendor')

    def unlink(self):
        for rec in self:
            for record in rec.allocation_temp_id.allocate_sub_bucket:
                if record and record.bucket_type.id == rec.bucket_type.id:
                    record.unlink()
        res = super(AllocationTemplateLine, self).unlink()
        return res

    @api.constrains('allocate_percent')
    def _constrains_allocate_percent(self):
        for record in self:
            if record.allocate_percent>100:
                raise UserError(_("Percentage should be smaller than 100"))

    @api.onchange('allocate_user_id')
    def _onchange_allocate_user_id(self):
        if self.allocate_user_id:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))


class SubAllocationTemplateLine(models.Model):
    _name = "suballocate.template.line"

    bucket_type = fields.Many2one('bucket.type','Bucket Type',readonly=True)
    sub_bucket_type = fields.Many2one('bucket.type','Sub Bucket Type',readonly=True)
    assignable_status = fields.Selection([('assigned', 'Assigned'),
                                          ('unassigned', 'Unassigned'),
                                          ('assignable_at_inv', 'Assignable At Time of Invoice')
                                          ], "Assignable Status", default="unassigned",readonly=True)
    allocate_user_id = fields.Many2one('res.partner', string='Name',readonly=True)
    allocate_percent = fields.Integer("%", default=0)
    sub_allocated_id = fields.Many2one('allocation.template', string='Allocation Template Id')

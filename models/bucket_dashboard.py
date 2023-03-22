# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class BucketDashboard(models.Model):
    _name = "bucket.dashboard"
    
    bucket_type_id = fields.Many2one('bucket.type','Bucket Type')
    bucket_inv_ids = fields.Many2many('account.move', 'bucket_dashboard_onv', 'bucket_dashboard_id', 'inv_id',string="Invoices",copy=False)
    bucket_inv_count = fields.Integer(string='Invoices', compute='_compute_bucket_inv_ids')
    
    
    @api.depends('bucket_inv_ids')
    def _compute_bucket_inv_ids(self):
        for bucket_dash in self:
            bucket_dash.bucket_inv_count = len(bucket_dash.bucket_inv_ids)
    
    
    def _get_action_view_bucket_invoices(self, invoices):
        '''
        This function returns an action that display linked invoices
        of given bucket. It can either be a in a list or in a form
        view, if there is only one invoice to show.
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
    
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif invoices:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        return action
    
    #
    def action_view_bucket_invoices(self):
        return self._get_action_view_bucket_invoices(self.bucket_inv_ids)
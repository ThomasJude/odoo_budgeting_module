# _*_ Coding: utf-8 _*_

from odoo import models, fields, api


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'

    message = fields.Text('Message', readonly=True)

    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}

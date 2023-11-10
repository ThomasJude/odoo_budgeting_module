from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

class Years(models.Model):
    _name = 'year'

    name = fields.Char('Year',required=True,size=4)

    @api.constrains('name')
    def _check_name_duplicacy(self):
        year = self.env['year'].search([('name', '=', self.name), ('id', '!=', self.id)])
        if year:
            raise UserError(_('Already this year is Exists ! '))
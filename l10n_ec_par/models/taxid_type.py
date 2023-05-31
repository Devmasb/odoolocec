
from odoo import api, fields, models

class TaxIDType(models.Model):
    _name = 'lec.taxid.type'
    _description = "Tax ID Type"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    code = fields.Char('code')
    name = fields.Char('name')
    min_length = fields.Integer('min_length')
    max_length = fields.Integer('max_length')
    default = fields.Boolean('default', default=False)




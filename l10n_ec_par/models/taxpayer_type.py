
from odoo import api, fields, models

class TaxPayerType(models.Model):
    _name = 'lec.taxpayer.type'
    _description = "Tax Payer Type"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    code = fields.Char('code')
    name = fields.Char('name')

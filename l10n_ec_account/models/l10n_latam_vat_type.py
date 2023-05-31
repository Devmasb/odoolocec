from odoo import fields, models, api


class L10nLatamIdentificationType(models.Model):
    _inherit = 'l10n_latam.identification.type'
    code_identification_ec = fields.Char(string='Code Identification')
# Copyright 2004-2011 Pexego Sistemas Informáticos. (http://pexego.es)
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2014-2018 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    imprimir_nota_venta = fields.Boolean(
        string='Imprimir Nota de Venta',related='company_id.imprimir_nota_venta')

    def _compute_imprimir_nota(self):
        for rec in self:
            rec.imprimir_nota_venta = self.env['ir.config_parameter'].sudo().get_param(
                'l10n_ec_reports.imprimir_nota_venta')

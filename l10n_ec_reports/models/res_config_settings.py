from email.policy import default
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    imprimir_nota_venta = fields.Boolean(
        string='Imprimir Nota de Venta', default=False,
        related='company_id.imprimir_nota_venta', readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        #if self.imprimir_nota_venta:
        self.env.company.imprimir_nota_venta=self.imprimir_nota_venta
        #print('Actualizando',self.env.company.imprimir_nota_venta,self.env.company.name)
        # self.env['ir.config_parameter'].set_param(
        #     'nombre_del_parametro_configurable', self.imprimir_nota_venta)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        #print('Obteniendo',self.env.company.imprimir_nota_venta,self.env.company.name)
        res.update(
            imprimir_nota_venta=self.env.company.imprimir_nota_venta
        )
        return res


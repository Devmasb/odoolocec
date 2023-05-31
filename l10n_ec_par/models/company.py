
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
import re

import logging

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'

    help = fields.Char(
        default='** Very large text that I need to display in the res.company form view if it is possible as one '
                'single line depending on the size of the view.',
        readonly=True)

    l10n_latam_identification_type_id = fields.Many2one('l10n_latam.identification.type',
        string="Identification Type", index=True, auto_join=True,
        inverse="_inverse_typepayer",
        default=lambda self: self.env.ref('l10n_latam_base.it_vat', raise_if_not_found=False),
        help="The type of identification")
    vat = fields.Char(string='Identification Number', help="Identification Number for selected type")

    agente_retencion = fields.Boolean(string='Agente retención')
    val_agente_retencion = fields.Char(string='.')

    contribuyente_especial = fields.Boolean(string='Contribuyente Especial')
    val_contribuyente_especial = fields.Char(string='.')

    env_service = fields.Selection(
        [
            ('1', 'Test'),
            ('2', 'Production')
        ],
        string='Environment Type',
        required=True,
        default='1'
    )

    is_force_keep_accounting = fields.Selection(
        [
            ('SI', 'Yes'),
            ('NO', 'No')
        ],
        string = 'Keep Accounting',
        required='True',
        default='NO'
    )
    is_special_taxpayer = fields.Selection(
        [
            ('284', 'Yes'),
            ('000', 'No')
        ],
        string='Special TaxPayer',
        required='True',
        default='000'
    )
    is_microcompany = fields.Boolean(string='Microempresa')
    is_rimpe = fields.Boolean(string='Pertenece a Régimen RIMPE?')
    es_artesano = fields.Boolean(string='Es Artesano')
    registo_artesanal = fields.Char(string='No. Registro')

    #Field add by HDCorp
    rimpe_type = fields.Selection(
        string='Tipo de Rimpe',
        selection=[('neg_emprendedor', 'Negocio Emprendedor'),
                   ('neg_popular', 'Negocio Popular'), ],
        required=False, )


    need_accounting = fields.Selection(
        [
            ('SI', 'SI'),
            ('NO', 'NO')
        ],
        string='Need Accounting',
        required='True',
        default='NO'
    )


    taxid_type = fields.Many2one('lec.taxid.type')
    taxpayer_type = fields.Many2one('lec.taxpayer.type', string='Tax Payer Type')
    property_account_position_id = fields.Many2one('account.fiscal.position',
        string="Fiscal Position",
        related='partner_id.property_account_position_id',
        domain="[('company_id', '=', current_company_id)]",
        inverse='_inverse_taxpayer',
        readonly=False,
        help="The fiscal position determines the taxes/accounts used for this contact.")

    send_sri_data  = fields.Boolean(
        string='Send SRI Data',
        required=False)

    @api.constrains('vat')
    def check_vat(self):
        if self.vat:
            if len(self.vat) < 13:
                raise UserError('The identification number must have 13 characters')
            elif len(self.vat) > 13:
                raise UserError('The identification number must have 13 characters')

    @api.constrains('name','send_sri_data')
    def check_send_sri_data(self):
        pattern = "[a-zA-Z0-9][a-zA-Z0-9\s]+[a-zA-Z0-9\s]"
        pattern_id_informante = "[0-9]{10}001"

        if self.send_sri_data:
            if not self.vat :
                raise UserError('The RUC field can not be empty if you want to send data to SRI')

        if not re.fullmatch(pattern, self.name):
            raise UserError('Invalid Name to send data to SRI')




    # The next method returns the value inserted in res.partner taxpayer_type field and assign to respective field
    # in the res.company form
    def _inverse_taxpayer(self):
        for company in self:
            company.partner_id.property_account_position_id = company.property_account_position_id
    
    def _inverse_typepayer(self):
        for company in self:
            company.partner_id.l10n_latam_identification_type_id = company.l10n_latam_identification_type_id

    # The next method set and assign the value inserted in res.company to the corresponding field in its respective
    # partner's contact payertype in res.partner.

    # @api.model
    # def create(self, vals):
    #     company = super(Company, self).create(vals)
    #     if company.partner_id:
    #         company.partner_id.write({'taxid_type': company.taxid_type.id})
    #     return company

    import re
    from odoo.exceptions import ValidationError

    @api.onchange('email')
    def validate_mail(self):
        if self.email:
            match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', self.email)
            if match == None:
                raise ValidationError('Introduzca dirección de correo Valida')

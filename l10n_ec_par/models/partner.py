from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from . import utils
import re
import logging
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'
    _rec_name = 'display_name'

    vies_passed = fields.Boolean(
        string="VIES validation", default=False, readonly=True)

    agente_retencion = fields.Boolean(string='Agente retención')
    val_agente_retencion = fields.Char(string='.')
    display_name = fields.Char(
        string='Display_name',
        compute='_compute_display_name',
        required=False)

    is_special_taxpayer = fields.Selection(
        [
            ('284', 'Yes'),
            ('000', 'No')
        ],
        string='Special TaxPayer',
        required='True',
        default='000'
    )
    is_force_keep_accounting = fields.Selection(
        [
            ('SI', 'Yes'),
            ('NO', 'No')
        ],
        string='Keep Accounting',
        required='True',
        default='NO'
    )

    taxid_type = fields.Many2one('lec.taxid.type', string='TaxID Type')
    taxpayer_type = fields.Many2one('lec.taxpayer.type', string='Tax Payer Type')

    notify_invoice = fields.Boolean('notify_invoice', default=False)
    notify_shipment = fields.Boolean('notify_shipment', default=False)
    notify_withholding = fields.Boolean('notify_withholding', default=False)

    @api.constrains('vat', 'taxid_type', 'taxpayer_type')
    def check_vat(self):
        for record in self:
            if record.vat:
                if self.l10n_latam_identification_type_id.name == 'RUC' and len(self.vat) < 13:
                    raise UserError('La identificación debe tener 13 caracteres')
                elif self.l10n_latam_identification_type_id.name == 'RUC' and len(self.vat) > 13:
                    raise UserError('La identificación debe tener 13 caracteres')

                if self.l10n_latam_identification_type_id.name == 'Céd' and len(self.vat) < 10:
                    raise UserError('La identificación debe tener 10 caracteres')
                elif self.l10n_latam_identification_type_id.name == 'Céd' and len(self.vat) > 10:
                    raise UserError('La identificación debe tener 10 caracteres')

                tt = record.env['lec.taxid.type'].search([
                    ('id', '=', record.taxid_type.id)])
                if tt.min_length > 0 or tt.max_length > 0:
                    if record.vat == False or len(record.vat) < tt.min_length:
                        raise ValidationError('Tax id is minor than allowed')
                    elif len(record.vat) > tt.max_length:
                        raise ValidationError('Tax id is major than allowed')
                if not record.parent_id:
                    if record.vat in self.env['res.partner'].search(
                            [('vat', '=', record.vat), ('id', '!=', record.id)]).mapped('vat'):
                        raise ValidationError(_('The identification number already exit in the system'))

    @api.depends('vat')
    def _compute_display_name(self):
        for partner in self:
            self.display_name = u'{0} {1}'.format(
                partner.vat,
                partner.name
            )

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        if not args:
            args = []
        if name:
            partners = self.search([('vat', operator, name)] + args, limit=limit)  # noqa
            if not partners:
                partners = self.search([('name', operator, name)] + args, limit=limit)  # noqa
        else:
            partners = self.search(args, limit=limit)
        return partners.name_get()

    @api.onchange('email')
    def validate_mail(self):
        if self.email:
            match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', self.email)
            if match == None:
                raise ValidationError('Introduzca dirección de correo Valida')

    @api.depends('vat', 'name')
    def name_get(self):
        data = []
        for partner in self:
            display_val = u'{0} {1}'.format(
                partner.vat or '*',
                partner.name
            )
            data.append((partner.id, display_val))
        return data

    _sql_constraints = [
        ('vat_unique', 'CHECK(1==1)', ""), ]

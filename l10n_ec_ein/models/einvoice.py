import base64
from io import BytesIO
import os
import itertools
from datetime import datetime
import logging

# from odoo.addons.account.models.account_payment import MAP_INVOICE_TYPE_PARTNER_TYPE
from jinja2 import Environment, FileSystemLoader, Template

from odoo import api, models, fields
from odoo.exceptions import Warning as UserError

from odoo.addons.account_test import report
from odoo.addons.base.models.ir_attachment import IrAttachment
from odoo.tools import safe_eval

from . import utils
from . import edocument

# MAP_INVOICE_TYPE_PARTNER_TYPE.update({'liq_purchase': 'supplier'})
from ..xades.sri import DocumentXML, SriService
import os.path
from os import path

sign = '/tmp/sign.p12'
_logger = logging.getLogger(__name__)
class GrupoImpuestos:
    def __init__(self, codigo, codigoPorcentaje, baseImponible, tarifa, valor):
        self.codigo = codigo
        self.codigoPorcentaje = codigoPorcentaje
        self.baseImponible = baseImponible
        self.tarifa = tarifa
        self.valor = valor


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'account.edocument']
    _logger = logging.getLogger('account.edocument')

    def _default_sri_payment_type(self):
        return self.env['l10n_ec.sri.payment'].search([('code', '=', '01')], limit=1).id
    TEMPLATES = {
        'out_invoice': 'out_invoice.xml',
        'out_refund': 'out_refund.xml',
        'liq_purchase': 'liq_purchase.xml',
        'out_debit': 'debit_note.xml'
    }
    send_mail_flag = fields.Boolean(string="Documento Enviado?")
    to_cancel = fields.Boolean(string="Anular en SRI")
    SriServiceObj = SriService()
    base_imponible_excento_iva = fields.Float(
        string='Base excento de IVA',
        compute='_get_l10n_ec_base',
        store=True
    )
    base_imponible_no_objeto_iva = fields.Float(
        string='Base no objeto de IVA',
        compute='_get_l10n_ec_base',
        store=True
    )
    base_imponible_doce = fields.Float(
        string='Base 12%',
        compute='_get_l10n_ec_base',
        store=True
    )
    base_imponible_cero = fields.Float(
        string='Base 0%',
        compute='_get_l10n_ec_base',
        store=True
    )
    partner_type = fields.Char(
        string='Tipo contribuyente',
        related='partner_id.property_account_position_id.name'
    )

    sri_authorization = fields.Many2one('sri.authorization', copy=False)
    sri_payment_type = fields.Many2one('l10n_ec.sri.payment', string="Payment Method (SRI)", required=1,
                                       default=_default_sri_payment_type, copy=False)
    sri_authorization_date = fields.Char(string='Fecha autorización',
                                         related='sri_authorization.sri_authorization_date')
    auth_number_prov = fields.Char(u'Número de autorización')
    is_liquidation = fields.Boolean(string='Es Liquidacion', default=False)

    total_invoice = fields.Monetary(string='Total Factura', store=True, readonly=True,
        compute='_compute_total_invoice', currency_field='company_currency_id')

    total_invoice = fields.Monetary(string='Total Factura', store=True, readonly=True,
                                    compute='_compute_total_invoice', currency_field='company_currency_id')

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state')
    def _compute_total_invoice(self):
        total = 0.00
        for line in self.line_ids:
            if line.price_subtotal > 0:
                total = total + line.price_subtotal
        self.total_invoice = total
    
    def _info_adicional(self, invoice):
        """
        """
        infoAdicional = {
            'informacionAdicional': 'Adicional'
        }
        return infoAdicional

    def button_draft(self):
        for inv in self:
            if inv.to_cancel:
                raise UserError(
                "No se puede cambiar a borrador una"
                " factura anulada en el SRI"
            )
        return super().button_draft()

    def _info_liquidacion_compra(self, invoice):
        """
        """
        def fix_date(date):
            d = time.strftime('%d/%m/%Y',
                              time.strptime(date, '%Y-%m-%d'))
            return d

        company = invoice.company_id
        partner = invoice.partner_id
        infoLiquidacion = {
            'fechaEmision': self.invoice_date.strftime("%d/%m/%Y"),
            'dirEstablecimiento': partner.street,

            # 'obligadoContabilidad': 'SI',
            'obligadoContabilidad': company.is_force_keep_accounting,

            'tipoIdentificacionProveedor': partner.l10n_latam_identification_type_id.code_identification_ec,  # noqa
            'razonSocialProveedor': partner.name.replace('&', 'AND'),
            'identificacionProveedor': partner.vat,
            'direccionProveedor': partner.street,
            'totalSinImpuestos': '%.2f' % (self.amount_untaxed),
            'totalDescuento': '0.00',
            'importeTotal': '{:.2f}'.format(self.total_invoice),
            'moneda': 'USD',
            'formaPago': self.sri_payment_type.code
        }
        listkeyimpuestos = []
        listimpuestos = []
        for lines in self.invoice_line_ids:
            for tax in lines.tax_ids:
                if tax.tax_group_id.l10n_ec_type not in ['ret_vat_b10', 'ret_vat_srv20', 'ret_vat_b30', 'ret_vat_srv50',
                                                         'ret_vat_srv100', 'ret_vat_srv70', 'ret_ir']:
                    key = [tax.tax_group_id.code, tax.l10n_ec_sri_code]
                    if (key not in listkeyimpuestos):
                        listkeyimpuestos.append(key)
                        listimpuestos.append(GrupoImpuestos(
                            tax.tax_group_id.code,
                            tax.l10n_ec_sri_code,
                            lines.price_subtotal,
                            tax.amount,
                            lines.price_subtotal * (tax.amount / 100)
                        ))
                    else:
                        index = listkeyimpuestos.index(key)
                        listimpuestos[index].baseImponible += lines.price_subtotal
                        listimpuestos[index].valor = listimpuestos[index].baseImponible * (tax.amount / 100)

        totalConImpuestos = []

        for element in listimpuestos:
            totalImpuesto = {
                'codigo': element.codigo,
                'codigoPorcentaje': element.codigoPorcentaje,
                'baseImponible': '{:.2f}'.format(element.baseImponible),
                'tarifa': element.tarifa,
                'valor': '{:.2f}'.format(element.valor)
            }
            totalConImpuestos.append(totalImpuesto)

        infoLiquidacion.update({'totalConImpuestos': totalConImpuestos})
        return infoLiquidacion

    def render_document_liquidacion(self, invoice, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        # formato de plantilla para gasolinera o normal
        einvoice_tmpl = env.get_template(self.TEMPLATES['liq_purchase'])
        data = {}
        data.update(self._info_tributaria(invoice, access_key, emission_code))
        data.update(self._info_liquidacion_compra(invoice))
        detalles = self._detalles(invoice)
        data.update(detalles)
        data.update(self._info_adicional(invoice))
        data.update(self._compute_discount(detalles))
        einvoice = einvoice_tmpl.render(data)
        logging.error(einvoice)
        logging.error("Archivo XML LIQUIDACION")
        logging.error(einvoice)
        return einvoice
    
    def action_generate_eliquidacion(self):
        """
        Metodo de generacion de liquidacion electronica
        TODO: usar celery para enviar a cola de tareas
        la generacion de la factura y envio de email
        """
        for obj in self:
            access_key, emission_code = self._get_codes(name='account.move')
            einvoice = self.render_document_liquidacion(obj, access_key, emission_code)
            inv_xml = DocumentXML(einvoice, 'liq_purchase')
            if not inv_xml.validate_xml():
                raise UserError("Not Valid Schema")

            xades = self.env['sri.key.type'].search([
                ('company_id', '=', self.company_id.id)
            ])
            x_path = "/tmp/ComprobantesGenerados/"
            if not path.exists(x_path):
                os.mkdir(x_path)

            to_sign_file = open(x_path+'LIQUIDACION_SRI_'+self.name+".xml", 'w')
            to_sign_file.write(einvoice)
            to_sign_file.close()
            signed_document = xades.action_sign(to_sign_file)
            try:
                ok, errores = inv_xml.send_receipt(signed_document)
                if not ok:
                    raise UserError(errores)
            except:
                raise UserError("No hemos podido contactar con el SRI, intentolo nuevamente")

            sri_auth = self.env['sri.authorization'].create({
                'sri_authorization_code': access_key,
                'sri_create_date': self.write_date,
                'account_move': self.id,
                'authorization_type':'move',
                'env_service': self.company_id.env_service
            })
            self.write({'sri_authorization': sri_auth.id,
                'auth_number_prov':sri_auth.sri_authorization_code
            })

    def _info_invoice(self):
        """
        """
        company = self.company_id
        partner = self.partner_id

        infoFactura = {
            'fechaEmision': self.invoice_date.strftime("%d/%m/%Y"),
            'dirEstablecimiento': company.street,
            'obligadoContabilidad': company.is_force_keep_accounting,
            'tipoIdentificacionComprador': partner.l10n_latam_identification_type_id.code_identification_ec,
            'razonSocialComprador': partner.name.replace('&', 'AND'),
            'identificacionComprador': partner.vat,
            'direccionComprador': partner.street,
            'totalSinImpuestos': '%.2f' % (self.amount_untaxed),
            'totalDescuento': '0.00',
            'propina': '0.00',
            'importeTotal': '{:.2f}'.format(self.amount_total),
            'moneda': 'USD',
            'formaPago': self.sri_payment_type.code,
            'valorRetIva': '0.00',
            'valorRetRenta': '0.00',
            # 'contribuyenteEspecial': company.is_special_taxpayer
        }

        # Nuevo esquema
        contribuyente_especial = ''
        if (company.contribuyente_especial):
            contribuyente_especial = company.val_contribuyente_especial

            infoFactura.update({
                'contribuyenteEspecial': contribuyente_especial
            })
        print(contribuyente_especial)
        print('Factura', infoFactura)

        listkeyimpuestos = []
        listimpuestos = []
        for lines in self.invoice_line_ids:
            key = [lines.tax_ids.tax_group_id.code, lines.tax_ids.l10n_ec_sri_code]
            if (key not in listkeyimpuestos):
                listkeyimpuestos.append(key)
                listimpuestos.append(GrupoImpuestos(
                    lines.tax_ids.tax_group_id.code,
                    lines.tax_ids.l10n_ec_sri_code,
                    lines.price_subtotal,
                    lines.tax_ids.amount,
                    lines.price_subtotal * (lines.tax_ids.amount / 100)
                ))
            else:
                index = listkeyimpuestos.index(key)
                listimpuestos[index].baseImponible += lines.price_subtotal
                listimpuestos[index].valor = listimpuestos[index].baseImponible * (lines.tax_ids.amount / 100)

        totalConImpuestos = []

        for element in listimpuestos:
            totalImpuesto = {
                'codigo': element.codigo,
                'codigoPorcentaje': element.codigoPorcentaje,
                'baseImponible': '{:.2f}'.format(element.baseImponible),
                'tarifa': element.tarifa,
                'valor': '{:.2f}'.format(element.valor)
            }
            totalConImpuestos.append(totalImpuesto)

        infoFactura.update({'totalConImpuestos': totalConImpuestos})

        if self.move_type == 'out_refund':
            # inv = self.search([('name', '=', self.ref)], limit=1)
            inv = self.search([('id', '=', self.reversed_entry_id.id)], limit=1)
            inv_number = self.reversed_entry_id.l10n_latam_document_number
            notacredito = {
                'codDocModificado': self.reversed_entry_id.l10n_latam_document_type_id.code,  # Modificar
                'numDocModificado': inv_number,
                'motivo': self.ref,
                'fechaEmisionDocSustento': inv.invoice_date.strftime("%d/%m/%Y"),
                'valorModificacion': self.amount_total
            }
            infoFactura.update(notacredito)
        if self.debit_origin_id:
            inv = self.search([('id', '=', self.debit_origin_id.id)], limit=1)
            inv_number = inv.l10n_latam_document_number
            notadebito = {
                'codDocModificado': '01',  # Modificar
                'numDocModificado': inv_number,
                'motivo': self.ref,
                'fechaEmisionDocSustento': inv.invoice_date.strftime("%d/%m/%Y"),
                'valorTotal': '{:.2f}'.format(self.amount_total),
            }
            infoFactura.update(notadebito)
        return infoFactura

    def _motivos(self, invoice):
        """
        """
        def fix_chars(code):
            special = [
                [u'%', ' '],
                [u'º', ' '],
                [u'Ñ', 'N'],
                [u'ñ', 'n']
            ]
            for f, r in special:
                code = code.replace(f, r)
            return code
        motivos = []
        for line in invoice.invoice_line_ids:
            motivo = {
                'razon': fix_chars(line.name.replace('\n', ' ').strip()),
                'valor': '%.2f' % line.price_subtotal,
            }
        motivos.append(motivo)
        return {'motivos': motivos}


    def _detalles(self, invoice):
        """
        """
        def fix_chars(code):
            special = [
                [u'%', ' '],
                [u'º', ' '],
                [u'Ñ', 'N'],
                [u'ñ', 'n']
            ]
            for f, r in special:
                code = code.replace(f, r)
            return code

        detalle_adicional = {
            'nombre': 'Unidad',
            'valor': 1
        }

        detalles = []
        for line in invoice.invoice_line_ids:
            codigoPrincipal = line.product_id and \
                              line.product_id.default_code and \
                              fix_chars(line.product_id.default_code) or '001'
            priced = line.price_unit * (1 - (line.discount or 0.00) / 100.0)
            discount = (line.price_unit - priced) * line.quantity
            detalle = {
                'codigoPrincipal': codigoPrincipal,
                'descripcion': fix_chars(line.name.replace('\n', ' ').strip()),
                'cantidad': '%.6f' % line.quantity,
                'precioUnitario': '%.6f' % line.price_unit,
                'descuento': '%.2f' % discount,
                'precioTotalSinImpuesto': '%.2f' % line.price_subtotal,
                'detalle_adicional': detalle_adicional
            }
            impuestos = []
            if self.l10n_latam_document_type_id.code == '03':

                for tax in line.tax_ids:
                    if tax.tax_group_id.l10n_ec_type not in ['ret_vat_b10', 'ret_vat_srv20', 'ret_vat_b30',
                                                             'ret_vat_srv50', 'ret_vat_srv100', 'ret_vat_srv70',
                                                             'ret_ir']:
                        percent = int(tax.amount)
                        impuesto = {
                            'codigo': tax.tax_group_id.code,
                            'codigoPorcentaje': tax.l10n_ec_sri_code,
                            'tarifa': percent,
                            'baseImponible': '{:.2f}'.format(line.price_subtotal),
                            'valor': '{:.2f}'.format(line.price_subtotal * (tax.amount / 100))
                        }
                        impuestos.append(impuesto)
            else:
                for tax_line in line:
                    percent = int(tax_line.tax_ids.amount)
                    impuesto = {
                        'codigo': tax_line.tax_ids.tax_group_id.code,
                        'codigoPorcentaje': tax_line.tax_ids.l10n_ec_sri_code,
                        'tarifa': percent,
                        'baseImponible': '{:.2f}'.format(tax_line.price_subtotal),
                        'valor': '{:.2f}'.format(tax_line.price_subtotal * (tax_line.tax_ids.amount / 100))
                    }
                    impuestos.append(impuesto)
            detalle.update({'impuestos': impuestos})
            detalles.append(detalle)
        return {'detalles': detalles}

    def fecha_factura(self):
        """
        """
        def fix_date(date):
            d = date.strftime("%d/%m/%Y")
            return d

        if self.move_type == 'out_refund':
            inv = self.search([('id', '=', self.reversed_entry_id.id)], limit=1)
            fecha = fix_date(inv.invoice_date)
        if self.debit_origin_id:
            inv = self.search([('id', '=', self.debit_origin_id.id)], limit=1)
            fecha = fix_date(inv.invoice_date)
        return fecha
    
    def validar_sociedad_publica(self,identificacion):
        coeficientes=[3,2,7,6,5,4,3,2]
        sumadigito=0
        for i in range(len(coeficientes)):
            sumadigito += int(identificacion[i]) * coeficientes[i]
        modulo = 11
        residuo = sumadigito % modulo
        digitoverificador = modulo - residuo
        if digitoverificador == 10:
            digitoverificador = 1
        elif digitoverificador == 11:
            digitoverificador = 0
        return digitoverificador

    def validar_sociedad_privada(self, identificacion):
        coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        sumadigito = 0
        for i in range(len(coeficientes)):
            sumadigito += int(identificacion[i]) * coeficientes[i]
        modulo = 11
        residuo = sumadigito % modulo
        digitoverificador = modulo - residuo
        if digitoverificador == 10:
            digitoverificador = 1
        elif digitoverificador == 11:
            digitoverificador = 0
        return digitoverificador

    def validar_cedula(self, cedula, tipo):
        flag_validate = False

        if (tipo == '05' and len(cedula) == 10):
            flag_validate = True
            print('Cedula')

        if (tipo == '04' and len(cedula) == 13):
            flag_validate = True
            print('RUC')

        if (tipo == '08' and len(cedula) >= 3 and len(cedula) <= 13 and flag_validate != True):
            flag_validate = True
            print('Identificacion del exterior')

        if (tipo == '07' and len(cedula) >= 10 and len(cedula) <= 13):
            flag_validate = True
            print('Consumidor Final')

        print(flag_validate)
        return (flag_validate)

    def render_authorized_einvoice(self, autorizacion):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template('authorized_einvoice.xml')
        auth_xml = {
            'estado': autorizacion.estado,
            'numeroAutorizacion': autorizacion.numeroAutorizacion,
            'ambiente': autorizacion.ambiente,
            'fechaAutorizacion': str(autorizacion.fechaAutorizacion),
            'comprobante': autorizacion.comprobante
        }
        auth_invoice = einvoice_tmpl.render(auth_xml)
        return auth_invoice

    def action_generate_document(self):

        ## Validar cedula cliente
        identifiacion = self.partner_id.vat
        typeident = self.partner_id.l10n_latam_identification_type_id.code_identification_ec
        validate_ident = self.validar_cedula(identifiacion, typeident)
        if (validate_ident):

            if (self.l10n_latam_document_type_id.code == '01'):
                _logger.info('Facturas')
                self.action_generate_einvoice()
            elif (self.l10n_latam_document_type_id.code == '04'):
                _logger.info('Notas de credito')
                self.action_generate_ecredit()

            elif (self.l10n_latam_document_type_id.code == '05'):
                _logger.info('Notas de debito')
                self.action_generate_edebit()
            
            elif (self.l10n_latam_document_type_id.code=='03'):
                _logger.info('#'*100)
                _logger.info('Liquidacion de compra')
                self.action_generate_eliquidacion()
        else:
            raise UserError("Datos del cliente errones, reviselos y vuelva a procesar")
    
    def show_fact_autorization(self):

        access_key, emission_code = self._get_codes(name='account.move')
        # clave_acceso='3006202101035013487000110010100000001613487000119'
        try:
            inv_xml = DocumentXML()
            data, datosfactura = inv_xml.consulta_factura(access_key)
        except:
            raise UserError("No hemos podido contactar con el SRI, intentolo nuevamente")
        message = ''
        if (data):
            mensaje = f'Estado documento: ' + datosfactura.Estado + ' \n Ambiente: ' + datosfactura.Ambiente
            mensaje += ' \n Autorizacion: ' + datosfactura.claveAcceso + ' \n Fecha Autorizacion: ' + str(
                datosfactura.FechaAutorizacion)
            if (datosfactura.Estado == 'AUTORIZADO' and self.sri_authorization.id == False):
                # Añadir el cambio
                _logger.info('Cambio para generacion')
                sri_auth = self.env['sri.authorization'].create({
                    'sri_authorization_code': access_key,
                    'sri_create_date': datosfactura.FechaAutorizacion,
                    'account_move': self.id,
                    'authorization_type': 'move',
                    'env_service': self.company_id.env_service
                })
                self.write({'sri_authorization': sri_auth.id})
                if (self.l10n_latam_document_type_id.code == '03'):
                    self.write({'type': 'in_invoice',
                                'auth_number_prov': sri_auth.sri_authorization_code})
            if (datosfactura.Estado == 'AUTORIZADO' and self.sri_authorization):
                self.sri_authorization.sri_authorization_date = datosfactura.FechaAutorizacion
                self.sri_authorization.processed = True
        else:
            mensaje = 'Documento no ha sido Procesado Electronicamente'

        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': ('Mensaje SRI'),
                'message': mensaje,
                'type':'info',  #types: success,warning,danger,info
                'sticky': False,  #True/False will display for few seconds if false
            },
        }
        if datosfactura.Estado == 'AUTORIZADO':
            self.authorization_state = 'autorizado'

        else:
            self.authorization_state = 'pendiente'

        return notification

    def action_generate_edebit(self):
        for obj in self:
            if obj.move_type not in ['out_invoice']:
                continue
            access_key, emission_code = self._get_codes(name='account.debit')
            einvoice = self.render_document_debit(obj, access_key, emission_code)
            inv_xml = DocumentXML(einvoice, 'out_debit')
            if not inv_xml.validate_xml():
                raise UserError("Not Valid Schema")

            xades = self.env['sri.key.type'].search([
                ('company_id', '=', self.company_id.id)
            ])
            x_path = "/tmp/ComprobantesGenerados/"
            if not path.exists(x_path):
                os.mkdir(x_path)
                
            to_sign_file = open(x_path+'NOTA_DEBITO_SRI_'+self.name+".xml", 'w')
            to_sign_file.write(einvoice)
            to_sign_file.close()
            signed_document = xades.action_sign(to_sign_file)
            try:
                ok, errores = inv_xml.send_receipt(signed_document)
                if not ok:
                    raise UserError(errores)
            except:
                raise UserError("No hemos podido contactar con el SRI, intentolo nuevamente")

            sri_auth = self.env['sri.authorization'].create({
                'sri_authorization_code': access_key,
                'sri_create_date': self.write_date,
                'account_move': self.id,
                'authorization_type': 'move',
                'env_service': self.company_id.env_service
            })
            
            self.write({'sri_authorization': sri_auth.id})
    
    def action_generate_ecredit(self):
        for obj in self:
            if obj.move_type not in ['out_refund']:
                continue
            access_key, emission_code = self._get_codes(name='account.credit')
            einvoice = self.render_document_credit(obj, access_key, emission_code)
            inv_xml = DocumentXML(einvoice, 'out_refund')
            if not inv_xml.validate_xml():
                raise UserError("Not Valid Schema")

            xades = self.env['sri.key.type'].search([
                ('company_id', '=', self.company_id.id)
            ])
            x_path = "/tmp/ComprobantesGenerados/"
            if not path.exists(x_path):
                os.mkdir(x_path)
            # if obj.type == 'out_invoice':
            to_sign_file = open(x_path + 'NOTA_CREDITO_SRI_' + self.name + ".xml", 'w', encoding='utf-8')
            to_sign_file.write(einvoice)
            to_sign_file.close()
            signed_document = xades.action_sign(to_sign_file)
            try:
                ok, errores = inv_xml.send_receipt(signed_document)
                if not ok:
                    raise UserError(errores)
            except:
                raise UserError("No hemos podido contactar con el SRI, intentolo nuevamente")

            sri_auth = self.env['sri.authorization'].create({
                'sri_authorization_code': access_key,
                'sri_create_date': self.write_date,
                'account_move': self.id,
                'authorization_type': 'move',
                'env_service': self.company_id.env_service
            })
            self.write({'sri_authorization': sri_auth.id})

    def action_generate_einvoice(self):
        for obj in self:
            if obj.move_type not in ['out_invoice']:
                continue
            access_key, emission_code = self._get_codes(name='account.move')
            einvoice = self.render_document(obj, access_key, emission_code)
            
            inv_xml = DocumentXML(einvoice, obj.move_type)
            if not inv_xml.validate_xml():
                raise UserError("Not Valid Schema")

            xades = self.env['sri.key.type'].search([
                ('company_id', '=', self.company_id.id)
            ])
            x_path = "/tmp/ComprobantesGenerados/"
            if not path.exists(x_path):
                os.mkdir(x_path)
            to_sign_file = open(x_path + 'FACTURA_SRI_' + self.name + ".xml", 'w',encoding='UTF-8')
            to_sign_file.write(einvoice)
            to_sign_file.close()
            signed_document = xades.action_sign(to_sign_file)
            try:
                ok, errores = inv_xml.send_receipt(signed_document)
                if not ok:
                    raise UserError(errores)
            except:
                raise UserError("No hemos podido contactar con el SRI, intentelo nuevamente %s" % errores )

            sri_auth = self.env['sri.authorization'].create({
                'sri_authorization_code': access_key,
                'sri_create_date': self.write_date,
                'account_move': self.id,
                'authorization_type': 'move',
                'env_service': self.company_id.env_service
            })
            self.write({'sri_authorization': sri_auth.id})

    # rpac - Reprocesar sin generar Auth nueva
    def action_volver(self):
        for obj in self:
            if obj.move_type not in ['out_invoice']:
                continue
            access_key = obj.sri_authorization.sri_authorization_code
            emission_code = '002'
            einvoice = self.render_document(obj, access_key, emission_code)
            inv_xml = DocumentXML(einvoice, obj.move_type)
            if not inv_xml.validate_xml():
                raise UserError("Not Valid Schema")

            xades = self.env['sri.key.type'].search([
                ('company_id', '=', self.company_id.id)
            ])
            x_path = "/tmp/ComprobantesGenerados/"
            if not path.exists(x_path):
                os.mkdir(x_path)
            to_sign_file = open(x_path + 'FACTURA_SRI_' + self.name + ".xml", 'w')
            to_sign_file.write(einvoice)
            to_sign_file.close()
            signed_document = xades.action_sign(to_sign_file)
            print(signed_document)
            try:
                ok, errores = inv_xml.send_receipt(signed_document)
                if not ok:
                    raise UserError(errores)
            except:
                raise UserError("No hemos podido contactar con el SRI, intentolo nuevamente")

    def get_auth(self):
        to_process = self.env['sri.authorization'].search([
            ('processed', '=', False)
        ])

        for data in to_process:
            try:
                xml = DocumentXML()
                id_move = data.account_move.id
                auth, m = xml.request_authorization(data.sri_authorization_code)
                if not auth:
                    msg = ' '.join(list(itertools.chain(*m)))
                    _logger.info(msg)
                    assert False, msg
                data.write({'sri_authorization_date': auth['fechaAutorizacion']})
                data.write({'processed': True})
                auth_einvoice = self.render_authorized_einvoice(auth)
                attach = self.add_attachment(auth_einvoice, auth, id_move)
                message = """
                            DOCUMENTO ELECTRONICO GENERADO <br><br>
                            CLAVE DE ACCESO: %s <br>
                            NUMERO DE AUTORIZACION %s <br>
                            FECHA AUTORIZACION: %s <br>
                            ESTADO DE AUTORIZACION: %s <br>
                            AMBIENTE: %s <br>
                            """ % (
                    auth['numeroAutorizacion'],
                    auth['numeroAutorizacion'],
                    auth['fechaAutorizacion'],
                    auth['estado'],
                    'PRUEBAS' if self.company_id.env_service == '1' else 'PRODUCCION'
                )
                # template_id = self.env.ref(
                #    'l10n_ec_ein.email_template_einvoice').id
                # template = self.env['mail.template'].browse(template_id)
                # template.attachment_ids = [(6, 0, [attach.id])]
                # template.send_mail(self.id, force_send=True)
            except:
                _logger.info("No hemos podido contactar con el SRI, intentolo nuevamente")

    def add_attachment(self, xml_element, auth, id_move):
        buf = BytesIO()
        buf.write(xml_element.encode('utf-8'))
        document = base64.encodebytes(buf.getvalue())
        buf.close()
        ctx = self.env.context.copy()
        ctx.pop('default_type', False)
        attach = self.env['ir.attachment'].with_context(ctx).create(
            {
                'name': '{0}.xml'.format(auth['numeroAutorizacion']),
                'datas': document,
                'db_datas': document,
                'res_model': self._name,
                'res_id': id_move,
                'type': 'binary'
            },
        )
        return attach

    def send_document(self, attachments=None, tmpl=False):
        self.ensure_one()
        self._logger.info('Enviando documento electronico por correo')
        tmpl = self.env.ref(tmpl)
        tmpl.send_mail(  # noqa
            self.id,
            #email_values={'attachment_ids': attachments}
        )
        self.sent = True
        return True
    
    def action_send_mail_pos(self):
        self.ensure_one()
        to_process = self.env['sri.authorization'].search([
            ('account_move', '=', self.id)
        ])
        if self.partner_id.email:
            for data in to_process:
                ambientepp = str(data.sri_authorization_code[23])
                if not data.processed:
                    xml = DocumentXML()
                    id_move = data.account_move.id
                    auth, m = xml.request_authorization(data.sri_authorization_code)
                    if not auth:
                        msg = ' '.join(list(itertools.chain(*m)))
                        raise UserError(msg)
                    data.write({'sri_authorization_date': auth['fechaAutorizacion']})
                    data.write({'processed': True})
                    auth_einvoice = self.render_authorized_einvoice(auth)
                    attach = self.add_attachment(auth_einvoice, auth, id_move)
                    message = """
                            DOCUMENTO ELECTRONICO GENERADO <br><br>
                            CLAVE DE ACCESO: %s <br>
                            NUMERO DE AUTORIZACION %s <br>
                            FECHA AUTORIZACION: %s <br>
                            ESTADO DE AUTORIZACION: %s <br>
                            AMBIENTE: %s <br>
                            """ % (
                        auth['numeroAutorizacion'],
                        auth['numeroAutorizacion'],
                        auth['fechaAutorizacion'],
                        auth['estado'],
                        'PRUEBAS' if ambientepp == '1' else 'PRODUCCION'
                    )
                    data.account_move.message_post(body=message, attachments=[str(auth)])
                else:
                    inv_name = str(data.sri_authorization_code) + '.xml'
                    attach = self.env['ir.attachment'].search([('name', '=',
                                                                inv_name)], limit=1)
                template_id = self.env.ref('l10n_ec_ein.email_template_einvoice').id
                template = self.env['mail.template'].browse(template_id)
                template.attachment_ids = [(6, 0, [attach.id])]
                template.send_mail(self.id, force_send=True)
                self.send_mail_flag = True

    def _compute_discount(self, detalles):
        total = sum([float(det['descuento']) for det in detalles['detalles']])
        return {'totalDescuento': total}

    def render_document(self, invoice, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template(self.TEMPLATES[self.move_type])
        data = {}
        data.update(self._info_tributaria(invoice, access_key, emission_code))
        data.update(self._info_invoice())
        detalles = self._detalles(invoice)

        data.update(detalles)
        data.update(self._compute_discount(detalles))
        einvoice = einvoice_tmpl.render(data)
        return einvoice

    def render_document_debit(self, invoice, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template(self.TEMPLATES['out_debit'])
        data = {}
        data.update(self._info_tributaria(invoice, access_key, emission_code))
        data.update(self._info_invoice())
        detalles = self._detalles(invoice)
        motivos = self._motivos(invoice)
        data.update(detalles)
        data.update(motivos)
        # data.update(self._compute_discount(detalles))
        einvoice = einvoice_tmpl.render(data)
        logging.error("Archivo XML Debito generado")
        logging.error(einvoice)
        return einvoice

    def render_document_credit(self, invoice, access_key, emission_code):
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        einvoice_tmpl = env.get_template(self.TEMPLATES['out_refund'])
        data = {}
        data.update(self._info_tributaria(invoice, access_key, emission_code))
        data.update(self._info_invoice())
        detalles = self._detalles(invoice)
        data.update(detalles)
        # data.update(self._compute_discount(detalles))
        einvoice = einvoice_tmpl.render(data)
        logging.error("Archivo XML Credito generado")
        logging.error(einvoice)
        return einvoice

    def action_cancel_document(self):
        access_key, emission_code = self._get_codes(name='account.move')
        inv_xml = DocumentXML()
        data, datosfactura = inv_xml.consulta_factura(access_key)
        message = ''
        _logger.info(datosfactura.Estado)
        if not (data):
            self.to_cancel = True
            super(AccountMove, self).button_draft()
            super(AccountMove, self).button_cancel()
            mensaje = 'El documento se ha actualizado satisfactoriamente'
            tipo = 'success'

        else:
            # raise UserError("El documento aún no ha sido anulado")
            mensaje = 'El documento aún se encuentra autorizado en el SRI'
            tipo = 'danger'

        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': ('Mensaje SRI'),
                'message': mensaje,
                'type': tipo,  # types: success,warning,danger,info
                'sticky': True,  # True/False will display for few seconds if false
            },
        }
        return notification
        
    def action_send_cliente(self):
        for obj in self:
            if obj.move_type not in ['out_invoice', 'out_refund', 'liq_purchase']:
                continue
        to_process = self.env['sri.authorization'].search([
            ('account_move', '=', self.id)
        ])
        if not self.partner_id.email:
            raise UserError("No se ha registrado un email para este contacto")
        for data in to_process:
            ambientepp = str(data.sri_authorization_code[23])
            if not data.processed:
                xml = DocumentXML()
                id_move = data.account_move.id
                try:
                    auth, m = xml.request_authorization(data.sri_authorization_code)
                    if not auth:
                        msg = ' '.join(list(itertools.chain(*m)))
                        raise UserError(msg)
                except:
                    raise UserError("No hemos podido contactar con el SRI, intentolo nuevamente")

                data.write({'sri_authorization_date': auth['fechaAutorizacion']})
                data.write({'processed': True})
                auth_einvoice = self.render_authorized_einvoice(auth)
                attach = self.add_attachment(auth_einvoice, auth, id_move)
                message = """
                        DOCUMENTO ELECTRONICO GENERADO <br><br>
                        CLAVE DE ACCESO: %s <br>
                        NUMERO DE AUTORIZACION %s <br>
                        FECHA AUTORIZACION: %s <br>
                        ESTADO DE AUTORIZACION: %s <br>
                        AMBIENTE: %s <br>
                        """ % (
                    auth['numeroAutorizacion'],
                    auth['numeroAutorizacion'],
                    auth['fechaAutorizacion'],
                    auth['estado'],
                    'PRUEBAS' if ambientepp == '1' else 'PRODUCCION'
                )
                data.account_move.message_post(body=message, attachments=[str(auth)])
            else:
                inv_name = str(data.sri_authorization_code) + '.xml'
                attach = self.env['ir.attachment'].search([('name', '=',
                                                            inv_name)], limit=1)
                if not attach:
                    for obj in self:
                        try:
                            xml = DocumentXML()
                            id_move = data.account_move.id
                            auth, m = xml.request_authorization(data.sri_authorization_code)
                            auth_einvoice = self.render_authorized_einvoice(auth)
                            attach = self.add_attachment(auth_einvoice, auth, id_move)
                        except:
                            raise UserError(m)

            if (self.l10n_latam_document_type_id.code == '01'):
                _logger.debug('Factura')
                template_id = self.env.ref('l10n_ec_ein.email_template_einvoice').id
            elif (self.l10n_latam_document_type_id.code == '04'):
                _logger.info('Notas de credito')
                template_id = self.env.ref('l10n_ec_ein.email_template_ecreditnot').id
            elif (self.l10n_latam_document_type_id.code == '05'):
                _logger.info('#' * 100)
                _logger.info('Notas de debito')
                template_id = self.env.ref('l10n_ec_ein.email_template_edebitnot').id
            elif (self.l10n_latam_document_type_id.code == '03'):
                _logger.info('#' * 100)
                _logger.info('Liquidacion de compra')
                template_id = self.env.ref('l10n_ec_ein.email_template_eliquidation').id

            # template_id = self.env.ref('l10n_ec_ein.email_template_einvoice').id
            template = self.env['mail.template'].browse(template_id)
            template.attachment_ids = [(6, 0, [attach.id])]
            # if template.send_mail(self.id, force_send=True):
            #     self.send_mail_flag = True
            #     view = self.env.ref('sh_message.sh_message_wizard')
            #     view_id = view and view.id or False
            #     context = dict(self._context or {})
            #     context['message'] = "Correo enviado satisfactoriamente"
            #     return {
            #         'name': 'Comunicado',
            #         'type': 'ir.actions.act_window',
            #         'view_type': 'form',
            #         'view_mode': 'form',
            #         'res_model': 'sh.message.wizard',
            #         'views': [(view.id, 'form')],
            #         'view_id': view.id,
            #         'target': 'new',
            #         'context': context,
            #     }

            return {

                'name': "Enviar e Imprimir",
                'type': "ir.actions.act_window",
                'view_mode': 'form',
                'res_model': 'account.invoice.send',
                'target': 'new',
                # 'domain': [('negociacion', '=', self.id)],
                'context': {'default_template_id': template_id, 'default_attachment_ids': [attach.id], 'default_is_print': False}

            }

    @staticmethod
    def _read_template(type):
        with open(os.path.join(os.path.dirname(__file__), 'templates', type + ".xml")) as template:
            return template

    @staticmethod
    def render(self, template_path, **kwargs):
        return Template( 
            self._read_template(template_path)
        ).substitute(**kwargs)

    @api.onchange('l10n_latam_document_type_id')
    def _onchange_type_doc(self):
        if self.l10n_latam_document_type_id.code == '03':
            self.is_liquidation = True
            # self.type='liq_purchase'
        else:
            self.is_liquidation = False
    
    def action_post(self):
        super(AccountMove, self).action_post()
        for inv in self:
            if inv.l10n_latam_document_type_id.code == '03':
                referencia = inv.l10n_latam_document_number.replace('-', '')
                inv.write({'ref': referencia})
        return True

    @api.depends('amount_untaxed', 'invoice_line_ids')
    def _get_l10n_ec_base(self):
        for rec in self:
            base_imponible_0 = sum(
                line.price_subtotal
                for line in rec.invoice_line_ids
                for taxline in line.tax_ids
                if taxline.tax_group_id.l10n_ec_type == 'zero_vat'
            )
            base_imponible_12 = sum(
                line.price_subtotal
                for line in rec.invoice_line_ids
                for taxline in line.tax_ids
                if taxline.tax_group_id.l10n_ec_type == 'vat12'
            )
            base_imponible_excento = sum(
                line.price_subtotal
                for line in rec.invoice_line_ids
                for taxline in line.tax_ids
                if taxline.tax_group_id.l10n_ec_type == 'exempt_vat'
            )
            base_imponible_no_objeto = sum(
                line.price_subtotal
                for line in rec.invoice_line_ids
                for taxline in line.tax_ids
                if taxline.tax_group_id.l10n_ec_type == 'not_charged_vat'
            )
            rec.base_imponible_cero = base_imponible_0
            rec.base_imponible_doce = base_imponible_12
            rec.base_imponible_excento_iva = base_imponible_excento
            rec.base_imponible_no_objeto_iva = base_imponible_no_objeto

    def _get_unauthorized(self):
        invoice_authorization = self.search([
            ('sri_authorization', '=', False),
            ('move_type', '=', 'out_invoice')
        ])
        for invoice in invoice_authorization:
            try:
               invoice.action_generate_einvoice()
            except:
                continue

    def _get_authorization(self):
        self.get_auth()
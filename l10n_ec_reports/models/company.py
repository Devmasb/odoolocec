# -*- coding: utf-8 -*-

from datetime import timedelta, datetime, date
import calendar
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.tools.misc import format_date
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.tests.common import Form


class ResCompany(models.Model):
    _inherit = "res.company"

    imprimir_nota_venta = fields.Boolean('Imprimir Nota de Venta', default=False)

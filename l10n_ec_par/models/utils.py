# -*- coding: utf-8 -*-
from . import ec


def validator_identifier(vat, taxid_type):
    if taxid_type.code_identification_ec == '05':
        return ec.ci.is_valid(vat)
    elif taxid_type.code_identification_ec == '04':
        return ec.ruc.is_valid(vat)
    else:
        return True

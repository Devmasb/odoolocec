# -*- coding: utf-8 -*-

import os
from io import StringIO, BytesIO
import base64
import logging
import datetime
from lxml import etree
from lxml.etree import fromstring, DocumentInvalid

try:
    from suds.client import Client
except ImportError:
    logging.getLogger('xades.sri').info('Instalar libreria suds-jurko')

class DatosTributarios:
    def __init__(self,claveAcceso='',numeroAutorizacion='',FechaAutorizacion='',Estado='',Ambiente=''):
        self.claveAcceso=claveAcceso
        self.numeroAutorizacion=numeroAutorizacion
        self.FechaAutorizacion=FechaAutorizacion
        self.Estado=Estado
        self.Ambiente=Ambiente


def consulta_factura(clave_acceso):
    print('Consultando el documento para recepcion SRI')
    if len(clave_acceso)!=49:
        raise ('Clave de acceso no es valida')

    flag=False
    sri = SriService()
    datosTributarios =DatosTributarios()
    messages = []
    client = Client(SriService.get_active_ws()[1])
    result = client.service.autorizacionComprobante(clave_acceso)
    print(result)
    # if (result.numeroComprobantes!='0'):

    #     # print(result)
    #     flag=True
    #     autorizacion = result.autorizaciones[0][0]
    #     datosTributarios.claveAcceso=autorizacion.numeroAutorizacion
    #     datosTributarios.numeroAutorizacion=autorizacion.numeroAutorizacion
    #     datosTributarios.FechaAutorizacion=autorizacion.fechaAutorizacion
    #     datosTributarios.Estado=autorizacion.estado
    #     datosTributarios.Ambiente=autorizacion.ambiente
    #     dt=autorizacion.fechaAutorizacion
    #     d_truncated = dt.replace(tzinfo=None)
    #     print(d_truncated)
    #     print(autorizacion.fechaAutorizacion)

    return (flag,datosTributarios)
class SriService(object):
    __AMBIENTE_PRUEBA = '1'
    __AMBIENTE_PROD = '2'
    __ACTIVE_ENV = False
    # revisar el utils
    __WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'  # noqa
    __WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'  # noqa
    __WS_RECEIV = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'  # noqa
    __WS_AUTH = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'  # noqa

    __WS_TESTING = (__WS_TEST_RECEIV, __WS_TEST_AUTH)
    __WS_PROD = (__WS_RECEIV, __WS_AUTH)

    _WSDL = {
        __AMBIENTE_PRUEBA: __WS_TESTING,
        __AMBIENTE_PROD: __WS_PROD
    }
    __WS_ACTIVE = __WS_TESTING
    __WS_ACTIVE1 = __WS_PROD

    @classmethod
    def set_active_env(self, env_service):
        if env_service == self.__AMBIENTE_PRUEBA:
            self.__ACTIVE_ENV = self.__AMBIENTE_PRUEBA
        else:
            self.__ACTIVE_ENV = self.__AMBIENTE_PROD
        self.__WS_ACTIVE = self._WSDL[self.__ACTIVE_ENV]

    @classmethod
    def get_active_env(self):
        return self.__ACTIVE_ENV

    @classmethod
    def get_env_test(self):
        return self.__AMBIENTE_PRUEBA

    @classmethod
    def get_env_prod(self):
        return self.__AMBIENTE_PROD

    @classmethod
    def get_ws_test(self):
        return self.__WS_TEST_RECEIV, self.__WS_TEST_AUTH

    @classmethod
    def get_ws_prod(self):
        return self.__WS_RECEIV, self.__WS_AUTH

    @classmethod
    def get_active_ws(self):
        return self.__WS_ACTIVE
    @classmethod
    def get_active_ws1(self):
        return self.__WS_ACTIVE1

    @classmethod
    def create_access_key(self, values):
        """
        values: tuple ([], [])
        """
        env = '1'
        dato = ''.join(values[0] + [env])
        modulo = CheckDigit.compute_mod11(dato)
        access_key = ''.join([dato, str(modulo)])
        return access_key

clave_acceso='1107202103035013487000110010100000000083487000112'
consulta_factura(clave_acceso)
from decimal import Decimal

import pytest
from pydantic import ValidationError

from procfac.esquema import Factura, Impuesto, Item

CAMPOS = [
    "punto_venta", "numero_comprobante",
    "cuit_emisor", "razon_social_emisor", "domicilio_emisor", "localidad_emisor",
    "condicion_iva_emisor",
    "cuit_receptor", "razon_social_receptor", "domicilio_receptor", "localidad_receptor",
    "condicion_iva_receptor",
    "fecha_comprobante", "condicion_venta", "subtotal", "impuestos", "total", "items",
]


def test_campos_en_orden_y_nullables():
    assert list(Factura.model_fields) == CAMPOS
    factura = Factura()
    assert all(getattr(factura, campo) is None for campo in CAMPOS)


def test_no_admite_campos_extra():
    with pytest.raises(ValidationError):
        Factura(moneda="USD")


def test_cuit_se_normaliza():
    assert Factura(cuit_emisor="30-71234567-8").cuit_emisor == "30712345678"


@pytest.mark.parametrize("cuit", ["123", "30-71234567-89"])
def test_cuit_de_otra_longitud_falla(cuit):
    with pytest.raises(ValidationError):
        Factura(cuit_receptor=cuit)


def test_fecha_valida():
    assert Factura(fecha_comprobante="2026-03-15").fecha_comprobante == "2026-03-15"


@pytest.mark.parametrize("fecha", ["2026-02-30", "15/03/2026"])
def test_fecha_invalida_falla(fecha):
    with pytest.raises(ValidationError):
        Factura(fecha_comprobante=fecha)


def test_importes_se_redondean_half_up():
    factura = Factura(subtotal=1.005, total="2.675", impuestos=[Impuesto(importe="0.125")])
    assert factura.subtotal == Decimal("1.01")
    assert factura.total == Decimal("2.68")
    assert factura.impuestos[0].importe == Decimal("0.13")


def test_cantidad_sin_redondeo():
    item = Item(cantidad=0.3333, precio_unitario=10, subtotal_item=3.333)
    assert item.cantidad == Decimal("0.3333")
    assert item.subtotal_item == Decimal("3.33")


@pytest.mark.parametrize("campo", ["punto_venta", "numero_comprobante"])
def test_enteros_no_negativos(campo):
    assert getattr(Factura(**{campo: 12}), campo) == 12
    with pytest.raises(ValidationError):
        Factura(**{campo: -1})


def test_listas_distinguen_null_de_vacia():
    assert Factura(items=None, impuestos=None).items is None
    factura = Factura(items=[], impuestos=[])
    assert factura.items == [] and factura.impuestos == []

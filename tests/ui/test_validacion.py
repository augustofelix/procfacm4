"""Armado de la factura editada a partir de lo que hay en pantalla (RF-13, RF-16, RF-30)."""

import math
from decimal import Decimal

from procfac.ui.validacion import construir_factura_editada, filas


def test_agregar_y_quitar_filas():
    impuestos = [{"descripcion_impuesto": "IVA 21%", "importe": 210.0}]
    items = [
        {"codigo": "P1", "descripcion": "Tornillo", "cantidad": 2.0, "precio_unitario": 1.0, "subtotal_item": 2.0},
    ]
    # El usuario quita la fila de impuestos y agrega un ítem.
    items.append({"codigo": "P2", "descripcion": "Tuerca", "cantidad": 0.5, "precio_unitario": math.nan,
                  "subtotal_item": None})
    factura = construir_factura_editada({}, [], items, impuestos_era_null=False, items_era_null=False)
    assert factura.impuestos == []
    assert [i.codigo for i in factura.items] == ["P1", "P2"]
    assert factura.items[1].cantidad == Decimal("0.5")
    assert factura.items[1].precio_unitario is None


def test_lista_null_sin_filas_sigue_null_y_con_filas_se_carga():
    assert construir_factura_editada({}, [], [], impuestos_era_null=True, items_era_null=True).items is None
    factura = construir_factura_editada(
        {}, [{"descripcion_impuesto": "IVA", "importe": 1.0}], [], impuestos_era_null=True, items_era_null=True
    )
    assert factura.impuestos[0].importe == Decimal("1.0")


def test_textos_vacios_y_numeros():
    factura = construir_factura_editada(
        {"razon_social_emisor": "  ", "cuit_emisor": "123", "punto_venta": 3, "total": 1.005,
         "subtotal": None, "numero_comprobante": None},
        [], [], impuestos_era_null=False, items_era_null=False,
    )
    assert factura.razon_social_emisor is None
    assert factura.cuit_emisor == "123"
    assert factura.punto_venta == 3
    assert factura.total == Decimal("1.005")
    assert factura.subtotal is None and factura.numero_comprobante is None


def test_filas_para_la_tabla():
    from tests.conftest import factura_de_ejemplo

    tabla = filas(factura_de_ejemplo().items, ["codigo", "precio_unitario"])
    assert tabla[0] == {"codigo": "P001", "precio_unitario": 50.0}
    assert tabla[1]["precio_unitario"] is None
    assert filas(None, ["codigo"]) == []

import json
from decimal import Decimal
from pathlib import Path

import jsonschema

from procfac.esquema import Factura, FacturaEditada, Impuesto, Item, nombre_archivo, serializar_json

ESQUEMA = json.loads(
    (Path(__file__).parents[2] / "specs/001-procesar-factura-a/contracts/esquema-salida.schema.json")
    .read_text(encoding="utf-8")
)


def _factura():
    return Factura(
        punto_venta=1, numero_comprobante=123, cuit_emisor="30712345678",
        razon_social_emisor="Ñandú S.A.", fecha_comprobante="2026-03-15",
        subtotal="1000", total="1210.00",
        impuestos=[Impuesto(descripcion_impuesto="IVA 21%", importe="210")],
        items=[Item(codigo="P1", descripcion="Tornillo", cantidad="2.5", precio_unitario="10",
                    subtotal_item="25")],
    )


def test_formato_del_json():
    contenido = serializar_json(_factura())
    texto = contenido.decode("utf-8")
    assert "Ñandú" in texto
    assert texto.startswith('{\n  "punto_venta": 1,')
    datos = json.loads(texto)
    assert list(datos) == list(Factura.model_fields)
    assert datos["total"] == 1210.0 and isinstance(datos["total"], float)
    assert datos["items"][0]["cantidad"] == 2.5
    assert datos["domicilio_emisor"] is None


def test_mismo_resultado_en_dos_llamadas():
    assert serializar_json(_factura()) == serializar_json(_factura())


def test_la_factura_extraida_cumple_el_esquema():
    jsonschema.validate(json.loads(serializar_json(_factura())), ESQUEMA)
    jsonschema.validate(json.loads(serializar_json(Factura())), ESQUEMA)


def test_nombre_de_archivo():
    assert nombre_archivo(_factura()) == "factura_1_123.json"
    assert nombre_archivo(Factura(punto_venta=1)) == "factura.json"


def test_factura_editada_se_descarga_tal_cual():
    editada = FacturaEditada(
        cuit_emisor="3071234567", fecha_comprobante="2026-02-30", punto_venta=-1,
        total=Decimal("1.005"),
    )
    datos = json.loads(serializar_json(editada))
    assert datos["cuit_emisor"] == "3071234567"
    assert datos["fecha_comprobante"] == "2026-02-30"
    assert datos["punto_venta"] == -1
    assert datos["total"] == 1.005
    # Solo se verifican los tipos JSON, no el esquema (FR-019).
    assert isinstance(datos["punto_venta"], int) and isinstance(datos["total"], float)
    assert list(datos) == list(Factura.model_fields)


def test_factura_editada_desde_la_extraccion():
    factura = _factura()
    editada = FacturaEditada.model_validate(factura.model_dump())
    assert serializar_json(editada) == serializar_json(factura)

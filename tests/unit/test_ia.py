"""Módulo de IA con un cliente de Anthropic simulado: nunca usa la red."""

from types import SimpleNamespace

import pytest

from procfac.ia import FallaExtraccionIA
from procfac.ia.cliente import ExtractorClaude
from procfac.ia.modelos import FacturaIA, ImpuestoIA, ItemIA
from procfac.ia.prompt import INSTRUCCIONES
from tests.conftest import config_de_prueba


def factura_ia(**cambios):
    valores = {
        campo: None if campo in ("punto_venta", "numero_comprobante", "subtotal", "total") else ""
        for campo in FacturaIA.model_fields
    }
    valores.update(
        punto_venta=1, numero_comprobante=123, cuit_emisor="30-71234567-8",
        fecha_comprobante="2026-03-15", subtotal=1000.004, total=1210.005,
        impuestos=[ImpuestoIA(descripcion_impuesto="IVA 21%", importe=210)],
        items=[ItemIA(codigo="P1", descripcion="Tornillo", cantidad=0.3333, precio_unitario=10,
                      subtotal_item=3.333)],
    )
    valores.update(cambios)
    return FacturaIA(**valores)


class MensajesFalsos:
    def __init__(self, respuesta=None, error=None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas: list[dict] = []

    async def parse(self, **kwargs):
        self.llamadas.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.respuesta


def _extractor(respuesta=None, error=None):
    mensajes = MensajesFalsos(respuesta, error)
    return ExtractorClaude(config_de_prueba(), cliente=SimpleNamespace(messages=mensajes)), mensajes


def _respuesta(parsed_output, stop_reason="end_turn"):
    return SimpleNamespace(parsed_output=parsed_output, stop_reason=stop_reason)


def test_cliente_sin_reintentos_y_60_segundos():
    extractor = ExtractorClaude(config_de_prueba())
    assert extractor.cliente.max_retries == 0
    assert extractor.cliente.timeout == 60.0


async def test_una_sola_llamada_con_la_configuracion():
    extractor, mensajes = _extractor(_respuesta(factura_ia()))
    await extractor("texto de la factura")
    assert len(mensajes.llamadas) == 1
    llamada = mensajes.llamadas[0]
    assert llamada["model"] == "claude-opus-5-5"
    assert llamada["max_tokens"] == 16000
    assert llamada["output_config"] == {"effort": "low"}
    assert llamada["output_format"] is FacturaIA
    assert llamada["system"] == INSTRUCCIONES
    assert llamada["messages"] == [{"role": "user", "content": "texto de la factura"}]
    assert "fallbacks" not in llamada


async def test_convierte_a_factura_normalizada():
    extractor, _ = _extractor(_respuesta(factura_ia()))
    factura = await extractor("texto")
    assert factura.cuit_emisor == "30712345678"
    assert str(factura.subtotal) == "1000.00" and str(factura.total) == "1210.01"
    assert str(factura.items[0].cantidad) == "0.3333"
    assert factura.razon_social_emisor is None  # "" de la IA → null


def _uniones(esquema: dict) -> int:
    """Parámetros con tipo unión (anyOf o lista de tipos) en todo el esquema."""
    total = 0
    for definicion in [esquema, *esquema.get("$defs", {}).values()]:
        for propiedad in definicion.get("properties", {}).values():
            total += "anyOf" in propiedad or isinstance(propiedad.get("type"), list)
    return total


def test_esquema_dentro_del_limite_de_uniones_de_la_api():
    # La API rechaza con 400 los esquemas con más de 16 parámetros con uniones.
    assert _uniones(FacturaIA.model_json_schema()) <= 16


def _errores_del_sdk():
    import anthropic
    import httpx

    pedido = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    respuesta = httpx.Response(500, request=pedido)
    return [
        anthropic.APIStatusError("error", response=respuesta, body=None),
        anthropic.APIConnectionError(request=pedido),
        anthropic.APITimeoutError(request=pedido),
    ]


@pytest.mark.parametrize("error", _errores_del_sdk(), ids=lambda e: type(e).__name__)
async def test_errores_del_sdk_son_falla_sin_reintento(error):
    extractor, mensajes = _extractor(error=error)
    with pytest.raises(FallaExtraccionIA):
        await extractor("texto")
    assert len(mensajes.llamadas) == 1


@pytest.mark.parametrize(
    "respuesta",
    [
        _respuesta(factura_ia(), stop_reason="refusal"),
        _respuesta(factura_ia(), stop_reason="max_tokens"),
        _respuesta(None),
    ],
    ids=["refusal", "max_tokens", "sin_salida"],
)
async def test_respuestas_invalidas_son_falla_sin_reintento(respuesta):
    extractor, mensajes = _extractor(respuesta)
    with pytest.raises(FallaExtraccionIA):
        await extractor("texto")
    assert len(mensajes.llamadas) == 1


@pytest.mark.parametrize(
    "cambios, campo",
    [
        ({"fecha_comprobante": "2026-02-31"}, "fecha_comprobante"),  # corrección del profesor
        ({"fecha_comprobante": "2026-02-30"}, "fecha_comprobante"),
        ({"fecha_comprobante": "15/03/2026"}, "fecha_comprobante"),
        ({"cuit_emisor": "123456789"}, "cuit_emisor"),
        ({"subtotal": -1000}, "subtotal"),
        ({"total": -1210}, "total"),
        ({"punto_venta": -1}, "punto_venta"),
    ],
    ids=["31_de_febrero", "30_de_febrero", "otro_formato", "cuit_9_digitos", "subtotal_negativo",
         "total_negativo", "punto_venta_negativo"],
)
async def test_campo_invalido_queda_en_null_sin_falla(cambios, campo):
    """RF-35, AC-43, AC-44: un campo inválido no cancela la extracción."""
    extractor, mensajes = _extractor(_respuesta(factura_ia(**cambios)))
    factura = await extractor("texto")
    assert getattr(factura, campo) is None
    assert factura.numero_comprobante == 123 and factura.cuit_receptor is None
    assert factura.items[0].descripcion == "Tornillo"  # el resto se conserva
    assert len(mensajes.llamadas) == 1


async def test_negativos_en_impuestos_e_items_quedan_en_null():
    respuesta = _respuesta(factura_ia(
        impuestos=[ImpuestoIA(descripcion_impuesto="IVA 21%", importe=-210)],
        items=[ItemIA(codigo="P1", descripcion="Tornillo", cantidad=-2, precio_unitario=-10,
                      subtotal_item=-20)],
    ))
    extractor, _ = _extractor(respuesta)
    factura = await extractor("texto")
    assert factura.impuestos[0].importe is None
    assert factura.impuestos[0].descripcion_impuesto == "IVA 21%"
    item = factura.items[0]
    assert (item.cantidad, item.precio_unitario, item.subtotal_item) == (None, None, None)
    assert item.descripcion == "Tornillo"


async def test_salida_que_no_parsea_es_falla():
    import pydantic

    try:
        FacturaIA.model_validate({"punto_venta": "no"})  # falta todo y el tipo es inválido
    except pydantic.ValidationError as error:
        error_de_parseo = error
    extractor, mensajes = _extractor(error=error_de_parseo)
    with pytest.raises(FallaExtraccionIA):
        await extractor("texto")
    assert len(mensajes.llamadas) == 1

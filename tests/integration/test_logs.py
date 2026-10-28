"""Los logs tienen solo metadatos (RF-33, FR-025, AC-40)."""

import logging
import time

import pytest

from procfac.ia import FallaExtraccionIA
from procfac.ui.validacion import registrar_descarga
from tests.conftest import ExtractorFalso, config_de_prueba, factura_de_ejemplo, pdf_factura_a, texto_comprobante
from tests.integration.conftest import login
from tests.ui.conftest import api, hasta_validacion, ingresar, nueva_app, subir  # noqa: F401

FACTURA = factura_de_ejemplo()
PROHIBIDOS = [
    "EMPRESA EJEMPLO", "30712345678", "30-71234567-8", "Tornillo", "1210", "Comp. Nro",
    "clave-ana", "clave-beto", config_de_prueba().anthropic_api_key, "Bearer",
]


def _lineas(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "procfac"]


def _sin_contenido(lineas, tokens=()):
    for linea in lineas:
        for prohibido in [*PROHIBIDOS, *tokens]:
            assert prohibido not in linea, linea
        for clave in ("usuario=", "operacion=", "resultado=", "duracion_ms="):
            assert clave in linea


@pytest.fixture
def extractor():
    return ExtractorFalso(FACTURA)


async def test_api(cliente, extractor, caplog):
    caplog.set_level(logging.INFO, logger="procfac")
    headers = await login(cliente)
    token = headers["Authorization"].split()[1]
    pdf = pdf_factura_a([texto_comprobante()])
    await cliente.post("/facturas/verificar", headers=headers, files={"archivo": ("b.pdf", pdf_factura_a([texto_comprobante("factura_b")]))})
    await cliente.post("/facturas/extraer", headers=headers, files={"archivo": ("f.pdf", pdf)}, data={"consentimiento": "true"})
    extractor.resultado = FallaExtraccionIA()
    await cliente.post("/facturas/extraer", headers=headers, files={"archivo": ("f.pdf", pdf)}, data={"consentimiento": "true"})
    lineas = _lineas(caplog)
    assert any("resultado=rechazado motivo=no_es_factura_a" in l for l in lineas)
    assert any("resultado=extraido" in l for l in lineas)
    assert any("resultado=falla_ia" in l for l in lineas)
    _sin_contenido(lineas, [token])


def test_ui(api, caplog):  # noqa: F811
    caplog.set_level(logging.INFO, logger="procfac")
    at = subir(ingresar(nueva_app()))
    at.button(key="rechazar").click().run()
    at = hasta_validacion(api)
    at.button(key="cancelar").click().run()
    registrar_descarga("ana", time.time())
    lineas = _lineas(caplog)
    assert any("operacion=consentimiento resultado=rechazado" in l for l in lineas)
    assert any("operacion=validacion resultado=cancelada" in l for l in lineas)
    assert any("operacion=descarga resultado=descargado" in l for l in lineas)
    _sin_contenido(lineas)


def test_sin_archivos_de_log():
    from procfac.logs import configurar_logs

    configurar_logs()
    # Se excluyen los manejadores propios de pytest (escribe a /dev/null).
    manejadores = [
        h for l in (logging.getLogger(), logging.getLogger("procfac")) for h in l.handlers
        if not type(h).__module__.startswith("_pytest")
    ]
    assert manejadores and not any(isinstance(h, logging.FileHandler) for h in manejadores)

import logging

import pytest

from procfac.ia import FallaExtraccionIA
from tests.conftest import ExtractorFalso, pdf_factura_a, texto_comprobante
from tests.integration.conftest import login

PDF = pdf_factura_a([texto_comprobante()])


@pytest.fixture
def extractor():
    return ExtractorFalso(FallaExtraccionIA())


async def test_falla_de_la_ia_responde_502(cliente, extractor, caplog):
    caplog.set_level(logging.INFO, logger="procfac")
    respuesta = await cliente.post(
        "/facturas/extraer", headers=await login(cliente),
        files={"archivo": ("f.pdf", PDF)}, data={"consentimiento": "true"},
    )
    assert respuesta.status_code == 502
    assert respuesta.json() == {"codigo": "falla_extraccion", "mensaje": "No se pudo completar la extracción."}
    assert extractor.llamadas == 1
    assert any("resultado=falla_ia" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("data", [None, {"consentimiento": "false"}])
async def test_sin_consentimiento_no_llama_a_la_ia(cliente, extractor, data):
    respuesta = await cliente.post(
        "/facturas/extraer", headers=await login(cliente), files={"archivo": ("f.pdf", PDF)}, data=data
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "sin_consentimiento"
    assert extractor.llamadas == 0


async def test_cero_archivos_gana_a_sin_consentimiento(cliente, extractor):
    respuesta = await cliente.post("/facturas/extraer", headers=await login(cliente), data={"x": "1"})
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "cantidad_de_archivos"

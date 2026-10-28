"""PDF armados para la prueba y PDF de AC-36 (AC-11, AC-13, AC-14, AC-18, AC-33, AC-36)."""

import json

import pytest

from procfac.esquema import Factura
from procfac.procesamiento import campos_no_obtenidos
from tests.aceptacion.conftest import DATOS, extraer, requerir

pytestmark = pytest.mark.referencia
ARMADOS = DATOS / "armados"


def _rutas_null(esperado: dict) -> list[str]:
    return campos_no_obtenidos(Factura.model_validate(esperado))


async def test_ac36_copias(cliente_real):
    pdf = requerir(ARMADOS / "ac36.pdf")
    esperado = json.loads(requerir(ARMADOS / "ac36.json").read_text(encoding="utf-8"))
    respuesta = await extraer(cliente_real, pdf)
    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()["factura"]["items"]) == len(esperado["items"])


async def test_ac11_campos_no_obtenidos(cliente_real):
    pdf = requerir(ARMADOS / "ac11.pdf")
    esperado = json.loads(requerir(ARMADOS / "ac11.json").read_text(encoding="utf-8"))
    respuesta = await extraer(cliente_real, pdf)
    assert respuesta.status_code == 200, respuesta.text
    assert sorted(respuesta.json()["campos_no_obtenidos"]) == sorted(_rutas_null(esperado))


async def test_ac13_comprobante_ilegible(cliente_real):
    respuesta = await extraer(cliente_real, requerir(ARMADOS / "ac13.pdf"))
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["comprobante_ilegible"] is True


@pytest.mark.parametrize(
    "carpeta, codigo",
    [("ac14", "mas_de_una_factura"), ("ac18", "no_es_factura_a"), ("ac33.pdf", "mas_de_3_paginas")],
)
async def test_rechazos_sin_llamar_a_claude(cliente_real, carpeta, codigo):
    ruta = requerir(ARMADOS / carpeta)
    pdfs = sorted(ruta.glob("*.pdf")) if ruta.is_dir() else [ruta]
    for pdf in pdfs:
        # /verificar nunca llama a Claude; /extraer verifica antes de llamar.
        for endpoint in ("/facturas/verificar", "/facturas/extraer"):
            respuesta = await cliente_real.post(
                endpoint, files={"archivo": (pdf.name, pdf.read_bytes())}, data={"consentimiento": "true"}
            )
            assert respuesta.status_code == 422, f"{pdf.name}: {respuesta.text}"
            assert respuesta.json()["codigo"] == codigo, pdf.name

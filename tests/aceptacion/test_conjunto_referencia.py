"""Precisión y tiempos sobre el Conjunto de referencia (RNF-02, RNF-03, RNF-04)."""

import asyncio
import json
import logging
import time

import jsonschema
import pytest

from tests.aceptacion.conftest import DATOS, extraer, requerir
from tests.aceptacion.metricas import comparar, p95, precision
from tests.integration.test_flujo_api import ESQUEMA

pytestmark = pytest.mark.referencia
UMBRAL = 0.9


def _facturas():
    carpeta = requerir(DATOS / "referencia")
    pdfs = sorted(carpeta.glob("*.pdf"))
    if not pdfs:
        pytest.skip("tests/data/referencia/ no tiene PDF")
    return [(pdf, json.loads(pdf.with_suffix(".json").read_text(encoding="utf-8"))) for pdf in pdfs]


def _valores_sensibles(esperados):
    """Textos de los JSON esperados que no pueden aparecer en los logs (SC-010)."""
    valores = set()
    for esperado in esperados:
        pendientes = [esperado]
        while pendientes:
            actual = pendientes.pop()
            if isinstance(actual, dict):
                pendientes.extend(actual.values())
            elif isinstance(actual, list):
                pendientes.extend(actual)
            elif isinstance(actual, str) and len(actual) >= 5:
                valores.add(actual)
    return valores


async def test_precision_y_tiempo_de_a_una(cliente_real, config, caplog):
    caplog.set_level(logging.INFO, logger="procfac")
    facturas = _facturas()
    resultados, tiempos = [], []
    for pdf, esperado in facturas:
        inicio = time.perf_counter()
        respuesta = await extraer(cliente_real, pdf)
        tiempos.append(time.perf_counter() - inicio)
        assert respuesta.status_code == 200, f"{pdf.name}: {respuesta.text}"
        obtenido = respuesta.json()["factura"]
        jsonschema.validate(obtenido, ESQUEMA)  # AC-01
        resultados.append(comparar(obtenido, esperado))

    por_campo = precision(resultados)
    print("\nPrecisión por campo:")
    for campo, valor in sorted(por_campo.items()):
        print(f"  {campo:28} {valor:6.1%}")
    print(f"p95 de {len(tiempos)} tiempos: {p95(tiempos):.1f} s")

    # Aproxima SC-001: aceptar el consentimiento dispara esta llamada; el render de
    # Streamlit queda fuera y se verifica a mano (quickstart, escenario 5).
    assert p95(tiempos) < 30  # AC-27
    assert {c: v for c, v in por_campo.items() if v < UMBRAL} == {}  # AC-15, 16, 20, 21, 31

    lineas = [r.getMessage() for r in caplog.records if r.name == "procfac"]
    sensibles = _valores_sensibles(e for _, e in facturas) | {config.anthropic_api_key}
    assert not [l for l in lineas if any(v in l for v in sensibles)]  # SC-010, AC-40


async def test_cinco_a_la_vez(cliente_real):
    facturas = _facturas()[:5]

    async def medir(pdf):
        inicio = time.perf_counter()
        respuesta = await extraer(cliente_real, pdf)
        return respuesta, time.perf_counter() - inicio

    for (pdf, _), (respuesta, segundos) in zip(facturas, await asyncio.gather(*(medir(p) for p, _ in facturas))):
        assert respuesta.status_code == 200, pdf.name
        assert segundos < 30, f"{pdf.name}: {segundos:.1f} s"  # AC-29

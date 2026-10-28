"""Ninguna sesión recibe datos del proceso de otra (AC-04, AC-29, AC-30, AC-38)."""

import asyncio
import re
import time

import pytest

from tests.conftest import ExtractorFalso, factura_de_ejemplo, pdf_factura_a, texto_comprobante
from tests.integration.conftest import login


def _factura_segun_texto(texto):
    numero = int(re.search(r"Comp\. Nro: (\d+)", texto).group(1))
    return factura_de_ejemplo(numero_comprobante=numero, razon_social_emisor=f"EMISOR {numero}")


@pytest.fixture
def extractor():
    return ExtractorFalso(_factura_segun_texto, demora=0.5)


async def test_cinco_sesiones_a_la_vez(cliente, app):
    app.state.autenticador._usuarios.update({"u3": "clave-u3", "u4": "clave-u4"})
    sesiones = ["ana", "ana", "beto", "u3", "u4"]  # dos sesiones del mismo usuario
    cabeceras = [await login(cliente, u) for u in sesiones]

    async def extraer(headers, numero):
        pdf = pdf_factura_a([texto_comprobante(numero=numero)])
        return await cliente.post(
            "/facturas/extraer", headers=headers,
            files={"archivo": ("f.pdf", pdf)}, data={"consentimiento": "true"},
        )

    inicio = time.perf_counter()
    respuestas = await asyncio.gather(*(extraer(h, 1000 + i) for i, h in enumerate(cabeceras)))
    assert time.perf_counter() - inicio < 30
    for i, respuesta in enumerate(respuestas):
        factura = respuesta.json()["factura"]
        assert factura["numero_comprobante"] == 1000 + i
        otros = {f"EMISOR {1000 + j}" for j in range(5) if j != i}
        assert not any(otro in respuesta.text for otro in otros)


async def test_b_no_ve_datos_de_a(cliente):
    a, b = await login(cliente, "ana"), await login(cliente, "beto")
    pdf_a = pdf_factura_a([texto_comprobante(numero=777)])

    tarea_a = asyncio.create_task(cliente.post(
        "/facturas/extraer", headers=a, files={"archivo": ("a.pdf", pdf_a)}, data={"consentimiento": "true"}
    ))
    await asyncio.sleep(0.1)
    respuestas_b = [
        await cliente.post("/facturas/verificar", headers=b, files={"archivo": ("b.pdf", pdf_factura_a([texto_comprobante(numero=1)]))}),
        await cliente.post("/auth/login", json={"usuario": "beto", "clave": "clave-beto"}),
    ]
    respuesta_a = await tarea_a
    assert respuesta_a.json()["factura"]["razon_social_emisor"] == "EMISOR 777"
    for respuesta in respuestas_b:
        assert "777" not in respuesta.text and "EMISOR" not in respuesta.text

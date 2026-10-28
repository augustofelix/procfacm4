"""Rechazos antes de llamar a la IA (principio V; AC-14, AC-18, AC-19, AC-33, AC-35)."""

import pytest

from tests.conftest import (
    COMPROBANTES, pdf_danado, pdf_escaneado, pdf_factura_a, pdf_n_paginas, pdf_protegido,
    texto_comprobante,
)
from tests.integration.conftest import login

RUTAS = ["/facturas/verificar", "/facturas/extraer"]
MENSAJES = {
    "cantidad_de_archivos": "Debe enviarse exactamente un archivo PDF.",
    "no_es_pdf": "El archivo no es un PDF.",
    "mas_de_3_paginas": "El PDF supera las 3 páginas.",
    "no_es_factura_a": "No se pudo identificar el comprobante como factura A.",
    "mas_de_una_factura": "El PDF contiene más de una factura.",
}

FUERA_DE_ALCANCE = {
    **{tipo: pdf_factura_a([texto_comprobante(tipo)]) for tipo in COMPROBANTES if tipo != "factura_a"},
    "protegido": pdf_protegido(),
    "escaneado": pdf_escaneado(),
    "danado": pdf_danado(),
    "no_identificable": pdf_factura_a(["Documento sin datos de comprobante, solo texto libre."]),
}


async def _enviar(cliente, ruta, files):
    data = {"consentimiento": "true"} if ruta.endswith("extraer") else None
    return await cliente.post(ruta, headers=await login(cliente), files=files, data=data)


def _verificar(respuesta, codigo, extractor):
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json() == {"codigo": codigo, "mensaje": MENSAJES[codigo]}
    assert extractor.llamadas == 0


@pytest.mark.parametrize("ruta", RUTAS)
@pytest.mark.parametrize(
    "files",
    [None, [("archivo", ("a.pdf", b"%PDF-a")), ("archivo", ("b.pdf", b"%PDF-b"))]],
    ids=["0_archivos", "2_archivos"],
)
async def test_cantidad_de_archivos(cliente, extractor, ruta, files):
    _verificar(await _enviar(cliente, ruta, files), "cantidad_de_archivos", extractor)


@pytest.mark.parametrize("ruta", RUTAS)
@pytest.mark.parametrize("nombre, contenido", [("notas.txt", b"hola"), ("falso.pdf", b"no soy un pdf")])
async def test_no_es_pdf(cliente, extractor, ruta, nombre, contenido):
    _verificar(await _enviar(cliente, ruta, {"archivo": (nombre, contenido)}), "no_es_pdf", extractor)


@pytest.mark.parametrize("ruta", RUTAS)
async def test_mas_de_una_factura(cliente, extractor, ruta):
    pdf = pdf_factura_a([texto_comprobante(numero=1), texto_comprobante(numero=2)])
    _verificar(await _enviar(cliente, ruta, {"archivo": ("f.pdf", pdf)}), "mas_de_una_factura", extractor)


@pytest.mark.parametrize("ruta", RUTAS)
@pytest.mark.parametrize("caso", FUERA_DE_ALCANCE)
async def test_no_es_factura_a(cliente, extractor, ruta, caso):
    respuesta = await _enviar(cliente, ruta, {"archivo": ("f.pdf", FUERA_DE_ALCANCE[caso])})
    _verificar(respuesta, "no_es_factura_a", extractor)


@pytest.mark.parametrize("ruta", RUTAS)
async def test_mas_de_3_paginas(cliente, extractor, ruta):
    _verificar(await _enviar(cliente, ruta, {"archivo": ("f.pdf", pdf_n_paginas(4))}), "mas_de_3_paginas", extractor)

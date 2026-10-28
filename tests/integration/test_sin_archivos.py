"""Ni el PDF ni el JSON se escriben en disco en ningún momento (RNF-07, AC-22)."""

import os
import tempfile
import uuid
from pathlib import Path

import pytest
from fpdf import FPDF

from procfac.esquema import serializar_json
from tests.conftest import factura_de_ejemplo, pdf_factura_a, texto_comprobante
from tests.integration.conftest import login
from tests.ui.conftest import api, ingresar, nueva_app  # noqa: F401  (fixture api)

RAIZ = Path(__file__).parents[2]
EXCLUIDOS = {".venv", ".git", "__pycache__", ".pytest_cache"}
MARCA = f"MARCA-{uuid.uuid4().hex}"


def _pdf_con_marca() -> bytes:
    pdf = FPDF()
    pdf.set_compression(False)  # para que la marca quede legible en los bytes
    pdf.set_font("Helvetica", size=10)
    pdf.add_page()
    pdf.multi_cell(0, 5, texto_comprobante(extra=MARCA))
    return bytes(pdf.output())


PDF = _pdf_con_marca()
JSON = serializar_json(factura_de_ejemplo(razon_social_emisor=MARCA))


def _archivos():
    vistos = {}
    for base in (Path(tempfile.gettempdir()), RAIZ):
        for directorio, subdirs, nombres in os.walk(base):
            subdirs[:] = [d for d in subdirs if d not in EXCLUIDOS]
            for nombre in nombres:
                ruta = Path(directorio, nombre)
                try:
                    vistos[ruta] = ruta.stat().st_mtime_ns
                except OSError:
                    pass
    return vistos


def _sin_contenido_nuevo(antes):
    for ruta, mtime in _archivos().items():
        if antes.get(ruta) == mtime:
            continue
        try:
            contenido = ruta.read_bytes()
        except OSError:
            continue
        assert MARCA.encode() not in contenido, f"{ruta} contiene datos de la factura"
        assert PDF[:400] not in contenido and JSON not in contenido


@pytest.fixture
def extractor():
    from tests.conftest import ExtractorFalso

    return ExtractorFalso(factura_de_ejemplo(razon_social_emisor=MARCA))


async def test_api(cliente):
    antes = _archivos()
    headers = await login(cliente)
    files = {"archivo": ("f.pdf", PDF)}
    assert (await cliente.post("/facturas/verificar", headers=headers, files=files)).status_code == 200
    _sin_contenido_nuevo(antes)
    respuesta = await cliente.post("/facturas/extraer", headers=headers, files=files, data={"consentimiento": "true"})
    assert MARCA in respuesta.text
    _sin_contenido_nuevo(antes)
    rechazo = pdf_factura_a([texto_comprobante("factura_b", extra=MARCA)])
    await cliente.post("/facturas/verificar", headers=headers, files={"archivo": ("b.pdf", rechazo)})
    _sin_contenido_nuevo(antes)


def test_ui(api):  # noqa: F811
    from tests.ui.conftest import resultado

    api.resultado = resultado(factura_de_ejemplo(razon_social_emisor=MARCA))
    antes = _archivos()
    at = ingresar(nueva_app())
    at.file_uploader[0].upload("f.pdf", PDF, "application/pdf").run()
    _sin_contenido_nuevo(antes)
    at.button(key="aceptar").click().run()
    _sin_contenido_nuevo(antes)
    at.button(key="confirmar").click().run()
    at.get("download_button")[0].click().run()
    _sin_contenido_nuevo(antes)
    at.button(key="otra_factura").click().run()

    # Rechazo, cancelación y abandono a mitad del proceso.
    at.file_uploader[0].upload("f.pdf", PDF, "application/pdf").run()
    at.button(key="rechazar").click().run()
    at.file_uploader[0].upload("f.pdf", PDF, "application/pdf").run()
    at.button(key="aceptar").click().run()
    at.button(key="cancelar").click().run()
    abandonada = ingresar(nueva_app())
    abandonada.file_uploader[0].upload("f.pdf", PDF, "application/pdf").run()
    del abandonada
    _sin_contenido_nuevo(antes)

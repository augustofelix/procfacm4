import os
import tempfile

import httpx
import pytest
from starlette.requests import Request

from procfac.api.multipart import CantidadDeArchivos, leer_archivo_unico


def _request(files=None, data=None, contenido=None, content_type=None) -> Request:
    if contenido is None:
        armada = httpx.Request("POST", "http://test/facturas", files=files, data=data)
        contenido = armada.read()
        content_type = armada.headers["content-type"]
    enviado = False

    async def receive():
        nonlocal enviado
        if enviado:
            return {"type": "http.disconnect"}
        enviado = True
        return {"type": "http.request", "body": contenido, "more_body": False}

    headers = [(b"content-type", content_type.encode())] if content_type else []
    scope = {"type": "http", "method": "POST", "path": "/facturas", "headers": headers}
    return Request(scope, receive)


async def test_un_archivo():
    archivo = await leer_archivo_unico(
        _request(files={"archivo": ("f.pdf", b"%PDF-1.4 abc")}, data={"consentimiento": "true"})
    )
    assert archivo.nombre == "f.pdf"
    assert archivo.contenido == b"%PDF-1.4 abc"
    assert archivo.campos == {"consentimiento": "true"}


async def test_cero_archivos():
    with pytest.raises(CantidadDeArchivos):
        await leer_archivo_unico(_request(data={"consentimiento": "true"}))


async def test_dos_archivos():
    files = [("archivo", ("a.pdf", b"%PDF-a")), ("archivo", ("b.pdf", b"%PDF-b"))]
    with pytest.raises(CantidadDeArchivos):
        await leer_archivo_unico(_request(files=files))


async def test_cuerpo_que_no_es_multipart():
    with pytest.raises(CantidadDeArchivos):
        await leer_archivo_unico(_request(contenido=b"%PDF-1.4", content_type="application/pdf"))


async def test_archivo_grande_sin_temporales():
    antes = set(os.listdir(tempfile.gettempdir()))
    grande = b"%PDF-1.4\n" + os.urandom(2 * 1024 * 1024)
    archivo = await leer_archivo_unico(_request(files={"archivo": ("g.pdf", grande)}))
    assert archivo.contenido == grande
    assert set(os.listdir(tempfile.gettempdir())) - antes == set()

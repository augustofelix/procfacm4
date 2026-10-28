import json
from pathlib import Path

import jsonschema

from tests.conftest import pdf_con_copias, pdf_factura_a, texto_comprobante
from tests.integration.conftest import login

ESQUEMA = json.loads(
    (Path(__file__).parents[2] / "specs/001-procesar-factura-a/contracts/esquema-salida.schema.json")
    .read_text(encoding="utf-8")
)
PDF = pdf_factura_a([texto_comprobante()])


async def test_login(cliente):
    respuesta = await cliente.post("/auth/login", json={"usuario": "ana", "clave": "clave-ana"})
    assert respuesta.status_code == 200 and respuesta.json()["token"]


async def test_verificar_no_llama_a_la_ia(cliente, extractor):
    respuesta = await cliente.post(
        "/facturas/verificar", headers=await login(cliente), files={"archivo": ("f.pdf", PDF)}
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"admitido": True, "paginas": 1, "copias": 1}
    assert extractor.llamadas == 0


async def test_extraer_devuelve_los_campos_en_la_misma_respuesta(cliente, extractor):
    respuesta = await cliente.post(
        "/facturas/extraer", headers=await login(cliente),
        files={"archivo": ("f.pdf", PDF)}, data={"consentimiento": "true"},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    jsonschema.validate(cuerpo["factura"], ESQUEMA)
    assert cuerpo["factura"]["numero_comprobante"] == 123
    assert "items[1].precio_unitario" in cuerpo["campos_no_obtenidos"]
    assert cuerpo["comprobante_ilegible"] is False
    assert extractor.llamadas == 1


async def test_extraer_tres_copias(cliente, extractor):
    respuesta = await cliente.post(
        "/facturas/extraer", headers=await login(cliente),
        files={"archivo": ("f.pdf", pdf_con_copias())}, data={"consentimiento": "true"},
    )
    assert respuesta.status_code == 200
    assert extractor.llamadas == 1
    assert "ORIGINAL" in extractor.textos[0] and "TRIPLICADO" not in extractor.textos[0]

import asyncio

import pytest

from tests.conftest import pdf_factura_a, texto_comprobante
from tests.integration.conftest import login

PDF = pdf_factura_a([texto_comprobante()])


@pytest.mark.parametrize("ruta", ["/facturas/verificar", "/facturas/extraer"])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer inventado"}, {"Authorization": "Basic x"}])
async def test_sin_sesion_401(cliente, extractor, ruta, headers):
    respuesta = await cliente.post(
        ruta, headers=headers, files={"archivo": ("f.pdf", PDF)}, data={"consentimiento": "true"}
    )
    assert respuesta.status_code == 401
    assert respuesta.json() == {"codigo": "no_autorizado", "mensaje": "Sesión no iniciada."}
    assert extractor.llamadas == 0


@pytest.mark.parametrize("usuario, clave", [("ana", "mal"), ("nadie", "clave-ana")])
async def test_credenciales_invalidas_mismo_mensaje(cliente, usuario, clave):
    respuesta = await cliente.post("/auth/login", json={"usuario": usuario, "clave": clave})
    assert respuesta.status_code == 401
    assert respuesta.json() == {"codigo": "credenciales_invalidas", "mensaje": "Usuario o contraseña incorrectos."}


async def test_cinco_logins_a_la_vez(cliente, app):
    app.state.autenticador._usuarios.update({f"u{n}": f"clave-u{n}" for n in range(3, 6)})
    usuarios = ["ana", "beto", "u3", "u4", "u5"]
    cabeceras = await asyncio.gather(*(login(cliente, u) for u in usuarios))
    assert len({c["Authorization"] for c in cabeceras}) == 5


async def test_dos_logins_del_mismo_usuario_siguen_validos(cliente):
    primera, segunda = await login(cliente), await login(cliente)
    assert primera != segunda
    for headers in (primera, segunda):
        respuesta = await cliente.post("/facturas/verificar", headers=headers, files={"archivo": ("f.pdf", PDF)})
        assert respuesta.status_code == 200

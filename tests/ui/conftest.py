from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from procfac.esquema import ResultadoExtraccion
from procfac.ui import cliente_api
from procfac.ui.cliente_api import ErrorAPI
from tests.conftest import factura_de_ejemplo

APP = str(Path(__file__).parents[2] / "src" / "procfac" / "ui" / "app.py")
PDF = b"%PDF-1.4 contenido de prueba"


def resultado(factura=None, ilegible=False):
    from procfac import procesamiento

    factura = factura if factura is not None else factura_de_ejemplo()
    return ResultadoExtraccion(
        factura=factura,
        campos_no_obtenidos=procesamiento.campos_no_obtenidos(factura),
        comprobante_ilegible=ilegible,
    )


class APIFalsa:
    """Estado compartido por las instancias de ClienteFalso de un test."""

    def __init__(self):
        self.llamadas: list[tuple] = []
        self.resultado = resultado()
        self.error_verificar: ErrorAPI | None = None
        self.error_extraer: ErrorAPI | None = None


@pytest.fixture
def api(monkeypatch):
    estado = APIFalsa()

    class ClienteFalso:
        def __init__(self, url):
            pass

        def login(self, usuario, clave):
            estado.llamadas.append(("login", usuario))
            if clave != f"clave-{usuario}":
                raise ErrorAPI("credenciales_invalidas", "Usuario o contraseña incorrectos.", 401)
            return f"token-{usuario}-{len(estado.llamadas)}"

        def verificar(self, token, nombre, contenido):
            estado.llamadas.append(("verificar", nombre))
            if estado.error_verificar:
                raise estado.error_verificar
            return {"admitido": True, "paginas": 1, "copias": 1}

        def extraer(self, token, nombre, contenido):
            estado.llamadas.append(("extraer", nombre))
            if estado.error_extraer:
                raise estado.error_extraer
            return estado.resultado

    monkeypatch.setattr(cliente_api, "ClienteAPI", ClienteFalso)
    return estado


def nueva_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def ingresar(at: AppTest, usuario="ana", clave=None) -> AppTest:
    at.text_input(key="usuario").input(usuario)
    at.text_input(key="clave").input(clave or f"clave-{usuario}")
    at.button(key="ingresar").click().run()
    return at


def subir(at: AppTest, nombre="f.pdf", contenido=PDF) -> AppTest:
    at.file_uploader[0].upload(nombre, contenido, "application/pdf").run()
    return at


def hasta_validacion(api) -> AppTest:
    at = subir(ingresar(nueva_app()))
    at.button(key="aceptar").click().run()
    assert at.session_state["estado"] == "validacion", at.exception
    return at


def widget(lista, nombre, at: AppTest):
    return next(w for w in lista if w.key == f"{nombre}-{at.session_state['proceso']}")


def llamadas(api, tipo):
    return [l for l in api.llamadas if l[0] == tipo]

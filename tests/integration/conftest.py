import httpx
import pytest

from procfac.api.app import crear_app
from procfac.auth import Autenticador
from tests.conftest import ExtractorFalso, config_de_prueba, factura_de_ejemplo


@pytest.fixture
def extractor():
    return ExtractorFalso(factura_de_ejemplo())


@pytest.fixture
def app(extractor):
    config = config_de_prueba()
    return crear_app(config, Autenticador(config.usuarios), extractor)


@pytest.fixture
async def cliente(app):
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://api.test") as c:
        yield c


async def login(cliente, usuario="ana", clave=None) -> dict[str, str]:
    respuesta = await cliente.post("/auth/login", json={"usuario": usuario, "clave": clave or f"clave-{usuario}"})
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['token']}"}

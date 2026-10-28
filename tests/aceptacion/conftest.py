"""Aceptación con la API real de Claude y los datos copiados a mano en tests/data/.

Estructura esperada (ignorada por git; borrarla al terminar):

    tests/data/referencia/<nombre>.pdf + <nombre>.json   # Conjunto de referencia (20)
    tests/data/armados/ac36.pdf + ac36.json              # copias ORIGINAL/DUPLICADO/TRIPLICADO
    tests/data/armados/ac11.pdf + ac11.json              # campos no obtenidos
    tests/data/armados/ac13.pdf                          # comprobante no legible
    tests/data/armados/ac14/*.pdf                        # más de una factura
    tests/data/armados/ac18/*.pdf                        # no identificable como factura A
    tests/data/armados/ac33.pdf                          # 4 páginas
"""

import os
from pathlib import Path

import httpx
import pytest

DATOS = Path(__file__).parents[1] / "data"


def requerir(ruta: Path) -> Path:
    if not ruta.exists():
        pytest.skip(f"falta {ruta.relative_to(DATOS.parent)} (se copia a mano, ver tests/aceptacion/conftest.py)")
    return ruta


@pytest.fixture
def config():
    from procfac.config import ConfiguracionInvalida, cargar_configuracion

    try:
        return cargar_configuracion()
    except ConfiguracionInvalida as error:
        pytest.skip(f"configuración incompleta para la API real: {error}")


@pytest.fixture
async def cliente_real(config):
    from procfac.api.app import crear_app
    from procfac.auth import Autenticador
    from procfac.ia import ExtractorClaude

    if not os.environ.get("ANTHROPIC_API_KEY") and not config.anthropic_api_key:
        pytest.skip("falta ANTHROPIC_API_KEY")
    app = crear_app(config, Autenticador(config.usuarios), ExtractorClaude(config))
    usuario, clave = next(iter(config.usuarios.items()))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://api.test", timeout=90
    ) as cliente:
        token = (await cliente.post("/auth/login", json={"usuario": usuario, "clave": clave})).json()["token"]
        cliente.headers["Authorization"] = f"Bearer {token}"
        yield cliente


async def extraer(cliente, ruta: Path) -> httpx.Response:
    return await cliente.post(
        "/facturas/extraer", files={"archivo": (ruta.name, ruta.read_bytes())}, data={"consentimiento": "true"}
    )

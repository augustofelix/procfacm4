import os

import pytest

from procfac.config import ConfiguracionInvalida, cargar_configuracion


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    """Entorno sin variables de ProcFac y con un .env inexistente."""
    for nombre in list(os.environ):
        if nombre.startswith("PROCFAC_") or nombre == "ANTHROPIC_API_KEY":
            monkeypatch.delenv(nombre)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")
    return tmp_path / ".env"


def _usuarios(monkeypatch, cantidad):
    for n in range(1, cantidad + 1):
        monkeypatch.setenv(f"PROCFAC_USUARIO_{n}", f"usuario{n}")
        monkeypatch.setenv(f"PROCFAC_CLAVE_{n}", f"clave{n}")


def test_lee_el_ini(entorno, monkeypatch):
    _usuarios(monkeypatch, 1)
    config = cargar_configuracion(ruta_env=entorno)
    assert config.api_url == "http://127.0.0.1:8000"
    assert config.puerto == 8000
    assert config.modelo == "claude-opus-5-5"
    assert config.esfuerzo == "low"
    assert config.timeout_segundos == 60
    assert config.max_tokens == 16000
    assert config.max_paginas == 3
    assert config.min_caracteres_por_pagina == 20


@pytest.mark.parametrize("cantidad", [1, 5])
def test_acepta_de_1_a_5_usuarios(entorno, monkeypatch, cantidad):
    _usuarios(monkeypatch, cantidad)
    config = cargar_configuracion(ruta_env=entorno)
    assert config.usuarios == {f"usuario{n}": f"clave{n}" for n in range(1, cantidad + 1)}


def test_lee_el_env(monkeypatch, tmp_path, entorno):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    entorno.write_text("ANTHROPIC_API_KEY=desde-env\nPROCFAC_USUARIO_1=ana\nPROCFAC_CLAVE_1=x\n")
    config = cargar_configuracion(ruta_env=entorno)
    assert config.anthropic_api_key == "desde-env"
    assert config.usuarios == {"ana": "x"}
    for nombre in ("ANTHROPIC_API_KEY", "PROCFAC_USUARIO_1", "PROCFAC_CLAVE_1"):
        monkeypatch.delenv(nombre, raising=False)


def test_falla_sin_usuarios(entorno):
    with pytest.raises(ConfiguracionInvalida):
        cargar_configuracion(ruta_env=entorno)


def test_falla_con_mas_de_5_usuarios(entorno, monkeypatch):
    _usuarios(monkeypatch, 6)
    with pytest.raises(ConfiguracionInvalida):
        cargar_configuracion(ruta_env=entorno)


def test_falla_con_nombres_repetidos(entorno, monkeypatch):
    _usuarios(monkeypatch, 2)
    monkeypatch.setenv("PROCFAC_USUARIO_2", "usuario1")
    with pytest.raises(ConfiguracionInvalida):
        cargar_configuracion(ruta_env=entorno)


def test_falla_sin_api_key(entorno, monkeypatch):
    _usuarios(monkeypatch, 1)
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    with pytest.raises(ConfiguracionInvalida):
        cargar_configuracion(ruta_env=entorno)


def test_repr_no_muestra_secretos(entorno, monkeypatch):
    _usuarios(monkeypatch, 1)
    texto = repr(cargar_configuracion(ruta_env=entorno))
    assert "clave-de-prueba" not in texto
    assert "clave1" not in texto

"""Configuración: el .ini con lo general y el .env con los secretos (principio VI)."""

import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parents[2]
RUTA_INI = RAIZ / "config" / "procfac.ini"
RUTA_ENV = RAIZ / ".env"
MAX_USUARIOS = 5

_VARIABLE_USUARIO = re.compile(r"^PROCFAC_USUARIO_(\d+)$")


class ConfiguracionInvalida(Exception):
    pass


@dataclass(frozen=True)
class Configuracion:
    api_url: str
    host: str
    puerto: int
    modelo: str
    esfuerzo: str
    timeout_segundos: int
    max_tokens: int
    max_paginas: int
    min_caracteres_por_pagina: int
    usuarios: dict[str, str] = field(repr=False)
    anthropic_api_key: str = field(repr=False)


def leer_ini(ruta_ini: Path | str = RUTA_INI) -> configparser.ConfigParser:
    ini = configparser.ConfigParser()
    if not ini.read(ruta_ini, encoding="utf-8"):
        raise ConfiguracionInvalida(f"No se encontró el archivo de configuración {ruta_ini}.")
    return ini


def url_api(ruta_ini: Path | str = RUTA_INI) -> str:
    """URL de la API para la UI, que no necesita los secretos."""
    return leer_ini(ruta_ini).get("api", "url")


def _variables(ruta_env: Path | str) -> dict[str, str]:
    # Las variables ya definidas en el entorno tienen prioridad sobre el .env.
    variables = {k: v for k, v in dotenv_values(ruta_env).items() if v is not None}
    variables.update(os.environ)
    return variables


def _usuarios(variables: dict[str, str]) -> dict[str, str]:
    usuarios: dict[str, str] = {}
    for nombre_variable, usuario in sorted(variables.items()):
        coincidencia = _VARIABLE_USUARIO.match(nombre_variable)
        if not coincidencia or not usuario:
            continue
        clave = variables.get(f"PROCFAC_CLAVE_{coincidencia.group(1)}", "")
        if not clave:
            raise ConfiguracionInvalida(f"Falta la clave de {nombre_variable}.")
        if usuario in usuarios:
            raise ConfiguracionInvalida(f"El usuario {usuario!r} está repetido.")
        usuarios[usuario] = clave
    if not 1 <= len(usuarios) <= MAX_USUARIOS:
        raise ConfiguracionInvalida(f"Debe haber de 1 a {MAX_USUARIOS} usuarios configurados.")
    return usuarios


def cargar_configuracion(
    ruta_ini: Path | str = RUTA_INI, ruta_env: Path | str = RUTA_ENV
) -> Configuracion:
    ini = leer_ini(ruta_ini)
    variables = _variables(ruta_env)
    api_key = variables.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ConfiguracionInvalida("Falta ANTHROPIC_API_KEY.")
    return Configuracion(
        api_url=ini.get("api", "url"),
        host=ini.get("api", "host"),
        puerto=ini.getint("api", "puerto"),
        modelo=ini.get("ia", "modelo"),
        esfuerzo=ini.get("ia", "esfuerzo"),
        timeout_segundos=ini.getint("ia", "timeout_segundos"),
        max_tokens=ini.getint("ia", "max_tokens"),
        max_paginas=ini.getint("pdf", "max_paginas"),
        min_caracteres_por_pagina=ini.getint("pdf", "min_caracteres_por_pagina"),
        usuarios=_usuarios(variables),
        anthropic_api_key=api_key,
    )

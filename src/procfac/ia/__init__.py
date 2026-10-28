"""Módulo de IA: el único que conoce a la API de Claude (principio I).

El resto de la aplicación usa solo el protocolo `Extractor` y `FallaExtraccionIA`.
"""

from typing import Protocol

from procfac.esquema import Factura


class FallaExtraccionIA(Exception):
    """Error, demora mayor al tiempo de espera o respuesta inválida de la IA (RF-26)."""


class Extractor(Protocol):
    async def __call__(self, texto: str) -> Factura: ...


from procfac.ia.cliente import ExtractorClaude  # noqa: E402  (depende de FallaExtraccionIA)

__all__ = ["Extractor", "ExtractorClaude", "FallaExtraccionIA"]

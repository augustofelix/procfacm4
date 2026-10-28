"""Registro de procesos: solo metadatos, nunca contenido ni secretos (RF-33, FR-025)."""

import logging
import sys

_logger = logging.getLogger("procfac")


def configurar_logs() -> None:
    """Logs a stdout, sin archivos (RNF-07)."""
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


def registrar_proceso(
    usuario: str, operacion: str, resultado: str, motivo: str | None, duracion_ms: int
) -> None:
    """Única forma de registrar un proceso; no recibe datos de la factura."""
    _logger.info(
        "usuario=%s operacion=%s resultado=%s motivo=%s duracion_ms=%d",
        usuario, operacion, resultado, motivo or "-", duracion_ms,
    )

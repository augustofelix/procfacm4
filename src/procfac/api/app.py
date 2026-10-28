"""Aplicación FastAPI: fábrica, manejo de errores y sesión (contracts/api.md)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from procfac.api.multipart import CantidadDeArchivos
from procfac.auth import Autenticador, CredencialesInvalidas, NoAutorizado
from procfac.clasificacion import MotivoRechazo, Rechazo
from procfac.config import Configuracion
from procfac.ia import Extractor, FallaExtraccionIA
from procfac.logs import configurar_logs

MENSAJES_RECHAZO = {
    MotivoRechazo.no_es_pdf: "El archivo no es un PDF.",
    MotivoRechazo.mas_de_3_paginas: "El PDF supera las 3 páginas.",
    MotivoRechazo.no_es_factura_a: "No se pudo identificar el comprobante como factura A.",
    MotivoRechazo.mas_de_una_factura: "El PDF contiene más de una factura.",
}


def error(status: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"codigo": codigo, "mensaje": mensaje})


def usuario_actual(request: Request) -> str:
    """Usuario del token `Authorization: Bearer <token>`; se evalúa antes de leer el cuerpo."""
    esquema, _, token = request.headers.get("authorization", "").partition(" ")
    if esquema.lower() != "bearer":
        raise NoAutorizado()
    return request.app.state.autenticador.usuario_de(token.strip())


def crear_app(config: Configuracion, autenticador: Autenticador, extractor: Extractor) -> FastAPI:
    from procfac.api import rutas

    configurar_logs()
    app = FastAPI(title="ProcFac", docs_url=None, redoc_url=None)
    app.state.config = config
    app.state.autenticador = autenticador
    app.state.extractor = extractor

    @app.exception_handler(NoAutorizado)
    async def _no_autorizado(request, exc):
        return error(401, "no_autorizado", "Sesión no iniciada.")

    @app.exception_handler(CredencialesInvalidas)
    async def _credenciales(request, exc):
        return error(401, "credenciales_invalidas", "Usuario o contraseña incorrectos.")

    @app.exception_handler(CantidadDeArchivos)
    async def _cantidad(request, exc):
        return error(422, "cantidad_de_archivos", "Debe enviarse exactamente un archivo PDF.")

    @app.exception_handler(Rechazo)
    async def _rechazo(request, exc: Rechazo):
        return error(422, exc.motivo.value, MENSAJES_RECHAZO[exc.motivo])

    @app.exception_handler(FallaExtraccionIA)
    async def _falla(request, exc):
        return error(502, "falla_extraccion", "No se pudo completar la extracción.")

    app.include_router(rutas.router)
    return app


def _crear_app_real() -> FastAPI:
    from procfac.auth import Autenticador
    from procfac.config import cargar_configuracion
    from procfac.ia import ExtractorClaude

    config = cargar_configuracion()
    return crear_app(config, Autenticador(config.usuarios), ExtractorClaude(config))


def __getattr__(nombre: str):
    # `app` se crea recién cuando uvicorn la pide, para que los tests puedan importar
    # este módulo sin un .env real.
    if nombre == "app":
        globals()["app"] = _crear_app_real()
        return globals()["app"]
    raise AttributeError(nombre)

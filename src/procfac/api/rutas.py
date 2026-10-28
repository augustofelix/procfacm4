"""Endpoints de la API (contracts/api.md)."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from procfac import procesamiento
from procfac.api.app import error, usuario_actual
from procfac.api.multipart import leer_archivo_unico

router = APIRouter()


class Credenciales(BaseModel):
    usuario: str
    clave: str


def _parametros(request: Request) -> dict:
    config = request.app.state.config
    return {
        "max_paginas": config.max_paginas,
        "min_caracteres_por_pagina": config.min_caracteres_por_pagina,
    }


@router.post("/auth/login")
def login(credenciales: Credenciales, request: Request):
    token = request.app.state.autenticador.login(credenciales.usuario, credenciales.clave)
    return {"token": token}


@router.post("/facturas/verificar")
async def verificar(request: Request, usuario: str = Depends(usuario_actual)):
    archivo = await leer_archivo_unico(request)
    clasificacion = await procesamiento.verificar(archivo, usuario, **_parametros(request))
    return {"admitido": True, "paginas": clasificacion.paginas, "copias": clasificacion.copias}


@router.post("/facturas/extraer")
async def extraer(request: Request, usuario: str = Depends(usuario_actual)):
    archivo = await leer_archivo_unico(request)
    if archivo.campos.get("consentimiento") != "true":
        return error(
            422, "sin_consentimiento",
            "Falta el consentimiento para enviar la factura a la API de Claude.",
        )
    resultado = await procesamiento.extraer(
        archivo, usuario, request.app.state.extractor, **_parametros(request)
    )
    return resultado.model_dump(mode="json")

"""Orquestación: verificación previa y extracción (RF-12, RF-15, RF-17, RF-33)."""

import time

from starlette.concurrency import run_in_threadpool

from procfac.api.multipart import ArchivoRecibido
from procfac.clasificacion import Clasificacion, MotivoRechazo, Rechazo, clasificar, es_pdf
from procfac.esquema import Factura, ResultadoExtraccion
from procfac.ia import Extractor, FallaExtraccionIA
from procfac.logs import registrar_proceso
from procfac.pdf.lector import PdfIlegible, leer_pdf

_LISTAS = ("impuestos", "items")


def campos_no_obtenidos(factura: Factura) -> list[str]:
    """Rutas de los campos en null, también dentro de las listas; `[]` no se marca (AC-11)."""
    rutas = []
    for campo in Factura.model_fields:
        valor = getattr(factura, campo)
        if valor is None:
            rutas.append(campo)
        elif campo in _LISTAS:
            for indice, fila in enumerate(valor):
                rutas.extend(
                    f"{campo}[{indice}].{sub}" for sub in type(fila).model_fields if getattr(fila, sub) is None
                )
    return rutas


def comprobante_ilegible(factura: Factura) -> bool:
    """Todo en null, salvo items e impuestos, que pueden ser null o [] (RF-17, AC-13)."""
    return all(
        not getattr(factura, campo) if campo in _LISTAS else getattr(factura, campo) is None
        for campo in Factura.model_fields
    )


def _ms(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)


async def _clasificar(archivo: ArchivoRecibido, max_paginas: int, min_caracteres_por_pagina: int):
    if not es_pdf(archivo.nombre, archivo.contenido):
        raise Rechazo(MotivoRechazo.no_es_pdf)
    try:
        paginas = (await run_in_threadpool(leer_pdf, archivo.contenido)).paginas
    except PdfIlegible:
        paginas = None
    clasificacion = clasificar(
        archivo.nombre, archivo.contenido, paginas, max_paginas, min_caracteres_por_pagina
    )
    if not clasificacion.admitido:
        raise Rechazo(clasificacion.motivo)
    return clasificacion, paginas


async def verificar(
    archivo: ArchivoRecibido, usuario: str, max_paginas: int = 3, min_caracteres_por_pagina: int = 20
) -> Clasificacion:
    inicio = time.perf_counter()
    try:
        clasificacion, _ = await _clasificar(archivo, max_paginas, min_caracteres_por_pagina)
    except Rechazo as rechazo:
        registrar_proceso(usuario, "verificar", "rechazado", rechazo.motivo.value, _ms(inicio))
        raise
    registrar_proceso(usuario, "verificar", "admitido", None, _ms(inicio))
    return clasificacion


async def extraer(
    archivo: ArchivoRecibido,
    usuario: str,
    extractor: Extractor,
    max_paginas: int = 3,
    min_caracteres_por_pagina: int = 20,
) -> ResultadoExtraccion:
    """Vuelve a verificar (no confía en el cliente) y llama al extractor una sola vez."""
    inicio = time.perf_counter()
    try:
        clasificacion, paginas = await _clasificar(archivo, max_paginas, min_caracteres_por_pagina)
    except Rechazo as rechazo:
        registrar_proceso(usuario, "extraer", "rechazado", rechazo.motivo.value, _ms(inicio))
        raise
    texto = "\n".join(paginas[i] for i in clasificacion.paginas_a_enviar)
    try:
        factura = await extractor(texto)
    except FallaExtraccionIA:
        registrar_proceso(usuario, "extraer", "falla_ia", None, _ms(inicio))
        raise
    registrar_proceso(usuario, "extraer", "extraido", None, _ms(inicio))
    return ResultadoExtraccion(
        factura=factura,
        campos_no_obtenidos=campos_no_obtenidos(factura),
        comprobante_ilegible=comprobante_ilegible(factura),
    )

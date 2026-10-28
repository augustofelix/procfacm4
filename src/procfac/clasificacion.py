"""Clasificación previa al envío a la IA: funciones puras, sin E/S (research.md §R3).

Se desarrolla con tests primero (principio V): todo cambio acá va con su caso en
tests/unit/test_clasificacion.py.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum

CODIGO_FACTURA_A = 1

# "COD. 01", "Cód. 001", "Código: 01", "CODIGO N° 01"; sin cruzar saltos de línea.
_CODIGO = re.compile(
    r"\b(?:COD|C[ÓO]D|C[ÓO]DIGO)\b\.?[ \t]*(?:N[°º]?\.?[ \t]*)?:?[ \t]*(\d{1,3})\b",
    re.IGNORECASE,
)
_PUNTO_Y_NUMERO = re.compile(
    r"Punto[ \t]+de[ \t]+Venta[ \t]*:?[ \t]*(\d{1,5})[ \t]+"
    r"Comp(?:robante)?\.?[ \t]*N(?:ro|°|º|o)?\.?[ \t]*:?[ \t]*(\d{1,8})",
    re.IGNORECASE,
)
_NUMERO_CON_GUION = re.compile(r"N(?:°|º|ro\.?|o\.)[ \t]*(\d{1,5})[ \t]*-[ \t]*(\d{1,8})", re.IGNORECASE)
# Números de otros comprobantes que una factura puede citar ("Remito N° 0001-00000456").
_REFERENCIA = re.compile(r"(?:remito|recibo|orden|pedido|nota)\b[^\n]*$", re.IGNORECASE)
_LEYENDA = re.compile(r"\b(ORIGINAL|DUPLICADO|TRIPLICADO|CUADRUPLICADO)\b")


class MotivoRechazo(StrEnum):
    no_es_pdf = "no_es_pdf"
    mas_de_3_paginas = "mas_de_3_paginas"
    no_es_factura_a = "no_es_factura_a"
    mas_de_una_factura = "mas_de_una_factura"


class Rechazo(Exception):
    def __init__(self, motivo: MotivoRechazo):
        super().__init__(motivo.value)
        self.motivo = motivo


@dataclass(frozen=True)
class Clasificacion:
    admitido: bool
    motivo: MotivoRechazo | None = None
    paginas_a_enviar: list[int] = field(default_factory=list)
    copias: int = 0
    paginas: int = 0


def es_pdf(nombre: str, contenido: bytes) -> bool:
    return nombre.lower().endswith(".pdf") and contenido.startswith(b"%PDF-")


def codigo_comprobante(texto_pagina: str) -> int | None:
    coincidencia = _CODIGO.search(texto_pagina)
    return int(coincidencia.group(1)) if coincidencia else None


def es_factura_a(texto_pagina: str) -> bool:
    return codigo_comprobante(texto_pagina) == CODIGO_FACTURA_A


def identificador(texto_pagina: str) -> tuple[int, int] | None:
    """(punto de venta, número) del comprobante, sin ceros a la izquierda."""
    coincidencia = _PUNTO_Y_NUMERO.search(texto_pagina)
    if coincidencia:
        return int(coincidencia.group(1)), int(coincidencia.group(2))
    for coincidencia in _NUMERO_CON_GUION.finditer(texto_pagina):
        inicio_linea = texto_pagina.rfind("\n", 0, coincidencia.start()) + 1
        if not _REFERENCIA.search(texto_pagina[inicio_linea : coincidencia.start()]):
            return int(coincidencia.group(1)), int(coincidencia.group(2))
    return None


def _caracteres(texto: str) -> int:
    return len(re.sub(r"\s", "", texto))


def paginas_primera_copia(paginas: list[str]) -> tuple[list[int], int]:
    """Índices de las páginas de la primera copia y cantidad de copias (AC-36).

    Una copia empieza cuando cambia la leyenda ORIGINAL / DUPLICADO / TRIPLICADO; las
    páginas sin leyenda continúan la copia anterior. Sin leyendas, todo es una copia.
    """
    copias: list[list[int]] = []
    leyenda_actual = None
    for indice, texto in enumerate(paginas):
        coincidencia = _LEYENDA.search(texto)
        leyenda = coincidencia.group(1) if coincidencia else None
        if not copias or (leyenda is not None and leyenda != leyenda_actual):
            copias.append([])
            leyenda_actual = leyenda if leyenda is not None else leyenda_actual
        copias[-1].append(indice)
    return copias[0], len(copias)


def _rechazo(motivo: MotivoRechazo) -> Clasificacion:
    return Clasificacion(admitido=False, motivo=motivo)


def clasificar(
    nombre: str,
    contenido: bytes,
    paginas: list[str] | None,
    max_paginas: int = 3,
    min_caracteres_por_pagina: int = 20,
) -> Clasificacion:
    """Aplica las reglas en orden e informa el primer motivo que falla.

    `paginas` es el texto de cada página, o `None` si el PDF no se pudo abrir.
    """
    if not es_pdf(nombre, contenido):
        return _rechazo(MotivoRechazo.no_es_pdf)
    if paginas is None:
        return _rechazo(MotivoRechazo.no_es_factura_a)
    if len(paginas) > max_paginas:
        return _rechazo(MotivoRechazo.mas_de_3_paginas)
    if not paginas or any(_caracteres(p) < min_caracteres_por_pagina for p in paginas):
        return _rechazo(MotivoRechazo.no_es_factura_a)

    identificadores = [identificador(p) for p in paginas]
    for indice, texto in enumerate(paginas):
        codigo = codigo_comprobante(texto)
        inicio_de_copia = indice == 0 or identificadores[indice] is not None
        if codigo is not None and codigo != CODIGO_FACTURA_A:
            return _rechazo(MotivoRechazo.no_es_factura_a)
        if inicio_de_copia and codigo is None:
            return _rechazo(MotivoRechazo.no_es_factura_a)

    if len({i for i in identificadores if i is not None}) > 1:
        return _rechazo(MotivoRechazo.mas_de_una_factura)

    paginas_a_enviar, copias = paginas_primera_copia(paginas)
    return Clasificacion(
        admitido=True, paginas_a_enviar=paginas_a_enviar, copias=copias, paginas=len(paginas)
    )

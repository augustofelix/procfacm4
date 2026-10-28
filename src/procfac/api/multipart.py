"""Lectura del archivo único en memoria, sin UploadFile ni temporales (RNF-07, AC-19)."""

from dataclasses import dataclass, field

from python_multipart.multipart import MultipartParser, parse_options_header
from starlette.requests import Request


class CantidadDeArchivos(Exception):
    """La petición no trae exactamente un archivo."""


@dataclass(frozen=True)
class ArchivoRecibido:
    nombre: str
    contenido: bytes
    campos: dict[str, str] = field(default_factory=dict)


@dataclass
class _Parte:
    cabeceras: dict[bytes, bytes] = field(default_factory=dict)
    datos: bytearray = field(default_factory=bytearray)


async def leer_archivo_unico(request: Request) -> ArchivoRecibido:
    tipo, opciones = parse_options_header(request.headers.get("content-type"))
    if tipo != b"multipart/form-data" or b"boundary" not in opciones:
        raise CantidadDeArchivos()

    partes: list[_Parte] = []
    cabecera_actual = bytearray()
    valor_actual = bytearray()

    def on_part_begin():
        partes.append(_Parte())

    def on_header_field(datos, inicio, fin):
        cabecera_actual.extend(datos[inicio:fin])

    def on_header_value(datos, inicio, fin):
        valor_actual.extend(datos[inicio:fin])

    def on_header_end():
        partes[-1].cabeceras[bytes(cabecera_actual).lower()] = bytes(valor_actual)
        cabecera_actual.clear()
        valor_actual.clear()

    def on_part_data(datos, inicio, fin):
        partes[-1].datos.extend(datos[inicio:fin])

    parser = MultipartParser(
        opciones[b"boundary"],
        {
            "on_part_begin": on_part_begin,
            "on_header_field": on_header_field,
            "on_header_value": on_header_value,
            "on_header_end": on_header_end,
            "on_part_data": on_part_data,
        },
    )
    parser.write(await request.body())
    parser.finalize()

    archivos: list[tuple[str, bytes]] = []
    campos: dict[str, str] = {}
    for parte in partes:
        _, disposicion = parse_options_header(parte.cabeceras.get(b"content-disposition"))
        nombre_campo = disposicion.get(b"name", b"").decode("utf-8", "replace")
        if b"filename" in disposicion:
            nombre_archivo = disposicion[b"filename"].decode("utf-8", "replace")
            if nombre_archivo or parte.datos:
                archivos.append((nombre_archivo, bytes(parte.datos)))
        else:
            campos[nombre_campo] = parte.datos.decode("utf-8", "replace")

    if len(archivos) != 1:
        raise CantidadDeArchivos()
    nombre, contenido = archivos[0]
    return ArchivoRecibido(nombre=nombre, contenido=contenido, campos=campos)

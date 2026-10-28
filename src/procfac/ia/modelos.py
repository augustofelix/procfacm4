"""Modelos de transporte para la salida estructurada de la API de Claude.

Son espejo del Esquema de salida, con tipos simples y sin validadores: la normalización
y la validación las hace `procfac.esquema.Factura` al convertirlos (`a_factura`).

La salida estructurada admite como máximo 16 parámetros con tipos unión (nullable o
anyOf), así que los textos son `str` y la IA devuelve `""` cuando un dato no figura;
`a_factura` lo convierte en `null`. Solo los números y las listas son nullable.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from procfac.esquema import Factura


class _Transporte(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ImpuestoIA(_Transporte):
    descripcion_impuesto: str
    importe: float | None


class ItemIA(_Transporte):
    codigo: str
    descripcion: str
    cantidad: float | None
    precio_unitario: float | None
    subtotal_item: float | None


class FacturaIA(_Transporte):
    punto_venta: int | None
    numero_comprobante: int | None
    cuit_emisor: str
    razon_social_emisor: str
    domicilio_emisor: str
    localidad_emisor: str
    condicion_iva_emisor: str
    cuit_receptor: str
    razon_social_receptor: str
    domicilio_receptor: str
    localidad_receptor: str
    condicion_iva_receptor: str
    fecha_comprobante: str
    condicion_venta: str
    subtotal: float | None
    impuestos: list[ImpuestoIA] | None
    total: float | None
    items: list[ItemIA] | None


def _vacios_a_null(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {clave: _vacios_a_null(v) for clave, v in valor.items()}
    if isinstance(valor, list):
        return [_vacios_a_null(v) for v in valor]
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


def a_factura(factura_ia: FacturaIA) -> Factura:
    """Cualquier campo inválido hace fallar toda la respuesta (CHK023, RF-26)."""
    from procfac.ia import FallaExtraccionIA

    try:
        return Factura.model_validate(_vacios_a_null(factura_ia.model_dump()))
    except ValidationError as error:
        raise FallaExtraccionIA() from error

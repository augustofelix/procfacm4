"""Modelos de transporte para la salida estructurada de la API de Claude.

Son espejo del Esquema de salida, con tipos simples y sin validadores: la normalización
y la validación las hace `procfac.esquema.Factura` al convertirlos (`a_factura`).
"""

from pydantic import BaseModel, ConfigDict, ValidationError

from procfac.esquema import Factura


class _Transporte(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ImpuestoIA(_Transporte):
    descripcion_impuesto: str | None
    importe: float | str | None


class ItemIA(_Transporte):
    codigo: str | None
    descripcion: str | None
    cantidad: float | str | None
    precio_unitario: float | str | None
    subtotal_item: float | str | None


class FacturaIA(_Transporte):
    punto_venta: int | None
    numero_comprobante: int | None
    cuit_emisor: str | None
    razon_social_emisor: str | None
    domicilio_emisor: str | None
    localidad_emisor: str | None
    condicion_iva_emisor: str | None
    cuit_receptor: str | None
    razon_social_receptor: str | None
    domicilio_receptor: str | None
    localidad_receptor: str | None
    condicion_iva_receptor: str | None
    fecha_comprobante: str | None
    condicion_venta: str | None
    subtotal: float | str | None
    impuestos: list[ImpuestoIA] | None
    total: float | str | None
    items: list[ItemIA] | None


def a_factura(factura_ia: FacturaIA) -> Factura:
    """Cualquier campo inválido hace fallar toda la respuesta (CHK023, RF-26)."""
    from procfac.ia import FallaExtraccionIA

    try:
        return Factura.model_validate(factura_ia.model_dump())
    except ValidationError as error:
        raise FallaExtraccionIA() from error

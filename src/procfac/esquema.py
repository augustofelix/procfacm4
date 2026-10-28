"""Esquema de salida (RF-25): modelos Pydantic y serialización del JSON."""

import datetime as dt
import json
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

_CENTAVOS = Decimal("0.01")

# Los importes viajan como números JSON, no como texto (contracts/api.md).
Numero = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


def _a_decimal(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    if isinstance(valor, bool):
        raise ValueError("no es un número")
    try:
        # Desde str para que 1.005 no arrastre el error de representación binaria.
        return Decimal(str(valor))
    except InvalidOperation as error:
        raise ValueError("no es un número") from error


def _importe(valor: Any) -> Decimal | None:
    numero = _a_decimal(valor)
    return None if numero is None else numero.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def _cuit(valor: str | None) -> str | None:
    if valor is None:
        return None
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 11:
        raise ValueError("el CUIT debe tener 11 dígitos")
    return digitos


def _fecha(valor: str | None) -> str | None:
    if valor is None:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        raise ValueError("la fecha debe tener el formato AAAA-MM-DD")
    dt.date.fromisoformat(valor)
    return valor


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Impuesto(_Modelo):
    descripcion_impuesto: str | None = None
    importe: Numero | None = None

    _importe = field_validator("importe", mode="before")(staticmethod(_importe))


class Item(_Modelo):
    codigo: str | None = None
    descripcion: str | None = None
    cantidad: Numero | None = None
    precio_unitario: Numero | None = None
    subtotal_item: Numero | None = None

    _cantidad = field_validator("cantidad", mode="before")(staticmethod(_a_decimal))
    _importes = field_validator("precio_unitario", "subtotal_item", mode="before")(
        staticmethod(_importe)
    )


class Factura(_Modelo):
    """Resultado de la extracción, normalizado y validado (AC-01)."""

    punto_venta: int | None = Field(default=None, ge=0)
    numero_comprobante: int | None = Field(default=None, ge=0)
    cuit_emisor: str | None = None
    razon_social_emisor: str | None = None
    domicilio_emisor: str | None = None
    localidad_emisor: str | None = None
    condicion_iva_emisor: str | None = None
    cuit_receptor: str | None = None
    razon_social_receptor: str | None = None
    domicilio_receptor: str | None = None
    localidad_receptor: str | None = None
    condicion_iva_receptor: str | None = None
    fecha_comprobante: str | None = None
    condicion_venta: str | None = None
    subtotal: Numero | None = None
    impuestos: list[Impuesto] | None = None
    total: Numero | None = None
    items: list[Item] | None = None

    _cuits = field_validator("cuit_emisor", "cuit_receptor")(staticmethod(_cuit))
    _fecha = field_validator("fecha_comprobante")(staticmethod(_fecha))
    _importes = field_validator("subtotal", "total", mode="before")(staticmethod(_importe))


class ImpuestoEditado(_Modelo):
    descripcion_impuesto: str | None = None
    importe: Numero | None = None


class ItemEditado(_Modelo):
    codigo: str | None = None
    descripcion: str | None = None
    cantidad: Numero | None = None
    precio_unitario: Numero | None = None
    subtotal_item: Numero | None = None


class FacturaEditada(_Modelo):
    """Lo que confirma el usuario: solo restricción de tipo, sin normalizar (FR-019, RF-30)."""

    punto_venta: int | None = None
    numero_comprobante: int | None = None
    cuit_emisor: str | None = None
    razon_social_emisor: str | None = None
    domicilio_emisor: str | None = None
    localidad_emisor: str | None = None
    condicion_iva_emisor: str | None = None
    cuit_receptor: str | None = None
    razon_social_receptor: str | None = None
    domicilio_receptor: str | None = None
    localidad_receptor: str | None = None
    condicion_iva_receptor: str | None = None
    fecha_comprobante: str | None = None
    condicion_venta: str | None = None
    subtotal: Numero | None = None
    impuestos: list[ImpuestoEditado] | None = None
    total: Numero | None = None
    items: list[ItemEditado] | None = None


class ResultadoExtraccion(BaseModel):
    factura: Factura
    campos_no_obtenidos: list[str]
    comprobante_ilegible: bool


def _a_json(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {clave: _a_json(v) for clave, v in valor.items()}
    if isinstance(valor, list):
        return [_a_json(v) for v in valor]
    return valor


def serializar_json(factura: Factura | FacturaEditada) -> bytes:
    """JSON de descarga: UTF-8, indentado y con los importes como números (RF-07)."""
    datos = _a_json(factura.model_dump(mode="python"))
    return json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8")


def nombre_archivo(factura: Factura | FacturaEditada) -> str:
    if factura.punto_venta is None or factura.numero_comprobante is None:
        return "factura.json"
    return f"factura_{factura.punto_venta}_{factura.numero_comprobante}.json"

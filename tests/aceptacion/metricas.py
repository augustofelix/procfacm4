"""Métricas de precisión de RNF-03 y percentil de RNF-02 para el Conjunto de referencia."""

import math
from collections import Counter
from decimal import Decimal

CAMPOS_ESCALARES = [
    "punto_venta", "numero_comprobante",
    "cuit_emisor", "razon_social_emisor", "domicilio_emisor", "localidad_emisor", "condicion_iva_emisor",
    "cuit_receptor", "razon_social_receptor", "domicilio_receptor", "localidad_receptor",
    "condicion_iva_receptor", "fecha_comprobante", "condicion_venta", "subtotal", "total",
]
CAMPOS_ITEM = ["codigo", "descripcion", "precio_unitario", "subtotal_item"]


def _normalizar(valor):
    # 1210 y 1210.0 son el mismo importe; `null` coincide solo con `null` (SC-003).
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return Decimal(str(valor)).normalize()
    return valor


def _igual(a, b) -> bool:
    return _normalizar(a) == _normalizar(b)


def _pares(impuestos):
    if impuestos is None:
        return None
    return Counter((i.get("descripcion_impuesto"), _normalizar(i.get("importe"))) for i in impuestos)


def comparar(obtenido: dict, esperado: dict) -> dict[str, bool]:
    """Coincidencia exacta por campo (RNF-03, AC-15, AC-16, AC-20, AC-21, AC-31)."""
    resultado = {c: _igual(obtenido.get(c), esperado.get(c)) for c in CAMPOS_ESCALARES}
    # impuestos: mismos pares sin importar el orden (multiconjunto).
    resultado["impuestos"] = _pares(obtenido.get("impuestos")) == _pares(esperado.get("impuestos"))

    items_obtenidos = obtenido.get("items") or []
    items_esperados = esperado.get("items") or []
    misma_cantidad = (obtenido.get("items") is None) == (esperado.get("items") is None) and len(
        items_obtenidos
    ) == len(items_esperados)
    resultado["items_cantidad"] = misma_cantidad

    def todos(campo):
        # Si la cantidad de ítems difiere, los campos de ítem cuentan como incorrectos.
        return misma_cantidad and all(
            _igual(o.get(campo), e.get(campo)) for o, e in zip(items_obtenidos, items_esperados)
        )

    resultado["items_cantidades"] = todos("cantidad")
    for campo in CAMPOS_ITEM:
        resultado[f"items_{campo}"] = todos(campo)
    return resultado


def precision(resultados: list[dict[str, bool]]) -> dict[str, float]:
    claves = resultados[0].keys() if resultados else []
    return {c: sum(r[c] for r in resultados) / len(resultados) for c in claves}


def p95(tiempos: list[float]) -> float:
    """Rango más cercano: con 20 tiempos ordenados, el 19.º (SC-001)."""
    ordenados = sorted(tiempos)
    return ordenados[math.ceil(0.95 * len(ordenados)) - 1]

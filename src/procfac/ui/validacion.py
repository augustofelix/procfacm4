"""Pantalla de validación: campos y tablas editables (RF-13, RF-15, RF-16, RF-30)."""

import math
import time
from decimal import Decimal

import pandas as pd
import streamlit as st

from procfac.esquema import Factura, FacturaEditada
from procfac.logs import registrar_proceso

ETIQUETAS = {
    "punto_venta": "Punto de venta",
    "numero_comprobante": "Número de comprobante",
    "cuit_emisor": "CUIT del emisor",
    "razon_social_emisor": "Razón social del emisor",
    "domicilio_emisor": "Domicilio del emisor",
    "localidad_emisor": "Localidad del emisor",
    "condicion_iva_emisor": "Condición de IVA del emisor",
    "cuit_receptor": "CUIT del receptor",
    "razon_social_receptor": "Razón social del receptor",
    "domicilio_receptor": "Domicilio del receptor",
    "localidad_receptor": "Localidad del receptor",
    "condicion_iva_receptor": "Condición de IVA del receptor",
    "fecha_comprobante": "Fecha (AAAA-MM-DD)",
    "condicion_venta": "Condición de venta",
    "subtotal": "Subtotal",
    "total": "Total",
}
ENTEROS = ("punto_venta", "numero_comprobante")
IMPORTES = ("subtotal", "total")
COLUMNAS_IMPUESTOS = ["descripcion_impuesto", "importe"]
COLUMNAS_ITEMS = ["codigo", "descripcion", "cantidad", "precio_unitario", "subtotal_item"]
NUMERICAS = {"importe", "cantidad", "precio_unitario", "subtotal_item"}
NO_OBTENIDO = "No obtenido"


def _vacio(valor) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _texto(valor) -> str | None:
    if _vacio(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def _numero(valor) -> Decimal | None:
    if _vacio(valor):
        return None
    return Decimal(str(valor))


def _fila(fila: dict, columnas: list[str]) -> dict:
    return {c: _numero(fila.get(c)) if c in NUMERICAS else _texto(fila.get(c)) for c in columnas}


def _lista(tabla: list[dict], columnas: list[str], era_null: bool) -> list[dict] | None:
    filas_validas = [_fila(f, columnas) for f in tabla]
    filas_validas = [f for f in filas_validas if any(v is not None for v in f.values())]
    # Una lista que vino en null y sigue sin filas se mantiene como "no obtenida".
    if not filas_validas and era_null:
        return None
    return filas_validas


def construir_factura_editada(
    valores: dict, impuestos: list[dict], items: list[dict], impuestos_era_null: bool, items_era_null: bool
) -> FacturaEditada:
    """Arma lo confirmado con solo restricción de tipo; textos vacíos → null (research §R8)."""
    datos: dict = {}
    for campo in ETIQUETAS:
        valor = valores.get(campo)
        if campo in ENTEROS:
            datos[campo] = None if valor is None else int(valor)
        elif campo in IMPORTES:
            datos[campo] = _numero(valor)
        else:
            datos[campo] = _texto(valor)
    datos["impuestos"] = _lista(impuestos, COLUMNAS_IMPUESTOS, impuestos_era_null)
    datos["items"] = _lista(items, COLUMNAS_ITEMS, items_era_null)
    return FacturaEditada(**datos)


def filas(lista, columnas: list[str]) -> list[dict]:
    """Filas para `st.data_editor`, con los números como float."""
    resultado = []
    for fila in lista or []:
        valores = fila.model_dump()
        resultado.append(
            {c: (None if valores[c] is None else float(valores[c])) if c in NUMERICAS else valores[c] for c in columnas}
        )
    return resultado


def _celdas_no_obtenidas(campo: str, no_obtenidos: list[str]) -> list[str]:
    """"items[1].precio_unitario" → "ítem 2, precio_unitario" (en pantalla, desde 1)."""
    nombre = "ítem" if campo == "items" else "impuesto"
    celdas = []
    for ruta in no_obtenidos:
        if ruta.startswith(f"{campo}["):
            indice, subcampo = ruta[len(campo) + 1 :].split("].", 1)
            celdas.append(f"{nombre} {int(indice) + 1}, {subcampo}")
    return celdas


def mostrar_campos(
    factura: Factura | FacturaEditada, editable: bool, no_obtenidos: list[str], clave: str
) -> FacturaEditada:
    """Muestra todos los campos del Esquema de salida y devuelve lo que quedó en pantalla.

    La lista de no obtenidos refleja la extracción original y no se renumera si el
    usuario agrega o elimina filas.
    """
    deshabilitado = not editable
    valores: dict = {}
    for campo, etiqueta in ETIQUETAS.items():
        if campo in no_obtenidos:
            etiqueta = f"{etiqueta} ({NO_OBTENIDO})"
        actual = getattr(factura, campo)
        key = f"{campo}-{clave}"
        if campo in ENTEROS:
            valores[campo] = st.number_input(etiqueta, value=actual, step=1, key=key, disabled=deshabilitado)
        elif campo in IMPORTES:
            valores[campo] = st.number_input(
                etiqueta, value=None if actual is None else float(actual), step=0.01,
                key=key, disabled=deshabilitado,
            )
        else:
            valores[campo] = st.text_input(etiqueta, value=actual or "", key=key, disabled=deshabilitado)

    tablas = {}
    for campo, columnas, titulo in (
        ("impuestos", COLUMNAS_IMPUESTOS, "Impuestos"),
        ("items", COLUMNAS_ITEMS, "Ítems"),
    ):
        st.subheader(titulo + (f" ({NO_OBTENIDO})" if campo in no_obtenidos else ""))
        configuracion = {
            c: st.column_config.NumberColumn(c) if c in NUMERICAS else st.column_config.TextColumn(c)
            for c in columnas
        }
        tabla = pd.DataFrame(filas(getattr(factura, campo), columnas), columns=columnas)
        for c in columnas:
            tabla[c] = tabla[c].astype("float64" if c in NUMERICAS else "object")
        editada = st.data_editor(
            tabla,
            column_config=configuracion, column_order=columnas, num_rows="dynamic",
            key=f"{campo}-{clave}", disabled=deshabilitado, hide_index=True,
        )
        tablas[campo] = editada.to_dict("records")
        celdas = _celdas_no_obtenidas(campo, no_obtenidos)
        if celdas:
            st.caption(f"{NO_OBTENIDO}: " + "; ".join(celdas))

    return construir_factura_editada(
        valores, tablas["impuestos"], tablas["items"],
        impuestos_era_null=getattr(factura, "impuestos") is None,
        items_era_null=getattr(factura, "items") is None,
    )


def registrar_descarga(usuario: str, inicio_proceso: float) -> None:
    """Se pasa como `on_click` del botón de descarga; no lee `session_state` (FR-025)."""
    registrar_proceso(usuario, "descarga", "descargado", None, int((time.time() - inicio_proceso) * 1000))

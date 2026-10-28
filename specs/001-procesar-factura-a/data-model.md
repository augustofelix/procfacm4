# Data Model: Procesamiento de facturas A en PDF a JSON validado

**Feature**: `001-procesar-factura-a` | **Fecha**: 2026-10-27 | **Plan**: [plan.md](plan.md)

Todo vive en memoria: ninguna entidad se persiste (RNF-07). Los modelos de dominio son
Pydantic v2 en `src/procfac/esquema.py`, salvo que se indique otro módulo.

## Factura (Esquema de salida, RF-25)

| Campo | Tipo Python | Nullable | Regla |
|---|---|---|---|
| `punto_venta` | `int` | sí | ≥ 0; se serializa sin ceros a la izquierda |
| `numero_comprobante` | `int` | sí | ≥ 0; se serializa sin ceros a la izquierda |
| `cuit_emisor` | `str` | sí | se quitan los caracteres que no son dígitos; después, exactamente 11 dígitos |
| `razon_social_emisor` | `str` | sí | libre, tal como figura en el PDF |
| `domicilio_emisor` | `str` | sí | libre |
| `localidad_emisor` | `str` | sí | libre |
| `condicion_iva_emisor` | `str` | sí | libre |
| `cuit_receptor` | `str` | sí | igual que `cuit_emisor` |
| `razon_social_receptor` | `str` | sí | libre |
| `domicilio_receptor` | `str` | sí | libre |
| `localidad_receptor` | `str` | sí | libre |
| `condicion_iva_receptor` | `str` | sí | libre |
| `fecha_comprobante` | `str` | sí | `AAAA-MM-DD`, fecha válida |
| `condicion_venta` | `str` | sí | libre |
| `subtotal` | `Decimal` | sí | cuantizado a 2 decimales, `ROUND_HALF_UP` |
| `impuestos` | `list[Impuesto]` | sí | `null` = no obtenido; `[]` = el comprobante no tiene |
| `total` | `Decimal` | sí | cuantizado a 2 decimales, `ROUND_HALF_UP` |
| `items` | `list[Item]` | sí | `null` = no obtenido; `[]` = el comprobante no tiene |

Configuración del modelo: `extra="forbid"`; el orden de los campos es el de la tabla (y el
del JSON descargado).

## Impuesto

| Campo | Tipo | Nullable | Regla |
|---|---|---|---|
| `descripcion_impuesto` | `str` | sí | libre, tal como figura en el PDF |
| `importe` | `Decimal` | sí | cuantizado a 2 decimales |

Igualdad para RNF-03: dos listas de `impuestos` coinciden si tienen los mismos pares sin
importar el orden (se comparan como multiconjunto).

## Item

| Campo | Tipo | Nullable | Regla |
|---|---|---|---|
| `codigo` | `str` | sí | libre |
| `descripcion` | `str` | sí | libre |
| `cantidad` | `Decimal` | sí | **sin redondeo** |
| `precio_unitario` | `Decimal` | sí | cuantizado a 2 decimales |
| `subtotal_item` | `Decimal` | sí | cuantizado a 2 decimales |

Quedan fuera (versión 2): unidad de medida, bonificación, alícuota de IVA, subtotal con IVA.

## FacturaIA (transporte, `src/procfac/ia/modelos.py`)

Modelo espejo de `Factura` que se usa solo como `output_format` de la API de Claude: los
mismos campos, todos nullable, con importes y cantidades como `float | str | None` y sin
validadores. `procfac.ia` lo convierte en `Factura`; si la conversión falla, lanza
`FallaExtraccionIA` (RF-26). Ningún otro módulo lo importa (principio I).

## ResultadoExtraccion (respuesta de `POST /facturas/extraer`)

| Campo | Tipo | Regla |
|---|---|---|
| `factura` | `Factura` | tal como salió de la extracción, antes de editar (AC-01) |
| `campos_no_obtenidos` | `list[str]` | rutas de los campos que valen `null`: de primer nivel (`"total"`, `"items"`) y dentro de las listas (`"items[0].precio_unitario"`, `"impuestos[1].importe"`); un campo de lista vacía (`[]`) **no** se incluye (RF-15, AC-11) |
| `comprobante_ilegible` | `bool` | `true` si todos los campos son `null`, sin contar `items` e `impuestos`, que pueden ser `null` o `[]` (RF-17, AC-13) |

`campos_no_obtenidos` y `comprobante_ilegible` se calculan en `procfac.procesamiento`, no en
el módulo de IA.

## FacturaEditada (lo que confirma el usuario, `src/procfac/esquema.py`)

Mismos campos y orden que `Factura`, con `ImpuestoEditado` e `ItemEditado`, `extra="forbid"`
y **solo restricción de tipo** (RF-30, AC-37): `int | None` en `punto_venta` y
`numero_comprobante`, `Decimal | None` en importes y `cantidad`, `str | None` en los textos.
Sin validadores: no se normaliza el CUIT, no se valida la fecha, no se redondea ni se exige
`≥ 0` (FR-019, principio VII). Se crea desde la extracción con
`FacturaEditada.model_validate(factura.model_dump())`. Es lo que se serializa y descarga.

## Documento PDF (`src/procfac/pdf/lector.py`)

| Campo | Tipo | Regla |
|---|---|---|
| `paginas` | `list[str]` | texto de cada página extraído con pdfplumber, en orden |

Se construye desde `bytes` con `io.BytesIO`; nunca desde una ruta.

## Clasificacion (`src/procfac/clasificacion.py`)

| Campo | Tipo | Regla |
|---|---|---|
| `admitido` | `bool` | |
| `motivo` | `MotivoRechazo \| None` | `None` si `admitido` |
| `paginas_a_enviar` | `list[int]` | índices de las páginas de la primera copia (AC-36) |

`MotivoRechazo` (enum, ver [contracts/api.md](contracts/api.md)): `no_es_pdf`,
`mas_de_3_paginas`, `no_es_factura_a`, `mas_de_una_factura`. Orden de evaluación en
[research.md §R3](research.md).

`Rechazo(Exception)`, con el atributo `motivo: MotivoRechazo`, también vive en
`clasificacion.py`; la API lo convierte en HTTP 422.

## Usuario y sesión (`src/procfac/auth.py`)

- **Usuario**: `nombre: str`, `clave: str`, cargados desde el `.env`; de 1 a 5, sin nombres
  repetidos (RNF-04).
- **Sesión de API**: `token: str → usuario: str` en un dict en memoria; sin vencimiento.
  Varios tokens por usuario (RF-31).
- **Sesión de UI**: `st.session_state` de cada pestaña; guarda `token`, `estado`, el PDF
  (`bytes`), `resultado`, la `FacturaEditada`, `usuario` (el nombre, para el log) e
  `inicio_proceso` (para calcular la duración que se registra).

## Estados del proceso en la UI (RF-11, RF-14, RF-21, RF-23, RF-27, RF-32)

```text
login ──ok──▶ carga ──PDF admitido──▶ consentimiento ──acepta──▶ extrayendo ──ok──▶ validacion
               ▲  ▲                        │ rechaza                  │ falla IA         │ confirma
               │  └──── PDF rechazado ─────┼──────────────────────────┘                  ▼
               │        (mensaje)          ▼                                         descargable
               └──────────────────────── carga ◀── cancela (validacion) ──┐              │
               └──────────────────────── carga ◀── "Procesar otra factura" o PDF nuevo ─┘
```

- Volver a `carga` descarta de `st.session_state` el PDF, el resultado y la factura.
- En `validacion` se edita todo (RF-13, RF-16, filas de `items` e `impuestos`); la descarga
  no está disponible (AC-26).
- "Confirmar" pasa a `descargable`: los campos quedan **de solo lectura** y la descarga se
  habilita. Cada descarga entrega el mismo JSON (RF-32, CHK028, CHK029).
- Subir un PDF nuevo desde `descargable` equivale a volver a `carga` y verificar ese PDF;
  descarta el proceso anterior sin pedir confirmación (RF-32, CHK035). En `validacion` no
  hay selector de archivos, para no descartar las correcciones en curso.

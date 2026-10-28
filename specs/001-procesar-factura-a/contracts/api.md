# Contrato de la API HTTP

**Feature**: `001-procesar-factura-a` | Base URL configurable en `config/procfac.ini`
(por defecto `http://127.0.0.1:8000`). Todas las respuestas son JSON en UTF-8.

## Errores

Todo error de negocio responde con este cuerpo:

```json
{ "codigo": "<codigo>", "mensaje": "<texto para mostrar al usuario>" }
```

| HTTP | `codigo` | Cuándo | Mensaje | Requisitos |
|---|---|---|---|---|
| 401 | `no_autorizado` | falta el token o no es válido | "Sesión no iniciada." | RF-09, AC-05 |
| 401 | `credenciales_invalidas` | usuario o clave incorrectos en el login | "Usuario o contraseña incorrectos." | RF-19, AC-25 |
| 422 | `cantidad_de_archivos` | 0 o más de un archivo en la petición | "Debe enviarse exactamente un archivo PDF." | RNF-01, AC-19 |
| 422 | `no_es_pdf` | el archivo no es PDF | "El archivo no es un PDF." | RF-29, AC-35 |
| 422 | `mas_de_3_paginas` | más de 3 páginas | "El PDF supera las 3 páginas." | RF-28, AC-33 |
| 422 | `no_es_factura_a` | protegido, dañado, escaneado o de otro tipo | "No se pudo identificar el comprobante como factura A." | RF-24, AC-18 |
| 422 | `mas_de_una_factura` | más de una factura (las copias cuentan como una) | "El PDF contiene más de una factura." | RF-18, AC-14 |
| 422 | `sin_consentimiento` | `/facturas/extraer` sin `consentimiento=true` | "Falta el consentimiento para enviar la factura a la API de Claude." | RF-20 |
| 502 | `falla_extraccion` | error, demora mayor a 60 s o respuesta ilegible o fuera de esquema de la API de Claude | "No se pudo completar la extracción." | RF-26, RF-27, AC-32 |

Los errores de validación propios de FastAPI (cuerpo de login mal formado) también
responden 422 con su formato estándar.

## `POST /auth/login`

- **Body** (`application/json`): `{ "usuario": "str", "clave": "str" }`
- **200**: `{ "token": "str" }`. Cada llamada crea un token nuevo; los anteriores siguen
  válidos (RF-31).
- **401** `credenciales_invalidas`.

## `POST /facturas/verificar`

Verificación previa, **sin** llamar a la API de Claude. La UI la usa al subir el PDF, antes
de mostrar el consentimiento (AC-06, AC-14, AC-18, AC-33).

- **Headers**: `Authorization: Bearer <token>`
- **Body** (`multipart/form-data`): exactamente una parte de archivo, `archivo`.
- **200**: `{ "admitido": true, "paginas": 3, "copias": 3 }`
- **401** · **422** `cantidad_de_archivos` | `no_es_pdf` | `mas_de_3_paginas` |
  `no_es_factura_a` | `mas_de_una_factura`.

## `POST /facturas/extraer`

Única petición posterior al consentimiento (RNF-06, AC-17). Repite la verificación previa
(no confía en el cliente) y, si pasa, envía a la API de Claude el texto de la primera copia.

- **Headers**: `Authorization: Bearer <token>`
- **Body** (`multipart/form-data`): la parte de archivo `archivo` y el campo de texto
  `consentimiento` con valor `true`.
- **200**: `ResultadoExtraccion` ([data-model.md](../data-model.md)):

```json
{
  "factura": { "punto_venta": 1, "numero_comprobante": 123, "cuit_emisor": "30712345678",
               "...": "...", "impuestos": [], "items": null },
  "campos_no_obtenidos": ["items"],
  "comprobante_ilegible": false
}
```

  Los importes viajan como números JSON; la estructura de `factura` es la de
  [esquema-salida.schema.json](esquema-salida.schema.json).
- **401** · **422** (los de `/verificar` y `sin_consentimiento`) · **502**
  `falla_extraccion`.
- Sin reintentos: la API de Claude se llama una sola vez por petición, con un tiempo de
  espera de 60 s.

## Garantías transversales

- Ninguna respuesta contiene datos de otra petición: la API no guarda el PDF ni el
  resultado entre peticiones (RF-05, AC-30).
- El cuerpo se lee y se procesa en memoria; ningún endpoint escribe el PDF ni el JSON en
  disco (RNF-07, AC-22).
- Cada petición a `/facturas/*` registra una línea de log con usuario, resultado, motivo y
  duración, sin contenido (RF-33, AC-40).

# Research: Procesamiento de facturas A en PDF a JSON validado

**Feature**: `001-procesar-factura-a` | **Fecha**: 2026-10-27 | **Plan**: [plan.md](plan.md)

Resuelve las incógnitas del Technical Context y los huecos del checklist general
(`checklists/general.md`) que bloquean el diseño. Cada decisión cita lo que cubre.

## R1. Arquitectura: API FastAPI sin estado + UI Streamlit

- **Decision**: dos procesos. La API (FastAPI) expone login, verificación previa y
  extracción, y **no guarda estado del proceso entre peticiones**: solo guarda en memoria el
  mapa de tokens de sesión. La UI (Streamlit) guarda el PDF, el resultado y las ediciones en
  `st.session_state`, que es propio de cada sesión de navegador (pestaña), y genera la
  descarga en memoria.
- **Rationale**: con la API sin estado, AC-04 y AC-30 se cumplen solos (no hay datos de un
  proceso que otra sesión pueda pedir) y no hay datos de facturas abandonadas que vencer
  (CHK007). La sesión de Streamlit es por pestaña, lo que da gratis RF-31 (varias sesiones
  por usuario, cada una con su proceso). RNF-06 se cumple porque, tras el consentimiento,
  hay una sola petición (`POST /facturas/extraer`) que devuelve los campos.
- **Alternatives considered**: guardar el proceso en la API con un ID (obliga a vencer
  procesos, a controlar dueño por ID y a más superficie para fugas entre sesiones); UI sola
  sin API (no cumple AC-05, AC-19, AC-30 ni AC-35, que exigen una API con códigos HTTP).

## R2. Recepción del archivo sin tocar el disco (RNF-07, AC-22)

- **Decision**: los endpoints que reciben el PDF no usan `UploadFile`. Una dependencia
  propia lee el cuerpo completo con `await request.body()` y lo parsea en memoria con el
  parser por eventos de `python-multipart` (`MultipartParser` con callbacks que escriben en
  `bytearray`). Cuenta las partes de archivo: 0 o más de 1 → HTTP 422 (AC-19).
- **Rationale**: `UploadFile` de Starlette usa `SpooledTemporaryFile` con umbral de 1 MB y
  pasa a disco con PDF más grandes; no hay límite de tamaño en bytes (fuera de alcance), así
  que no se puede descartar. Leer el cuerpo en memoria elimina el camino a disco.
- **Alternatives considered**: subir el umbral de `SpooledTemporaryFile` parcheando
  Starlette (frágil ante actualizaciones); recibir `application/pdf` crudo en vez de
  multipart (no permite detectar "más de un archivo" de AC-19 de forma natural).
- **Nota UI**: `st.file_uploader` de Streamlit guarda los archivos en memoria
  (`UploadedFile` es un `BytesIO`); `st.download_button` sirve los bytes desde memoria.

## R3. Criterios de clasificación (RF-18, RF-24, RF-28, RF-29; CHK010 a CHK016)

Todo se resuelve localmente, sin la API de Claude, con funciones puras sobre el texto de
cada página (desarrolladas con tests primero, principio V).

- **Decision, orden de las verificaciones** (se informa el primer motivo que falla, CHK013):
  1. **Es PDF** (RF-29): el contenido empieza con `%PDF-` y el nombre termina en `.pdf`;
     si no → HTTP 422 `no_es_pdf`. Se exigen ambos (CHK015).
  2. **Se puede abrir**: si pdfplumber falla por contraseña o por archivo dañado →
     `no_es_factura_a` (AC-18 agrupa los protegidos; los dañados se tratan igual, CHK016).
  3. **Páginas** (RF-28): más de 3 → `mas_de_3_paginas`.
  4. **Texto extraíble**: alguna página con menos de 20 caracteres no blancos de texto →
     `no_es_factura_a` (PDF escaneado, aunque sea solo una página; CHK014).
  5. **Tipo factura A** (RF-24): se decide **solo por el código de comprobante**: "COD." /
     "Cód." / "Código" seguido de `0*1` como número completo, que AFIP exige impreso junto
     a la letra. Cualquier otro código (02 y 03 notas A, 04 recibo A, 51 M, 06 B, 11 C,
     19 E, 201 FCE MiPyME A, 91 remito, liquidaciones, etc.) o la falta de código →
     `no_es_factura_a` (CHK010, CHK011). No se buscan palabras como "REMITO" o "RECIBO" en
     el texto: las facturas A suelen imprimir "Remito N°" o "Recibí conforme" como datos
     propios, y esas palabras las rechazarían por error.
     El código se exige en la **primera página de cada copia** (la que tiene el
     identificador del paso 6). Una página sin identificador ni código es continuación de
     la anterior; una página con un código distinto de 01 → `no_es_factura_a`.
  6. **Una sola factura** (RF-18): en cada página se busca el identificador
     (punto de venta, número) con los patrones del formato AFIP ("Punto de Venta: 00001
     Comp. Nro: 00000123" y "N° 0001-00000123"), normalizado sin ceros a la izquierda. Si
     hay más de un identificador distinto → `mas_de_una_factura`. Las páginas sin
     identificador se consideran continuación de la anterior (CHK012).
- **Copias** (AC-36, CHK018): si hay leyendas ORIGINAL / DUPLICADO / TRIPLICADO, se agrupan
  las páginas por copia y **solo se envía a la IA el texto de la primera copia**. Así el
  encabezado, los totales y los ítems salen de una sola copia.
- **Rationale**: el código de comprobante es obligatorio en los comprobantes AFIP y
  distingue sin ambigüedad A (01) de M (51) y FCE A (201); evita heurísticas visuales sobre
  el recuadro de la letra.
- **Riesgo aceptado** (PRD, Riesgos): una factura A real sin el código impreso se rechaza.
  Las 20 facturas del Conjunto de referencia validan el criterio; si alguna falla, se
  revisa el patrón antes de cerrar la feature.
- **Alternatives considered**: detectar la letra "A" en el recuadro por posición (frágil
  según el diseño de cada emisor); delegar la clasificación a la IA (prohibido: el rechazo
  debe ser previo al envío).

## R4. Extracción con la API de Claude (RF-01 a RF-04, RF-25, RF-26, RF-27)

- **Decision**:
  - SDK `anthropic` (1.x) con `AsyncAnthropic(timeout=60.0, max_retries=0)`. El SDK
    reintenta 2 veces por defecto: `max_retries=0` es obligatorio para RF-26 (sin
    reintentos). Los 60 s se cuentan desde el envío de la petición a la API (CHK022).
  - Modelo `claude-opus-5-5` con `output_config.effort = "low"` (extracción, no
    razonamiento largo, para cumplir RNF-02). El modelo y el esfuerzo se configuran en el
    `.ini` para ajustarlos con el Conjunto de referencia.
  - Salida estructurada con `client.messages.parse(output_format=FacturaIA)`, donde
    `FacturaIA` es un modelo Pydantic "de transporte" (tipos simples, todos los campos
    nullable). No se usa `tool_choice` forzado: Opus 5.5 lo rechaza con 400.
  - Se envía **solo el texto** extraído por pdfplumber de la primera copia, no el PDF
    (principio III; minimiza lo que sale hacia un tercero, CHK002).
  - Falla (RF-26) = excepción del SDK (`APIStatusError`, `APIConnectionError`,
    `APITimeoutError`), `stop_reason` distinto de `end_turn` (incluye `refusal` y
    `max_tokens`), salida que no parsea, o que no valida el Esquema de salida al
    convertirla al modelo de dominio. **Cualquier** campo inválido cuenta como falla de toda
    la respuesta (CHK023).
  - No se activa el parámetro `fallbacks` (reenvío a otro modelo ante un rechazo): sería un
    reintento, que RF-26 prohíbe.
- **Normalización antes de validar** (CHK020, CHK021): CUIT sin caracteres que no sean
  dígitos y luego exactamente 11 dígitos; importes redondeados a 2 decimales con
  `ROUND_HALF_UP`; `cantidad` sin redondear; `fecha_comprobante` debe ser `AAAA-MM-DD`
  válida. Si después de normalizar algo no cumple → falla.
- **Rationale**: `messages.parse` con Pydantic es el camino recomendado del SDK; separar el
  modelo de transporte del de dominio evita depender de qué restricciones de JSON Schema
  acepta la salida estructurada.
- **Alternatives considered**: `claude-sonnet-5-5` (más barato y rápido; queda como
  alternativa configurable si Opus no cumple RNF-02); enviar el PDF como bloque
  `document` (manda más datos a un tercero y contradice el principio III).

## R5. Sesiones y autenticación (RF-09, RF-19, RF-31, RNF-04)

- **Decision**: `POST /auth/login` compara con `hmac.compare_digest` contra los usuarios
  del `.env` y devuelve un token opaco (`secrets.token_urlsafe(32)`). Los tokens viven en
  un dict en memoria `token → usuario`, sin vencimiento (fuera de alcance). Cada login crea
  un token nuevo y no invalida los anteriores (RF-31). Todos los endpoints de facturas
  exigen `Authorization: Bearer <token>`; sin token válido → 401 (AC-05).
- **Formato del `.env`**: pares numerados `PROCFAC_USUARIO_1` / `PROCFAC_CLAVE_1` hasta
  `_5`, más `ANTHROPIC_API_KEY`. Al arrancar se rechaza la configuración con más de 5
  usuarios o con usuarios repetidos.
- **Mensaje de login fallido** (CHK005): uno solo, "Usuario o contraseña incorrectos", sin
  indicar cuál falló. Sin límite de intentos (CHK006: no está en el PRD; no se agrega).
- **Alternatives considered**: lista `usuario:clave` en una sola variable (rompe con
  contraseñas que contienen `:` o `;`); JWT (innecesario sin vencimiento ni servicios
  externos).

## R6. Concurrencia y rendimiento (RNF-02, RNF-04)

- **Decision**: endpoints `async`; pdfplumber (CPU) se ejecuta con
  `starlette.concurrency.run_in_threadpool`; la llamada a Claude es asíncrona. Un worker de
  uvicorn alcanza para 5 procesos simultáneos (el tiempo lo domina la API de Claude). Los
  tokens viven en un solo proceso, así que **no** se usan varios workers.
- **Más de 5 procesos simultáneos** (CHK038): no se limitan (el PRD no lo pide); RNF-04 solo
  garantiza el tiempo con 5.

## R7. Logs (RF-33)

- **Decision**: módulo `logging` hacia stdout, formato clave=valor, con un único punto de
  registro (`registrar_proceso(usuario, operacion, resultado, motivo, duracion_ms)`). Nunca
  se pasa a los logs el texto, los campos ni los bytes. El access log de uvicorn queda
  activo (solo método, ruta y código).
- La API registra `verificar` y `extraer` (admitido, rechazo y motivo, falla_ia, extraido).
  La UI registra lo que la API no ve: `consentimiento` (aceptado/rechazado), `validacion`
  (cancelada) y `descarga` (descargado, con `on_click` del `download_button`). Las dos usan
  `procfac.logs`; ninguna pasa contenido (FR-025).
- **Rationale**: stdout no escribe archivos (RNF-07); un único punto de registro facilita
  el test de AC-40.

## R8. JSON de descarga (RF-07, RF-30, RF-32)

- **Decision**: la UI arma el JSON con `procfac.esquema.serializar_json(factura)` sobre la
  `FacturaEditada` (solo tipos, sin normalizar lo que ingresó el usuario; FR-019). Importes
  como números JSON (el `Decimal` se convierte a `float` solo al serializar),
  UTF-8 con `ensure_ascii=False` e indentación de 2 espacios. Nombre del archivo:
  `factura_<punto_venta>_<numero_comprobante>.json`, o `factura.json` si falta alguno
  (CHK034). Volver a descargar entrega los mismos bytes (RF-32).
- **Campos de texto vacíos** (CHK033): se descargan como `null`, igual que los numéricos
  (RF-30), para que "sin dato" tenga una sola representación.
- **Campos numéricos en la UI** (RF-30, CHK032): `st.number_input` y `NumberColumn` solo
  admiten números con punto decimal; no se aceptan la coma ni el separador de miles. Se
  admiten negativos (puede haber ítems de descuento).

## R9. Estrategia de pruebas

- **Decision**:
  - `tests/unit/`: clasificación (texto de páginas sintético), esquema y normalización,
    campos no obtenidos, autenticación, multipart en memoria, logs.
  - `tests/integration/`: API con `httpx.AsyncClient` + `ASGITransport`, y el módulo de IA
    reemplazado por un doble (la constitución prohíbe depender de la API real). PDF de
    prueba generados en memoria con `fpdf2` (dependencia de desarrollo), incluidos el
    protegido con contraseña, el escaneado (solo imagen) y el de 4 páginas.
  - `tests/aceptacion/` (marcador `referencia`): usa la API real de Claude y
    `tests/data/` (Conjunto de referencia, AC-36, PDF armados). Se omite si faltan los
    datos o la API key. Calcula las métricas de RNF-03 y los tiempos de RNF-02 y RNF-04.
  - AC-22: test de integración que recorre el flujo y compara, antes y después, los
    archivos de `tempfile.gettempdir()` y del directorio de trabajo, buscando los bytes del
    PDF o del JSON.
- **Rationale**: el principio V exige tests primero para la clasificación; los PDF
  generados al vuelo no son datos reales, así que no hace falta guardarlos.

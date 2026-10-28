---

description: "Lista de tareas para implementar el procesamiento de facturas A"
---

# Tasks: Procesamiento de facturas A en PDF a JSON validado

**Input**: Design documents from `/specs/001-procesar-factura-a/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (api.md, ui.md, esquema-salida.schema.json), quickstart.md

**Tests**: incluidos. La constitución exige tests primero para la clasificación (principio V,
no negociable) y que `pytest` pase sin la API real de Claude; los criterios de aceptación
del PRD (AC-xx) se verifican con tests. En cada fase, los tests se escriben primero y deben
**fallar** antes de implementar.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 a US4 de spec.md)
- Include exact file paths in descriptions

## Path Conventions

Un solo paquete con layout `src/`: código en `src/procfac/`, tests en `tests/`, en la raíz
del repositorio (ver plan.md → Project Structure).

## Reglas que aplican a todas las tareas

- Nada escribe el PDF ni el JSON en disco: siempre `bytes` / `io.BytesIO` (RNF-07).
- Solo `src/procfac/ia/` importa `anthropic` (principio I).
- Ningún secreto en código, `.ini`, tests ni logs (principio VI).
- Los tests no llaman a la API real de Claude, salvo los marcados `referencia`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: inicializar el proyecto y su configuración

- [ ] T001 Crear `pyproject.toml` (proyecto `procfac`, Python `>=3.13`, layout `src/`) con dependencias `fastapi`, `uvicorn[standard]`, `streamlit`, `pdfplumber`, `pydantic>=2`, `anthropic>=1`, `python-multipart`, `python-dotenv` y `httpx`; grupo `dev` con `pytest`, `pytest-asyncio`, `fpdf2` y `jsonschema`; en `[tool.pytest.ini_options]`: `testpaths=["tests"]`, `asyncio_mode="auto"`, marcador `referencia` ("usa la API real de Claude y tests/data/") y `addopts="-m 'not referencia'"`; luego correr `uv sync` para generar `uv.lock`
- [ ] T002 Crear la estructura de carpetas del plan con `__init__.py` vacíos: `src/procfac/`, `src/procfac/pdf/`, `src/procfac/ia/`, `src/procfac/api/`, `src/procfac/ui/`, `tests/unit/`, `tests/integration/`, `tests/ui/`, `tests/aceptacion/`
- [ ] T003 [P] Crear `config/procfac.ini` con la sección `[api]` (`url = http://127.0.0.1:8000`, `host = 127.0.0.1`, `puerto = 8000`), `[ia]` (`modelo = claude-opus-5-5`, `esfuerzo = low`, `timeout_segundos = 60`, `max_tokens = 16000`) y `[pdf]` (`max_paginas = 3`, `min_caracteres_por_pagina = 20`); sin secretos
- [ ] T004 [P] Crear `.env.example` con `ANTHROPIC_API_KEY=`, `PROCFAC_USUARIO_1=`/`PROCFAC_CLAVE_1=` hasta `_5`, sin valores reales, y agregar la línea `!.env.example` en `.gitignore` después de `.env.*` para que no se ignore
- [ ] T005 [P] Crear `Makefile` con el objetivo `dev` que levanta en paralelo `uv run uvicorn procfac.api.app:app --host 127.0.0.1 --port 8000` y `uv run streamlit run src/procfac/ui/app.py --server.port 8501` (y los detiene juntos con Ctrl+C), y el objetivo `test` que corre `uv run pytest`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: configuración, esquema, lectura del PDF, clasificación, multipart en memoria,
autenticación y la interfaz del módulo de IA, que usan todas las historias

**⚠️ CRITICAL**: ninguna historia puede empezar hasta terminar esta fase. La clasificación
queda acá porque el MVP ya no puede enviar a la IA documentos fuera de alcance (principio II).

### Tests de la fase 2 (escribir primero; deben fallar) ⚠️

- [ ] T006 [P] Escribir `tests/unit/test_config.py`: lee `config/procfac.ini` y un `.env` temporal creado con `monkeypatch.setenv`; acepta de 1 a 5 pares `PROCFAC_USUARIO_n`/`PROCFAC_CLAVE_n`; falla con `ConfiguracionInvalida` si hay 0 usuarios, más de 5, nombres repetidos o falta `ANTHROPIC_API_KEY`
- [ ] T007 [P] Escribir `tests/unit/test_esquema.py`: `Factura` con `extra="forbid"` y los 18 campos en el orden de data-model.md, todos nullable; CUIT: "se quitan los caracteres que no son dígitos; después, exactamente 11 dígitos" (`"30-71234567-8"` → `"30712345678"`, `"123"` falla); `fecha_comprobante` "`AAAA-MM-DD`, fecha válida" (`"2026-02-30"` falla); importes "cuantizado a 2 decimales, `ROUND_HALF_UP`" (`1.005` → `1.01`); `cantidad` "**sin redondeo**" (`0.3333` queda igual); `punto_venta` y `numero_comprobante` enteros ≥ 0; `impuestos` e `items` distinguen `None` de `[]`
- [ ] T008 [P] Escribir `tests/unit/test_serializacion.py` para `serializar_json(factura: Factura | FacturaEditada) -> bytes`: UTF-8 con `ensure_ascii=False`, indentación 2, claves en el orden del esquema, importes como números JSON (no strings), `None` → `null`, mismo resultado en dos llamadas; y `nombre_archivo(factura)` → `factura_<punto_venta>_<numero_comprobante>.json` o `factura.json` si falta alguno; además valida contra `specs/001-procesar-factura-a/contracts/esquema-salida.schema.json` la salida de una `Factura` (resultado de la extracción, AC-01); con una `FacturaEditada` con `cuit_emisor="3071234567"`, `fecha_comprobante="2026-02-30"`, `punto_venta=-1` y `total=Decimal("1.005")`, el JSON contiene esos valores tal cual y solo se verifican los tipos JSON de cada campo, no el esquema (FR-019, principio VII)
- [ ] T009 [P] Escribir `tests/conftest.py` con fábricas de PDF en memoria con `fpdf2` (devuelven `bytes`, nunca archivos): `pdf_factura_a(paginas_texto)`, `pdf_con_copias(texto, copias=("ORIGINAL","DUPLICADO","TRIPLICADO"))`, `pdf_n_paginas(n)`, `pdf_protegido()` (con contraseña de usuario), `pdf_escaneado()` (una página solo con imagen) y `pdf_danado()` (`b"%PDF-1.4\n"` truncado); y textos de ejemplo de facturas A, B, C, E, M, FCE MiPyME A, nota de crédito, nota de débito, recibo, remito, liquidación y tipo X con el formato AFIP ("COD. 01", "Punto de Venta: 00001 Comp. Nro: 00000123"), cada uno con su código de comprobante (el tipo X, sin código)
- [ ] T010 [P] Escribir `tests/unit/test_lector_pdf.py`: `leer_pdf(bytes) -> DocumentoPDF` devuelve el texto de cada página en orden; lanza `PdfIlegible` con PDF protegido o dañado; nunca recibe ni crea rutas (verificar con `monkeypatch` de `builtins.open` que no se abre ningún archivo para escribir)
- [ ] T011 [P] Escribir `tests/unit/test_clasificacion.py` (principio V) para `clasificar(nombre, contenido: bytes, paginas: list[str] | None) -> Clasificacion` siguiendo el orden de research.md §R3: (1) sin `%PDF-` o sin extensión `.pdf` → `no_es_pdf`; (2) ilegible → `no_es_factura_a`; (3) más de 3 páginas → `mas_de_3_paginas` (3 se admite); (4) alguna página con menos de 20 caracteres no blancos → `no_es_factura_a`; (5) solo por código de comprobante: acepta "COD. 01", "Cód. 001", "Código: 01"; sin código o con 02, 03, 04, 06, 11, 19, 51, 91, 201 → `no_es_factura_a`, un caso por cada comprobante de AC-18; una factura A con "Remito N° 0001-00000456" y "Recibí conforme" en el texto → admitida; el código se exige en la primera página de cada copia: una factura de 2 páginas cuya segunda página no repite el encabezado ni el código → admitida, y una de 2 páginas con "COD. 01" en la primera y "COD. 03" en la segunda → `no_es_factura_a`; (6) dos identificadores (punto de venta, número) distintos → `mas_de_una_factura`, con identificadores normalizados sin ceros a la izquierda ("00001-00000123" y "1-123" son el mismo) y páginas sin identificador como continuación; copias ORIGINAL/DUPLICADO/TRIPLICADO del mismo identificador → admitido con `paginas_a_enviar=[0]` (AC-36); cuando fallan dos reglas, se informa la primera del orden
- [ ] T012 [P] Escribir `tests/unit/test_multipart.py` para `leer_archivo_unico(request)`: con 1 archivo devuelve `(nombre, bytes, campos)`; con 0 o 2 archivos lanza `CantidadDeArchivos`; un PDF de 2 MB se lee sin crear archivos en `tempfile.gettempdir()`; los campos de texto (`consentimiento`) se devuelven en `campos`
- [ ] T013 [P] Escribir `tests/unit/test_auth.py`: `login(usuario, clave)` devuelve un token nuevo por llamada (dos logins del mismo usuario dan dos tokens válidos a la vez, RF-31); credenciales incorrectas lanzan `CredencialesInvalidas` sin indicar cuál falló; `usuario_de(token)` devuelve el usuario o lanza `NoAutorizado`
- [ ] T014 [P] Escribir `tests/unit/test_aislamiento_ia.py`: recorre con `ast` todos los `.py` de `src/procfac/` y falla si alguno fuera de `src/procfac/ia/` importa `anthropic` (principio I); y que `src/procfac/ui/` no importe `procfac.ia`, `procfac.clasificacion` ni `procfac.procesamiento`

### Implementación de la fase 2

- [ ] T015 Implementar `src/procfac/config.py`: `Configuracion` (dataclass congelada) con `api_url`, `host`, `puerto`, `modelo`, `esfuerzo`, `timeout_segundos`, `max_tokens`, `max_paginas`, `min_caracteres_por_pagina`, `usuarios: dict[str, str]` y `anthropic_api_key`; `cargar_configuracion(ruta_ini="config/procfac.ini")` con `configparser` y `python-dotenv` (`load_dotenv` sin sobrescribir variables ya definidas); excepción `ConfiguracionInvalida`; nunca registrar en logs ni en `repr` la API key ni las claves (`field(repr=False)`) (hace pasar T006)
- [ ] T016 [P] Implementar `src/procfac/logs.py`: `configurar_logs()` con `logging.StreamHandler(sys.stdout)` (sin `FileHandler`) y `registrar_proceso(usuario: str, operacion: str, resultado: str, motivo: str | None, duracion_ms: int)` que escribe una sola línea `clave=valor`; no acepta otros argumentos, para que no se pueda pasar contenido (RF-33)
- [ ] T017 [P] Implementar `src/procfac/esquema.py`: modelos Pydantic v2 `Impuesto`, `Item` y `Factura` con las reglas de data-model.md (validadores `field_validator` para CUIT, fecha, cuantización `ROUND_HALF_UP` a 2 decimales y `cantidad` sin redondeo; `model_config = ConfigDict(extra="forbid")`); `ResultadoExtraccion` (`factura`, `campos_no_obtenidos: list[str]`, `comprobante_ilegible: bool`); `FacturaEditada`, `ImpuestoEditado` e `ItemEditado` (mismos campos y orden, solo tipos, sin `field_validator`, data-model.md → FacturaEditada); `serializar_json(factura: Factura | FacturaEditada) -> bytes` (convierte `Decimal` a `float` solo al serializar) y `nombre_archivo(factura) -> str` (hace pasar T007 y T008)
- [ ] T018 [P] Implementar `src/procfac/pdf/lector.py`: `DocumentoPDF` (`paginas: list[str]`) y `leer_pdf(contenido: bytes) -> DocumentoPDF` con `pdfplumber.open(io.BytesIO(contenido))` y `page.extract_text(layout=True)`; convierte las excepciones de pdfminer (contraseña, archivo dañado) en `PdfIlegible` (hace pasar T010)
- [ ] T019 Implementar `src/procfac/clasificacion.py` como funciones puras sin E/S: `MotivoRechazo` (enum `no_es_pdf`, `mas_de_3_paginas`, `no_es_factura_a`, `mas_de_una_factura`), la excepción `Rechazo(motivo: MotivoRechazo)`, `Clasificacion` (`admitido`, `motivo`, `paginas_a_enviar`, `copias`), `es_pdf(nombre, contenido)`, `es_factura_a(texto_pagina)`, `identificador(texto_pagina) -> tuple[int, int] | None`, `paginas_primera_copia(paginas)` y `clasificar(...)`, con las expresiones regulares y el orden de research.md §R3; `max_paginas` y `min_caracteres_por_pagina` como parámetros con valores por defecto 3 y 20 (hace pasar T011; depende de T018)
- [ ] T020 [P] Implementar `src/procfac/api/multipart.py`: `leer_archivo_unico(request) -> ArchivoRecibido(nombre, contenido, campos)` con `await request.body()` y `python_multipart.multipart.MultipartParser` con callbacks que acumulan en `bytearray` (nunca `UploadFile` ni `request.form()`); exige `Content-Type` `multipart/form-data`; lanza `CantidadDeArchivos` si hay 0 o más de 1 parte con `filename` (hace pasar T012)
- [ ] T021 [P] Implementar `src/procfac/auth.py`: `Autenticador(usuarios)` con `login()` (`hmac.compare_digest` sobre usuario y clave), tokens `secrets.token_urlsafe(32)` en un `dict` protegido con `threading.Lock`, `usuario_de(token)`, y excepciones `CredencialesInvalidas` y `NoAutorizado`; sin vencimiento ni cierre de sesión (hace pasar T013)
- [ ] T022 Implementar la interfaz del módulo de IA en `src/procfac/ia/__init__.py`: `class FallaExtraccionIA(Exception)` y el protocolo `Extractor` (`async def __call__(self, texto: str) -> Factura`), sin implementación real todavía; y en `tests/conftest.py` el doble `ExtractorFalso(resultado: Factura | Exception)` que registra cuántas veces se lo llamó y con qué texto (depende de T017)
- [ ] T023 Implementar `src/procfac/api/app.py`: `crear_app(config, autenticador, extractor) -> FastAPI` (fábrica para inyectar dobles en los tests) y `app = crear_app(...)` con la configuración real; manejadores de excepciones que responden `{"codigo", "mensaje"}` con los códigos y mensajes de la tabla de contracts/api.md (`CantidadDeArchivos` → 422 `cantidad_de_archivos`, `NoAutorizado` → 401 `no_autorizado`, `CredencialesInvalidas` → 401 `credenciales_invalidas`, `procfac.clasificacion.Rechazo` → 422 con el motivo, `FallaExtraccionIA` → 502 `falla_extraccion`); dependencia `usuario_actual` que lee `Authorization: Bearer <token>`; `configurar_logs()` al iniciar (depende de T015, T016, T019, T020, T021, T022)

**Checkpoint**: `uv run pytest tests/unit` pasa; la base está lista.

---

## Phase 3: User Story 1 - Convertir una factura A en un JSON validado (Priority: P1) 🎯 MVP

**Goal**: iniciar sesión, subir una factura A, aceptar el consentimiento, revisar, corregir
o completar los campos (incluidas filas de `items` e `impuestos`), confirmar y descargar el
JSON; volver a descargarlo y procesar otra factura.

**Independent Test**: con un usuario válido y un PDF de factura A generado en los tests (IA
simulada), el flujo completo por API y por UI produce un JSON con la estructura del Esquema
de salida y los valores confirmados (AC-01, AC-06, AC-08, AC-09, AC-11, AC-12, AC-13, AC-17,
AC-23, AC-24, AC-26, AC-36, AC-37, AC-39).

### Tests for User Story 1 (escribir primero; deben fallar) ⚠️

- [ ] T024 [P] [US1] Escribir `tests/unit/test_procesamiento.py`: `campos_no_obtenidos(factura)` devuelve las rutas de los campos en `None`, de primer nivel y dentro de las listas (un ítem con `precio_unitario=None` → `"items[0].precio_unitario"`), y no incluye los de lista vacía (AC-11); `comprobante_ilegible(factura)` es `True` si todos los campos son `None` sin contar `items` e `impuestos`, que pueden ser `None` o `[]` (AC-13); `extraer()` envía al extractor solo el texto de `paginas_a_enviar` (con un PDF de 3 copias, el texto de la página 0, AC-36); `verificar()` y `extraer()` llaman a `registrar_proceso` con usuario, operación, resultado y duración, y sin texto
- [ ] T025 [P] [US1] Escribir `tests/unit/test_ia.py` con un cliente `AsyncAnthropic` simulado (sin red): `ExtractorClaude(config)` crea el cliente con `timeout=60.0` y `max_retries=0`; llama a `messages.parse` una sola vez con el modelo, el esfuerzo (`output_config={"effort": ...}`) y `output_format=FacturaIA` del `.ini`; envía solo el texto recibido; convierte `FacturaIA` en `Factura` con la normalización del esquema
- [ ] T026 [P] [US1] Escribir `tests/integration/test_flujo_api.py` con `httpx.AsyncClient(transport=ASGITransport(app=crear_app(..., extractor=ExtractorFalso(...))))`: login 200 con token (AC-24); `POST /facturas/verificar` con una factura A → 200 `{"admitido": true, "paginas": 1, "copias": 1}` sin llamar al extractor (AC-06); `POST /facturas/extraer` con `consentimiento=true` → 200 con `factura`, `campos_no_obtenidos` y `comprobante_ilegible` que validan contra `contracts/esquema-salida.schema.json` (AC-01, AC-08, AC-17); el extractor se llamó exactamente una vez (RNF-06); con el PDF de 3 copias, 200 y el texto enviado es el de una sola copia (AC-36)
- [ ] T027 [P] [US1] Escribir `tests/ui/test_flujo_ui.py` con `streamlit.testing.v1.AppTest.from_file("src/procfac/ui/app.py")` y `cliente_api` simulado con `monkeypatch`: login correcto → pantalla de carga (AC-24); PDF admitido → advertencia con "Aceptar y procesar" y "Rechazar" y ninguna llamada a `extraer` (AC-06); aceptar → validación con todos los campos del esquema (AC-08) y sin botón de descarga (AC-26); los campos no obtenidos tienen la etiqueta "No obtenido", y las celdas no obtenidas de `items` e `impuestos` aparecen listadas debajo de su tabla (AC-11); con `comprobante_ilegible` se muestra exactamente el mensaje de comprobante no legible de contracts/ui.md y los campos vacíos (AC-13); editar un campo, agregar una fila de `items` y quitar una de `impuestos`, confirmar → los campos quedan de solo lectura y se muestra el botón "Descargar JSON"; `serializar_json(session_state["factura"])` contiene esos valores (AppTest no permite hacer clic en un `download_button`); escribir un CUIT de 10 dígitos y la fecha "2026-02-30" no da error y el JSON descargado los contiene tal cual (FR-019) (AC-09, AC-12, AC-23); los campos numéricos son `number_input` / `NumberColumn` y un campo numérico vacío se descarga como `null` (AC-37); un campo de texto vaciado también se descarga como `null` (research.md §R8); la descarga no modifica `session_state`, así que dos descargas dan los mismos bytes y "Procesar otra factura" vuelve a la carga sin datos en `session_state` (AC-39); en `descargable`, subir otro PDF borra `resultado` y `factura` de `session_state` y muestra el consentimiento del PDF nuevo (RF-32); en `validacion` no hay selector de archivos

### Implementation for User Story 1

- [ ] T028 [P] [US1] Implementar `src/procfac/ia/modelos.py`: `FacturaIA`, `ImpuestoIA` e `ItemIA` (Pydantic, mismos campos que el esquema, todos nullable, importes y cantidades como `float | str | None`, sin validadores) y `a_factura(f: FacturaIA) -> Factura` que lanza `FallaExtraccionIA` si `Factura.model_validate` falla
- [ ] T029 [P] [US1] Implementar `src/procfac/ia/prompt.py`: `INSTRUCCIONES` (texto del sistema en español) que pide extraer solo lo que figura en el texto, copiar textos y descripciones de impuestos tal como figuran, CUIT de 11 dígitos, fecha `AAAA-MM-DD`, importes con punto decimal, `null` para lo que no figura, `[]` si el comprobante no tiene ítems o impuestos, y los ítems de una sola copia en el orden del comprobante
- [ ] T030 [US1] Implementar `ExtractorClaude` en `src/procfac/ia/cliente.py` y exportarlo desde `src/procfac/ia/__init__.py`: `AsyncAnthropic(api_key=config.anthropic_api_key, timeout=float(config.timeout_segundos), max_retries=0)`; `__call__(texto)` llama a `client.messages.parse(model=config.modelo, max_tokens=config.max_tokens, system=INSTRUCCIONES, output_config={"effort": config.esfuerzo}, output_format=FacturaIA, messages=[{"role": "user", "content": texto}])` una sola vez y devuelve `a_factura(respuesta.parsed_output)`; sin `fallbacks` (hace pasar T025; depende de T028, T029)
- [ ] T031 [US1] Implementar `src/procfac/procesamiento.py`: `campos_no_obtenidos()`, `comprobante_ilegible()`, `async verificar(archivo, usuario)` (antes de `leer_pdf`, verifica `es_pdf(nombre, contenido)` y lanza `clasificacion.Rechazo(no_es_pdf)` si no cumple; después lee el PDF con `run_in_threadpool(leer_pdf, ...)`, clasifica y lanza `clasificacion.Rechazo(motivo)` si no se admite) y `async extraer(archivo, usuario, extractor) -> ResultadoExtraccion` (vuelve a verificar, une el texto de `paginas_a_enviar` y llama al extractor una vez); ambas registran con `registrar_proceso` (hace pasar T024; depende de T019, T022)
- [ ] T032 [US1] Implementar `src/procfac/api/rutas.py` y registrarlo en `crear_app`: `POST /auth/login` (body `{usuario, clave}` → `{token}`), `POST /facturas/verificar` y `POST /facturas/extraer` (este exige el campo `consentimiento == "true"`; si falta → 422 `sin_consentimiento`), los dos con `usuario_actual` y `leer_archivo_unico`; respuestas según contracts/api.md (hace pasar T026; depende de T023, T031)
- [ ] T033 [P] [US1] Implementar `src/procfac/ui/cliente_api.py`: `ClienteAPI(url)` con `httpx.Client(timeout=75.0)` y los métodos `login(usuario, clave) -> str`, `verificar(token, nombre, contenido: bytes) -> dict` y `extraer(token, nombre, contenido) -> ResultadoExtraccion`; envía el archivo desde `bytes` en memoria; convierte las respuestas de error `{codigo, mensaje}` en `ErrorAPI(codigo, mensaje, status)`
- [ ] T034 [US1] Implementar `src/procfac/ui/validacion.py`: `mostrar_campos(factura, editable: bool, no_obtenidos: list[str]) -> FacturaEditada` con `st.text_input` para los textos, `st.number_input(value=None, step=1)` para `punto_venta` y `numero_comprobante`, `st.number_input(value=None)` para `subtotal` y `total`, y `st.data_editor(num_rows="dynamic")` con `NumberColumn` para `importe`, `cantidad`, `precio_unitario` y `subtotal_item`; etiqueta "No obtenido" en los campos de primer nivel de `no_obtenidos` y, debajo de cada tabla, la lista de sus celdas no obtenidas con la etiqueta "No obtenido" (`st.data_editor` no permite etiquetar celdas sueltas); esa lista refleja la extracción original y no se renumera si el usuario agrega o elimina filas; los vacíos se devuelven como `None`; con `editable=False`, todo deshabilitado; nunca construye un `Factura` con lo que ingresa el usuario (RF-13, RF-15, RF-16, RF-30, FR-019)
- [ ] T035 [US1] Implementar `src/procfac/ui/app.py`: máquina de estados en `st.session_state["estado"]` con `login`, `carga`, `consentimiento`, `extrayendo`, `validacion` y `descargable` (data-model.md → Estados); pantallas y textos de contracts/ui.md; `st.file_uploader(type=["pdf"], accept_multiple_files=False)`; consentimiento con la advertencia de contracts/ui.md; `st.spinner("Extrayendo los datos de la factura…")`; en `validacion`, `st.warning` con el mensaje de comprobante no legible de contracts/ui.md si `comprobante_ilegible` y botón "Confirmar"; en `descargable`, `st.download_button("Descargar JSON", data=serializar_json(factura), file_name=nombre_archivo(factura), mime="application/json")` con la `FacturaEditada` de `session_state["factura"]` y "Procesar otra factura", que llama a `volver_a_carga()` (borra `pdf`, `resultado` y `factura` de `session_state` y pasa a `carga`); en `descargable`, un `st.file_uploader(type=["pdf"], accept_multiple_files=False)` que al recibir un PDF llama a `volver_a_carga()` y sigue con la verificación del PDF nuevo (RF-32); llama a `configurar_logs()` al iniciar, guarda `usuario` al hacer login e `inicio_proceso` al subir el PDF, y llama a `registrar_proceso` con `operacion="consentimiento"` al aceptar y con `operacion="descarga"` mediante `registrar_descarga(usuario, inicio_proceso)`, que se pasa al `download_button` como `on_click=registrar_descarga, args=(usuario, inicio_proceso)` y no lee `session_state` (FR-025) (hace pasar T027; depende de T016, T033, T034)

**Checkpoint**: la historia 1 funciona sola: `uv run pytest tests/unit tests/integration/test_flujo_api.py tests/ui/test_flujo_ui.py` pasa y `make dev` permite el flujo completo con la API real.

---

## Phase 4: User Story 2 - Rechazar documentos fuera de alcance sin enviarlos a la IA (Priority: P2)

**Goal**: todo documento fuera de alcance se rechaza antes de llamar a la IA, con el motivo,
y la UI vuelve a la pantalla de carga sin JSON.

**Independent Test**: los PDF de prueba (más de una factura, cada comprobante de AC-18,
protegido, escaneado, de 4 páginas) y los archivos que no son PDF se rechazan con el código
y el mensaje de contracts/api.md, y el extractor falso nunca se llama (AC-02, AC-14, AC-18,
AC-19, AC-33, AC-34, AC-35).

### Tests for User Story 2 (escribir primero; deben fallar) ⚠️

- [ ] T036 [P] [US2] Escribir `tests/integration/test_rechazos.py` (principio V) parametrizado sobre `/facturas/verificar` y `/facturas/extraer` (con `consentimiento=true`): 0 archivos y 2 archivos → 422 `cantidad_de_archivos` (AC-19); un `.txt` y un `.pdf` sin `%PDF-` → 422 `no_es_pdf` (AC-35); dos facturas distintas → 422 `mas_de_una_factura` con "El PDF contiene más de una factura." (AC-14); nota de crédito, nota de débito, recibo, remito, liquidación, factura M, FCE MiPyME A, B, C, E, tipo X, protegido, escaneado, dañado y de tipo no identificable → 422 `no_es_factura_a` (AC-18); 4 páginas → 422 `mas_de_3_paginas` (AC-33); en todos los casos, `ExtractorFalso.llamadas == 0`
- [ ] T037 [P] [US2] Escribir `tests/ui/test_rechazos_ui.py` con `AppTest`: el selector acepta solo `pdf` y un archivo (AC-02, AC-34); con `verificar` simulado que lanza `ErrorAPI` de cada motivo, la UI muestra el `mensaje` de la API, queda en `carga`, no muestra el consentimiento ni llama a `extraer` (AC-14, AC-18, AC-33)

### Implementation for User Story 2

- [ ] T038 [US2] Revisar en `src/procfac/api/app.py` que los mensajes por `MotivoRechazo` armados en T023 sean los textos exactos de contracts/api.md y verificar que `/facturas/extraer` clasifique **antes** de construir el texto para la IA (hace pasar T036)
- [ ] T039 [US2] Completar en `src/procfac/ui/app.py` el manejo de `ErrorAPI` al verificar: guardar el `mensaje` en `session_state["aviso"]`, descartar el PDF, volver a `carga` y mostrar el aviso con `st.error` (hace pasar T037)

**Checkpoint**: las historias 1 y 2 funcionan; ningún rechazo llega a la IA.

---

## Phase 5: User Story 3 - Cancelar el proceso de forma segura (Priority: P2)

**Goal**: rechazar el consentimiento, cancelar la validación o una falla de la IA cancelan
el proceso sin entregar JSON y sin reintentar.

**Independent Test**: con el extractor falso configurado para fallar de cada forma (error,
demora, respuesta fuera de esquema) y con las acciones de cancelación en la UI, siempre se
vuelve a la carga sin JSON y el extractor se llama a lo sumo una vez (AC-07, AC-10, AC-32).

### Tests for User Story 3 (escribir primero; deben fallar) ⚠️

- [ ] T040 [P] [US3] Ampliar `tests/unit/test_ia.py`: con el cliente simulado que lanza `anthropic.APIStatusError`, `anthropic.APIConnectionError` y `anthropic.APITimeoutError`, que devuelve `stop_reason="refusal"` o `"max_tokens"`, `parsed_output=None`, o un CUIT de 9 dígitos → `ExtractorClaude` lanza `FallaExtraccionIA`, y `messages.parse` se llamó exactamente una vez en cada caso (RF-26, sin reintentos)
- [ ] T041 [P] [US3] Escribir `tests/integration/test_fallas_ia.py`: con `ExtractorFalso(FallaExtraccionIA())`, `/facturas/extraer` → 502 `{"codigo": "falla_extraccion", "mensaje": "No se pudo completar la extracción."}` (AC-32); sin el campo `consentimiento` → 422 `sin_consentimiento` y el extractor no se llama (RF-20); con 0 archivos y sin `consentimiento` → 422 `cantidad_de_archivos` (contracts/api.md → Orden de las verificaciones)
- [ ] T042 [P] [US3] Escribir `tests/ui/test_cancelaciones_ui.py` con `AppTest`: "Rechazar" en el consentimiento → `carga`, sin llamadas a `extraer` y sin datos en `session_state` (AC-07); "Cancelar" en la validación → `carga` sin descarga disponible (AC-10); `extraer` que lanza `ErrorAPI("falla_extraccion", ...)` → `carga` con "No se pudo completar la extracción." (AC-32)

### Implementation for User Story 3

- [ ] T043 [US3] Completar `ExtractorClaude.__call__` en `src/procfac/ia/cliente.py`: capturar `anthropic.APIStatusError`, `anthropic.APIConnectionError` (incluye `APITimeoutError`) y `pydantic.ValidationError`, y verificar `stop_reason == "end_turn"` y `parsed_output is not None`; en cualquier otro caso lanzar `FallaExtraccionIA` sin volver a llamar (hace pasar T040)
- [ ] T044 [US3] Completar `src/procfac/procesamiento.py` y `src/procfac/api/rutas.py`: registrar el resultado `falla_ia` al capturar `FallaExtraccionIA` antes de propagarla al manejador 502, y responder 422 `sin_consentimiento` antes de leer el PDF (hace pasar T041)
- [ ] T045 [US3] Completar `src/procfac/ui/app.py`: "Rechazar" y "Cancelar" llaman a `volver_a_carga()` (definida en T035); un `ErrorAPI` durante la extracción vuelve a `carga` con el aviso "No se pudo completar la extracción."; "Rechazar" registra `consentimiento`/`rechazado` y "Cancelar" registra `validacion`/`cancelada` con `registrar_proceso` (FR-025) (hace pasar T042)

**Checkpoint**: las historias 1, 2 y 3 funcionan; toda cancelación termina en la carga sin JSON.

---

## Phase 6: User Story 4 - Acceso con sesión y aislamiento entre usuarios simultáneos (Priority: P3)

**Goal**: sin sesión no se procesa; hasta 5 usuarios (y varias sesiones del mismo usuario)
trabajan a la vez sin ver datos ajenos y en menos de 30 s cada uno.

**Independent Test**: peticiones sin token o con credenciales inválidas se rechazan; 5
sesiones concurrentes con IA simulada reciben cada una solo su resultado; dos tokens del
mismo usuario quedan aislados (AC-04, AC-05, AC-25, AC-28, AC-29, AC-30, AC-38).

### Tests for User Story 4 (escribir primero; deben fallar) ⚠️

- [ ] T046 [P] [US4] Escribir `tests/integration/test_sesiones.py`: `/facturas/verificar` y `/facturas/extraer` sin `Authorization` o con un token inventado → 401 `no_autorizado` y el extractor no se llama (AC-05); login con clave incorrecta y con usuario inexistente → 401 `credenciales_invalidas` con el mismo mensaje (AC-25); 5 usuarios hacen login a la vez con `asyncio.gather` → 5 tokens distintos (AC-28); dos logins del mismo usuario → los dos tokens siguen válidos (AC-38)
- [ ] T047 [P] [US4] Escribir `tests/integration/test_aislamiento.py`: con un `ExtractorFalso` que devuelve una factura distinta según el texto y demora 0,5 s, 5 sesiones (incluidas 2 del mismo usuario) llaman a `/facturas/extraer` a la vez con PDF distintos; cada respuesta contiene solo la factura de su PDF (AC-04, AC-30, AC-38) y las 5 terminan en menos de 30 s (AC-29, con IA simulada); mientras A extrae, las respuestas de B a `/facturas/verificar` y `/auth/login` no contienen ningún valor de la factura de A
- [ ] T048 [P] [US4] Escribir `tests/ui/test_sesiones_ui.py` con `AppTest`: credenciales incorrectas → "Usuario o contraseña incorrectos." y sigue en `login` (AC-25); sin token en `session_state`, la app muestra solo el login; dos `AppTest` independientes (dos pestañas) con el mismo usuario no comparten `session_state` (AC-38)

### Implementation for User Story 4

- [ ] T049 [US4] Revisar `src/procfac/api/app.py` y `src/procfac/api/rutas.py` para que `usuario_actual` se evalúe **antes** de leer el cuerpo en `/facturas/*` (un 401 no lee el PDF) y que ninguna ruta guarde datos del proceso fuera de variables locales (hace pasar T046 y T047)
- [ ] T050 [US4] Completar `src/procfac/ui/app.py`: si no hay `token` en `session_state`, mostrar solo el login; en el login, mostrar `ErrorAPI.mensaje` de `credenciales_invalidas` con `st.error` (hace pasar T048)

**Checkpoint**: las cuatro historias funcionan de forma independiente.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: requisitos transversales (disco, logs) y aceptación con la API real

- [ ] T051 [P] Escribir `tests/integration/test_sin_archivos.py` (AC-22): genera un PDF con un marcador único, toma una instantánea de los archivos de `tempfile.gettempdir()` y del directorio de trabajo, recorre por API verificar → extraer y por UI (AppTest) carga → validación → descarga, cancelación, rechazo y abandono a mitad del proceso; después de cada etapa, ningún archivo nuevo o modificado contiene los bytes del PDF ni el JSON
- [ ] T052 [P] Escribir `tests/integration/test_logs.py` (AC-40): con `caplog`, recorre por API un rechazo, una falla de IA y una extracción correcta, y por UI (`AppTest`) un consentimiento rechazado y una validación cancelada, más una llamada directa a `registrar_descarga()`; cada petición y cada evento de UI deja una línea con `usuario`, `operacion`, `resultado` y `duracion_ms`; ninguna línea contiene valores de la factura, el texto extraído, contraseñas, tokens ni la API key; y no hay `FileHandler` configurado
- [ ] T053 [P] Escribir `tests/aceptacion/metricas.py`: `comparar(obtenido: dict, esperado: dict) -> dict[str, bool]` con las reglas de RNF-03 (coincidencia exacta por campo; `impuestos` como multiconjunto de pares sin importar el orden; cantidad de ítems; cantidades de todos los ítems; cada campo de ítem en todos los ítems, comparando por posición; si la cantidad de ítems difiere, los campos de ítem cuentan como incorrectos) y `precision(resultados) -> dict[str, float]`, con tests propios en `tests/unit/test_metricas.py`
- [ ] T054 Escribir `tests/aceptacion/test_conjunto_referencia.py` con `@pytest.mark.referencia` y `pytest.skip` si falta `tests/data/referencia/` o `ANTHROPIC_API_KEY`: procesa las 20 facturas de a una con la API real y `ExtractorClaude`; verifica la estructura de cada respuesta (AC-01), precisión ≥ 90% por campo con `metricas.py` (AC-15, AC-16, AC-20, AC-21, AC-31) y p95 de los 20 tiempos < 30 s medido desde la llamada a `/facturas/extraer` (AC-27) (aproxima SC-001: aceptar el consentimiento dispara esa llamada; el render de Streamlit queda fuera y se verifica a mano en el escenario 5 de quickstart.md); luego 5 facturas distintas a la vez, cada una en < 30 s (AC-29); con `caplog`, ninguna línea de log contiene valores de los JSON esperados ni la API key (SC-010, AC-40); imprime la tabla de precisión por campo (depende de T053)
- [ ] T055 [P] Escribir `tests/aceptacion/test_pdf_armados.py` con `@pytest.mark.referencia` y skip si faltan los archivos: PDF de AC-36 (3 copias, ítems de una sola copia en la cantidad del JSON esperado), AC-11 (campos no obtenidos iguales a las rutas de todos los `null` del JSON esperado, incluidos los de ítems e impuestos), AC-13 (comprobante no legible), y AC-14, AC-18 y AC-33 con los PDF reales armados (rechazo sin llamar a Claude)
- [ ] T056 Ajustar los patrones de `src/procfac/clasificacion.py` si alguna factura del Conjunto de referencia se rechaza por error (research.md §R3, riesgo aceptado), agregando primero el caso que falla a `tests/unit/test_clasificacion.py` con texto sintético (sin datos reales); si `claude-opus-5-5` con esfuerzo `low` no cumple AC-27, probar `claude-sonnet-5-5` cambiando solo `config/procfac.ini` y registrar el resultado en `specs/001-procesar-factura-a/research.md` §R4
- [ ] T057 Recorrer `specs/001-procesar-factura-a/quickstart.md` de punta a punta (escenarios 1 a 14, comprobaciones con curl, logs y disco) con `make dev` y corregir lo que no coincida; borrar los archivos copiados en `tests/data/` al terminar

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de la fase 1; **bloquea** todas las historias.
- **US1 (fase 3)**: depende de la fase 2. Es el MVP.
- **US2 (fase 4)**, **US3 (fase 5)** y **US4 (fase 6)**: dependen de la fase 2 y, en la
  práctica, de las rutas y pantallas de US1 (T032, T035), porque completan esos mismos
  archivos. Se pueden testear por separado.
- **Polish (fase 7)**: depende de las historias que se quieran validar; T054 y T055 necesitan
  los datos reales en `tests/data/` y la API key.

### User Story Dependencies

- **US1 (P1)**: solo la fase 2.
- **US2 (P2)**: la clasificación ya está en la fase 2; agrega los mensajes en
  `api/app.py` y `ui/app.py` (después de T032 y T035).
- **US3 (P2)**: completa `ia/cliente.py` (T030), `procesamiento.py` (T031), `rutas.py`
  (T032) y `ui/app.py` (T035).
- **US4 (P3)**: completa `api/` y `ui/app.py`; sin dependencias con US2 ni US3.

### Within Each User Story

- Los tests se escriben primero y deben fallar.
- Modelos → servicios (`procesamiento`, `ia`) → endpoints (`api/rutas.py`) → UI.
- Las tareas que tocan `src/procfac/ui/app.py` (T035, T039, T045, T050) o
  `src/procfac/api/app.py` (T023, T038, T049) van en secuencia.

### Parallel Opportunities

- Fase 1: T003, T004 y T005 en paralelo.
- Fase 2: los tests T006 a T014 en paralelo; después, T016, T017, T018, T020 y T021 en
  paralelo; T019 espera a T018 y T023 espera al resto.
- US1: T024 a T027 en paralelo; T028, T029 y T033 en paralelo.
- US2, US3 y US4: sus tests (T036-T037, T040-T042, T046-T048) en paralelo entre sí.
- Fase 7: T051, T052, T053 y T055 en paralelo.

---

## Parallel Example: User Story 1

```bash
# Tests de US1 a la vez (deben fallar):
Task: "Escribir tests/unit/test_procesamiento.py"
Task: "Escribir tests/unit/test_ia.py"
Task: "Escribir tests/integration/test_flujo_api.py"
Task: "Escribir tests/ui/test_flujo_ui.py"

# Piezas independientes de US1:
Task: "Implementar src/procfac/ia/modelos.py"
Task: "Implementar src/procfac/ia/prompt.py"
Task: "Implementar src/procfac/ui/cliente_api.py"
```

## Parallel Example: User Stories 2 a 4 (tests)

```bash
Task: "Escribir tests/integration/test_rechazos.py"
Task: "Escribir tests/integration/test_fallas_ia.py"
Task: "Escribir tests/integration/test_sesiones.py"
Task: "Escribir tests/integration/test_aislamiento.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1: Setup.
2. Fase 2: Foundational, con la clasificación desarrollada tests primero.
3. Fase 3: US1.
4. **Validar**: `uv run pytest` y el flujo con `make dev` usando una factura A real.
5. Mostrar el MVP: ya rechaza lo que está fuera de alcance (fase 2), aunque los mensajes
   finos de la UI llegan con US2.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → validar → MVP.
3. US2 → rechazos con mensajes por motivo.
4. US3 → cancelaciones y fallas de la IA.
5. US4 → sesiones, aislamiento y concurrencia.
6. Polish → AC-22, AC-40 y aceptación con el Conjunto de referencia.

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- [USn] vincula la tarea con su historia de spec.md.
- Commit después de cada tarea o grupo lógico, con Conventional Commits en español.
- Los PDF de prueba se generan en memoria con `fpdf2`; los reales solo van en `tests/data/`.
- No marcar como hechas las tareas con tests en rojo.

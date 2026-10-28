# Implementation Plan: Procesamiento de facturas A en PDF a JSON validado

**Branch**: `001-procesar-factura-a` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-procesar-factura-a/spec.md`

## Summary

Aplicación que recibe el PDF nativo de una factura A, la clasifica localmente (tipo,
cantidad de facturas, copias, páginas, texto extraíble) y, con el consentimiento del
usuario, envía el texto de una sola copia a la API de Claude para extraer encabezado,
ítems, impuestos y totales con el Esquema de salida. El usuario revisa, corrige o completa
los campos, los confirma y descarga el JSON. Una API FastAPI **sin estado de proceso**
(solo tokens en memoria) y una UI Streamlit que guarda cada proceso en la sesión de su
pestaña; nada se escribe en disco. Decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI + uvicorn (API), Streamlit (UI), pdfplumber (texto del
PDF), Pydantic v2 (esquema), `anthropic` 1.x (`AsyncAnthropic`, `messages.parse`),
python-multipart (parser en memoria), python-dotenv (`.env`), httpx (cliente de la UI);
desarrollo: pytest, pytest-asyncio, fpdf2 (PDF de prueba generados en memoria), jsonschema
(validación contra `esquema-salida.schema.json`).

**Storage**: N/A. Todo en memoria (RNF-07): tokens en un dict de la API; procesos en
`st.session_state`.

**Testing**: pytest. Unitarios e integración con el módulo de IA simulado; aceptación con
la API real bajo el marcador `referencia` ([research.md §R9](research.md)).

**Target Platform**: servidor Linux (también WSL2), un proceso de API y uno de UI.

**Project Type**: aplicación web (API HTTP + UI Streamlit) en un solo paquete Python.

**Performance Goals**: < 30 s p95 desde el consentimiento hasta ver los campos, con 1
usuario (RNF-02); < 30 s para cada uno con 5 simultáneos (RNF-04).

**Constraints**: 1 PDF por petición y 1 factura por PDF; hasta 3 páginas; tiempo de espera
de 60 s sin reintentos hacia Claude; 0 archivos con el PDF o el JSON en disco; logs sin
contenido.

**Scale/Scope**: hasta 5 usuarios del `.env`; 6 pantallas; 3 endpoints; 20 facturas en el
Conjunto de referencia.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitución v1.0.1. Verificado antes de la fase 0 y de nuevo después del diseño
(fase 1): **pasa sin desviaciones**.

| Principio | Cómo lo cumple el diseño | Estado |
|---|---|---|
| I. Lógica de IA aislada | Solo `src/procfac/ia/` importa `anthropic` y arma el prompt. Interfaz: el protocolo `Extractor` (`async def __call__(self, texto: str) -> Factura`, que lanza `FallaExtraccionIA`), implementado por `ExtractorClaude`. `procesamiento.py` recibe un `Extractor` por inyección, y los tests lo reemplazan por el doble `ExtractorFalso`. Un test verifica que ningún otro módulo importe `anthropic`. | ✅ |
| II. Solo facturas tipo A | `clasificacion.py` exige el código de comprobante 01 y excluye FCE MiPyME A, M, B, C, E, X, notas, recibos, remitos y liquidaciones **antes** de llamar a la IA ([research §R3](research.md)). | ✅ |
| III. Solo PDF nativo | Rechazo de lo que no es PDF (422), de los PDF protegidos, dañados, escaneados (sin texto), con más de una factura o con más de 3 páginas, sin invocar la IA. A la IA se le envía el texto de pdfplumber; no hay OCR. | ✅ |
| IV. JSON con esquema y validación del usuario | `esquema.Factura` (Pydantic v2) valida la salida de la IA; si no cumple → falla sin reintento. La UI muestra todo, permite corregir y completar, y habilita la descarga solo tras confirmar. | ✅ |
| V. Clasificación con tests primero | Las tareas de `clasificacion.py` y `pdf/lector.py` (T018, T019) empiezan por `tests/unit/test_lector_pdf.py` y `tests/unit/test_clasificacion.py` (T010, T011), que deben fallar antes de implementar. `tests/integration/test_rechazos.py` (T036) verifica después los códigos y mensajes de la API. Todo cambio posterior a la clasificación (T056) agrega primero su caso a T011. | ✅ |
| VI. Sin secretos en el código | API key y usuarios desde `.env` (`config.py`); `.env.example` sin valores reales; los logs no registran claves ni tokens. | ✅ |
| VII. Alcance limitado al PRD | Cada decisión cita RF, RNF o AC. RF-30 a RF-33 ya están en el PRD. Sin límite de intentos de login, sin vencimiento de sesión, sin `fallbacks` de modelo, sin límite de tamaño en bytes. | ✅ |

| Restricción adicional | Cómo se cumple |
|---|---|
| HTTP 422 ante 0 o más archivos, o un archivo que no es PDF | `api/multipart.py` cuenta las partes de archivo; `clasificacion.es_pdf` ([contracts/api.md](contracts/api.md)) |
| Consentimiento antes de enviar | La UI muestra la advertencia; la API exige además `consentimiento=true` |
| Sin reintentos y 60 s | `AsyncAnthropic(timeout=60.0, max_retries=0)` |
| Todo en memoria, incluidas las subidas de FastAPI | Sin `UploadFile`: `request.body()` y parser multipart en memoria ([research §R2](research.md)) |
| Sesión obligatoria y aislamiento | Bearer token en `/facturas/*`; API sin estado de proceso |
| Datos reales solo en `tests/data/` | Los tests de aceptación leen de ahí y se omiten si no existe |

## Project Structure

### Documentation (this feature)

```text
specs/001-procesar-factura-a/
├── plan.md              # este archivo
├── research.md          # fase 0
├── data-model.md        # fase 1
├── quickstart.md        # fase 1
├── contracts/
│   ├── api.md           # endpoints, errores y códigos HTTP
│   ├── esquema-salida.schema.json
│   └── ui.md            # pantallas y mensajes
├── checklists/
│   ├── requirements.md
│   └── general.md
└── tasks.md             # fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
pyproject.toml           # dependencias (uv), configuración de pytest y marcadores
Makefile                 # make dev: uvicorn + streamlit
.env.example             # nombres de variables, sin valores reales
config/
└── procfac.ini          # URL de la API, modelo, esfuerzo, timeout, máximo de páginas

src/procfac/
├── __init__.py
├── config.py            # lee el .ini y el .env; valida de 1 a 5 usuarios
├── logs.py              # registrar_proceso(): solo metadatos (RF-33)
├── esquema.py           # Factura, Item, Impuesto; normalización; serializar_json()
├── pdf/
│   └── lector.py        # bytes → DocumentoPDF (texto por página), en memoria
├── clasificacion.py     # reglas puras: es_pdf, páginas, factura A, una factura, copias
├── procesamiento.py     # verificar(), extraer(): orquesta, campos no obtenidos
├── auth.py              # usuarios, login, tokens en memoria
├── ia/                  # ÚNICO módulo que importa anthropic (principio I)
│   ├── __init__.py      # protocolo Extractor, FallaExtraccionIA; exporta ExtractorClaude
│   ├── cliente.py       # ExtractorClaude: AsyncAnthropic(timeout=60, max_retries=0)
│   ├── modelos.py       # FacturaIA (transporte)
│   └── prompt.py        # instrucciones del sistema
├── api/
│   ├── app.py           # FastAPI, manejadores de errores → {codigo, mensaje}
│   ├── multipart.py     # lectura del archivo único en memoria (AC-19, RNF-07)
│   └── rutas.py         # /auth/login, /facturas/verificar, /facturas/extraer
└── ui/
    ├── app.py           # Streamlit: máquina de estados de las pantallas
    ├── cliente_api.py   # llamadas HTTP a la API
    └── validacion.py    # formularios y tablas editables (RF-13, RF-16, RF-30)

tests/
├── conftest.py          # generadores de PDF con fpdf2, doble del módulo de IA, cliente ASGI
├── unit/                # clasificación, esquema, procesamiento, auth, multipart, logs, aislamiento de IA
├── integration/         # API de punta a punta con IA simulada; rechazos; AC-22; AC-30
├── ui/                  # Streamlit AppTest con cliente_api simulado
├── aceptacion/          # marcador referencia: Conjunto de referencia y API real (RNF-02, RNF-03, RNF-04)
└── data/                # ignorada por git; datos reales copiados a mano
```

**Structure Decision**: un solo paquete `procfac` con layout `src/`, porque la API y la UI
comparten el esquema (`esquema.py`) y se distribuyen juntas. La UI solo importa `esquema`,
`logs` y `cliente_api`; nunca `ia`, `clasificacion` ni `procesamiento`, que corren en la API.

## Complexity Tracking

Sin violaciones de la constitución que justificar.

## Pendientes para la implementación

- `.gitignore` ignora `.env.*`, lo que también ignora `.env.example`: hay que agregar la
  excepción `!.env.example` (tarea de setup).
- Validar con el Conjunto de referencia el criterio de clasificación por código 01 y los
  patrones de punto de venta y número ([research §R3](research.md), riesgo aceptado).
- Si `claude-opus-5-5` con esfuerzo `low` no cumple RNF-02, probar `claude-sonnet-5-5`
  cambiando solo el `.ini`.

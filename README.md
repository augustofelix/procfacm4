# ProcFac — Procesamiento de facturas A en PDF

Aplicación que lee facturas A en PDF nativo (encabezado, ítems, totales e impuestos) y
devuelve un JSON estandarizado, validado por el usuario antes de descargarlo, para que
otros sistemas contables lo importen.

Autor: [augustofelix](https://github.com/augustofelix)

## Problema

En estudios contables y empresas se cargan a mano grandes volúmenes de facturas en
sistemas que después calculan impuestos. Esa carga consume tiempo y genera errores de
tipeo, tiempo que podría destinarse al control, el análisis y el asesoramiento.

## Objetivo

Convertir cada factura A en un JSON validado por el usuario, con la extracción lista en
menos de 30 segundos p95 (RNF-02) y una precisión de al menos 90% por campo (RNF-03).

## Documentación del proyecto

| Documento | Contenido |
|---|---|
| [`PRD.md`](PRD.md) | Requerimientos funcionales (RF), no funcionales (RNF), criterios de aceptación (AC), esquema de salida, fuera de alcance y riesgos |
| [`specs/001-procesar-factura-a/`](specs/001-procesar-factura-a/) | Spec, plan, investigación, modelo de datos, tareas y checklists de la feature |
| [`contracts/api.md`](specs/001-procesar-factura-a/contracts/api.md) | Contrato de la API HTTP |
| [`contracts/ui.md`](specs/001-procesar-factura-a/contracts/ui.md) | Contrato de la interfaz Streamlit |
| [`contracts/esquema-salida.schema.json`](specs/001-procesar-factura-a/contracts/esquema-salida.schema.json) | JSON Schema del esquema de salida |
| [`quickstart.md`](specs/001-procesar-factura-a/quickstart.md) | Escenarios de validación manual y comprobaciones por API |
| [`AGENTS.md`](AGENTS.md) | Reglas para agentes de código (qué no hacer) |

## Cómo funciona

1. El usuario inicia sesión con las credenciales definidas en `.env`.
2. Sube **un** PDF. Antes de enviar nada a Claude, el sistema lo verifica localmente con
   pdfplumber y lo rechaza si no es un PDF, tiene más de 3 páginas, contiene más de una
   factura o no se puede identificar como factura A. Las copias ORIGINAL, DUPLICADO y
   TRIPLICADO de una misma factura cuentan como una sola.
3. Se muestra una advertencia: el contenido de la factura se enviará a la API de Claude.
   Si el usuario no acepta, el proceso se cancela.
4. Con el consentimiento, se extraen los datos con Claude (una sola llamada, sin
   reintentos, con 60 s de tiempo máximo) y se validan contra el esquema de salida.
5. El usuario revisa los campos, corrige o completa los que no se obtuvieron y confirma.
6. Recién entonces se habilita la descarga del JSON.

El PDF y el JSON se procesan solo en memoria: nunca se escriben en el disco del servidor
(RNF-07). Los logs registran solo metadatos (usuario, fecha y hora, resultado y
duración), nunca el contenido de la factura (RF-33).

## Alcance

**Incluye:** facturas tipo A en PDF nativo de hasta 3 páginas, una factura por PDF, hasta
5 usuarios simultáneos.

**No incluye** (ver "Fuera de Alcance" en el PRD): PDF escaneados, facturas M y FCE MiPyME
A, notas de crédito/débito, recibos, remitos, liquidaciones, comprobantes B, C, E y X,
carga por lotes, email, integración con sistemas contables, gestión de usuarios desde la
app, cierre o vencimiento de sesión y los campos de ítem reservados para la versión 2.

## Esquema de salida

Encabezado: `punto_venta`, `numero_comprobante`, `cuit_emisor`, `razon_social_emisor`,
`domicilio_emisor`, `localidad_emisor`, `condicion_iva_emisor`, `cuit_receptor`,
`razon_social_receptor`, `domicilio_receptor`, `localidad_receptor`,
`condicion_iva_receptor`, `fecha_comprobante` (`AAAA-MM-DD`), `condicion_venta`.

Pie: `subtotal`, `impuestos` (lista de `descripcion_impuesto` + `importe`), `total`.

Ítems: `codigo`, `descripcion`, `cantidad`, `precio_unitario`, `subtotal_item`.

Los campos no obtenidos se devuelven en `null`. Tipos y formatos en la sección "Esquema
de salida" del [PRD](PRD.md).

## Stack

- Python 3.13, gestionado con [uv](https://docs.astral.sh/uv/)
- FastAPI + Uvicorn (API)
- Streamlit (UI)
- pdfplumber (lectura y clasificación del PDF)
- Pydantic v2 (validación del esquema)
- API de Anthropic Claude (extracción)

## Estructura

```
config/procfac.ini      Configuración general (sin secretos)
.streamlit/config.toml  Tema visual de la UI (colores, tipografía y radios)
.env.example            Plantilla del .env con la API key y los usuarios
src/procfac/
  api/                  App FastAPI, endpoints y lectura del multipart
  ui/                   App Streamlit, cliente de la API, validación de campos y estilo
  pdf/                  Lectura del PDF en memoria
  ia/                   Cliente de Claude, prompt y modelos
  clasificacion.py      Detección de factura A, cantidad de facturas y copias
  procesamiento.py      Orquestación de verificación y extracción
  esquema.py            Esquema de salida (Pydantic)
  auth.py               Login y tokens de sesión en memoria
  config.py             Carga del .ini y del .env
  logs.py               Logs de metadatos
tests/
  unit/                 Tests unitarios
  integration/          Tests de la API
  ui/                   Tests de la UI
  aceptacion/           Aceptación con la API real de Claude (marcador "referencia")
```

## Instalación y configuración

Requisitos: Python 3.13 y `uv`.

```bash
uv sync
cp .env.example .env
```

Completar el `.env` (no se commitea):

```dotenv
ANTHROPIC_API_KEY=...
PROCFAC_USUARIO_1=...
PROCFAC_CLAVE_1=...
# hasta PROCFAC_USUARIO_5 / PROCFAC_CLAVE_5
```

Debe haber entre 1 y 5 usuarios. La configuración general (URL y puerto de la API,
modelo, esfuerzo, tiempo de espera, máximo de páginas) está en `config/procfac.ini`.

## Estilo de la UI

La interfaz usa la paleta, la tipografía (Inter) y los radios del template de diseño
`templateweb`, sin su marca ni sus imágenes:

- **Login:** pantalla dividida, con un panel azul con la marca y el propósito de la app
  a la izquierda y el formulario a la derecha. En pantallas angostas se ve solo el
  formulario.
- **Resto de las pantallas:** barra lateral con la marca, los pasos del proceso (cargar,
  consentimiento, validar, descargar) con el actual resaltado y el usuario con sesión;
  el contenido va en una tarjeta blanca.

Los colores base están en `.streamlit/config.toml` (se leen al levantar la UI, así que
un cambio requiere reiniciar `make dev`); el resto de los estilos, en
`src/procfac/ui/estilo.py`. El estilo es solo visual: los textos, las pantallas y el
flujo son los de [`contracts/ui.md`](specs/001-procesar-factura-a/contracts/ui.md).

## Cómo correr

```bash
make dev
```

Levanta la API en `http://127.0.0.1:8000` y la UI en `http://127.0.0.1:8501`. `Ctrl+C`
detiene las dos.

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/login` | Recibe `usuario` y `clave`, devuelve un token |
| `POST` | `/facturas/verificar` | Verifica el PDF sin llamar a Claude |
| `POST` | `/facturas/extraer` | Extrae los datos con Claude; requiere `consentimiento=true` |

Los endpoints de facturas requieren `Authorization: Bearer <token>` y exactamente un
archivo en el campo `archivo`. Detalle de respuestas y errores en
[`contracts/api.md`](specs/001-procesar-factura-a/contracts/api.md).

## Tests

```bash
uv run pytest                  # unitarios, integración y UI, sin la API real de Claude
uv run pytest -m referencia    # aceptación con la API real de Claude y tests/data/
```

Las pruebas de aceptación usan facturas reales y PDF armados que **no** están en el
repositorio: se copian a mano en `tests/data/` (ignorada por git) solo para la prueba y
se borran al terminar. La estructura esperada está en
[`tests/aceptacion/conftest.py`](tests/aceptacion/conftest.py).

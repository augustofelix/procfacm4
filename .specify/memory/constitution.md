# Constitución de Procesamiento de Factura (ProcFac)

## Principios fundamentales

### I. Lógica de IA aislada

Toda interacción con el modelo de IA (armado de las instrucciones o prompt, llamada a la API
de Claude, lectura y parseo de su respuesta) DEBE vivir en un módulo dedicado. La lógica de
negocio (validación de alcance, clasificación del comprobante, armado del JSON, sesión,
interfaz de usuario y API) NO DEBE importar el SDK de Anthropic ni construir prompts; usa el
módulo de IA solo a través de una interfaz explícita que recibe datos y devuelve datos
tipados (modelos Pydantic).

Razón: permite probar la lógica de negocio sin llamar a la API, reemplazar o simular el
proveedor de IA y auditar en un solo lugar qué datos salen hacia un tercero.

### II. Solo Facturas tipo A

El sistema DEBE procesar únicamente Facturas tipo A. Cualquier otro comprobante (facturas M,
FCE MiPyME A, notas de crédito o débito, recibos, remitos, liquidaciones, comprobantes B, C,
E o X) DEBE rechazarse antes de enviar contenido a la API de Claude. NO DEBE incorporarse un
nuevo tipo de comprobante sin una modificación explícita del PRD vigente que lo incluya en
el alcance.

Razón: el esquema de salida, las validaciones y el Conjunto de referencia están definidos
para Facturas A; ampliar el alcance sin modificar el PRD rompe esas garantías.

### III. Solo PDF nativo

Los documentos de entrada DEBEN ser archivos PDF nativos, con texto extraíble (no escaneados
ni imágenes). Un PDF sin texto extraíble, un archivo que no sea PDF, un PDF con más de una
factura o con más de 3 páginas DEBE rechazarse con un mensaje claro y sin invocar a la IA.
El sistema NO DEBE incorporar reconocimiento óptico de caracteres (OCR).

Razón: la extracción se apoya en el texto que obtiene pdfplumber; sobre documentos
escaneados la calidad y la trazabilidad de los datos no están garantizadas.

### IV. Salida JSON con esquema y validación del usuario

El resultado de la lectura DEBE entregarse en formato JSON conforme al Esquema de salida
definido en el PRD y validado con Pydantic v2. Una respuesta de la IA que no cumpla el
esquema DEBE tratarse como error: se informa y se cancela el proceso, sin reintentos. Antes
de habilitar la descarga, el usuario DEBE poder revisar todos los campos extraídos y
corregirlos o completarlos; ningún JSON se entrega sin ese paso de revisión.

Razón: la IA puede inventar valores; la revisión humana y un esquema estricto garantizan que
los sistemas contables reciban datos confiables y con una estructura estable.

### V. Clasificación con tests primero (NO NEGOCIABLE)

La lógica de clasificación (determinar si el documento es una Factura A procesable: tipo de
comprobante, cantidad de facturas, copias ORIGINAL, DUPLICADO y TRIPLICADO, cantidad de
páginas y PDF nativo) DEBE desarrollarse escribiendo primero los tests: se escriben los
tests, se verifica que fallen y recién entonces se implementa (ciclo rojo-verde-refactorizar).
Todo cambio en esa lógica DEBE venir acompañado de tests que lo cubran.

Razón: la clasificación es la barrera que evita procesar comprobantes fuera de alcance y
enviar datos innecesarios a un tercero; un error ahí pasa inadvertido y es costoso.

### VI. Sin secretos en el código

La clave de API de Claude, los usuarios y sus contraseñas DEBEN cargarse desde variables de
entorno, definidas en el archivo `.env` (fuera del repositorio). NO DEBEN aparecer secretos
en el código fuente, en los archivos `.ini`, en los tests, en los registros (logs) ni en el
historial de git. El archivo `.env` NO DEBE commitearse.

Razón: las credenciales están en texto plano; filtrarlas al repositorio compromete la cuenta
de la API y el acceso a la aplicación.

### VII. Alcance limitado al PRD vigente

No se agregan funcionalidades que no estén en el PRD vigente. Todo requerimiento nuevo DEBE
incorporarse primero al PRD (con sus identificadores RF, RNF y AC) antes de especificarse o
implementarse. Las exclusiones explícitas del MVP (validación de los datos corregidos,
correo electrónico, integración con sistemas contables, gestión de usuarios, cierre o
vencimiento de sesión, reintentos automáticos, límite de tamaño en bytes y campos de ítem de
la versión 2) DEBEN respetarse.

Razón: mantiene el MVP acotado y verificable contra sus criterios de aceptación, y evita
complejidad sin respaldo en los requerimientos.

## Restricciones adicionales

- Tecnologías: Python 3.13, FastAPI (API), Streamlit (interfaz de usuario), pdfplumber,
  Pydantic v2 y la API de Anthropic Claude; dependencias gestionadas con uv. La
  configuración general va en archivos `.ini`.
- Un único PDF por petición y una única factura por PDF; las copias ORIGINAL, DUPLICADO y
  TRIPLICADO cuentan como una sola factura. La API responde HTTP 422 ante 0 o más de un
  archivo, o ante un archivo que no sea PDF.
- Antes de enviar contenido a la API de Claude, el sistema DEBE advertir al usuario y obtener
  su consentimiento; si no acepta, se cancela el proceso y se vuelve a la pantalla de carga.
- Sin reintentos a la API de Claude: ante un error, una demora mayor a 60 segundos o una
  respuesta ilegible o fuera de esquema, se muestra un mensaje y se cancela el proceso.
- Todo el procesamiento DEBE hacerse en memoria: ni el PDF ni el JSON se escriben en el
  sistema de archivos del servidor (incluidos los archivos temporales de subida de FastAPI).
- Procesar requiere sesión iniciada; los datos de un usuario NO DEBEN ser accesibles para
  otro. Hasta 5 usuarios pueden procesar un PDF cada uno al mismo tiempo.
- Las facturas reales, los PDF armados para las pruebas y sus JSON esperados van solo en
  `tests/data/` (ignorada por git) y NO DEBEN commitearse.

## Flujo de desarrollo

- Cada funcionalidad se especifica, planifica y divide en tareas con Spec Kit
  (`/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`), y cada
  artefacto DEBE referenciar los identificadores RF, RNF y AC del PRD que cubre.
- El plan de cada funcionalidad DEBE incluir una verificación explícita contra los
  principios de esta constitución; toda desviación DEBE justificarse por escrito en el plan.
- Los tests se ejecutan con `pytest` y DEBEN pasar antes de integrar cambios. Los tests de
  la lógica de negocio NO DEBEN depender de la API real de Claude (se simula el módulo de IA).
- Los commits siguen Conventional Commits, con la descripción en español y en imperativo.

## Gobernanza

Esta constitución prevalece sobre cualquier otra práctica del proyecto. `PRD.md` define qué
se construye; esta constitución define cómo y con qué límites; `AGENTS.md` es la guía
operativa para agentes y DEBE mantenerse consistente con ambos.

- Enmiendas: se proponen por escrito con su motivo, se actualiza este archivo con un informe
  de impacto y se revisa la consistencia de las plantillas y artefactos que dependen de él.
- Versionado semántico: MAYOR para eliminar o redefinir principios de forma incompatible;
  MENOR para agregar principios o secciones, o ampliar sustancialmente una guía; PARCHE para
  aclaraciones y correcciones de redacción.
- Cumplimiento: toda revisión de especificación, plan, tareas o código DEBE verificar que se
  cumplan estos principios; un incumplimiento no justificado bloquea la integración.

**Versión**: 1.0.0 | **Ratificada**: 2026-10-26 | **Última enmienda**: 2026-10-26

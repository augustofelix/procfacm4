# Feature Specification: Procesamiento de facturas A en PDF a JSON validado

**Feature Branch**: `001-procesar-factura-a`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "Generá el spec a partir del PRD en PRD.md"

**Fuente**: `PRD.md` (PRD-001). Cada requerimiento y escenario indica entre paréntesis los
identificadores RF, RNF y AC del PRD que cubre.

## Clarifications

### Session 2026-10-27

- Q: Durante la validación, ¿el usuario puede agregar o eliminar filas en las listas `items` e `impuestos`, o solo editar los valores de las filas extraídas? → A: Puede editar, agregar y eliminar filas en `items` e `impuestos`, y cargar filas si la lista vino en `null` o vacía.
- Q: Si el usuario escribe en un campo numérico un valor que no es un número, ¿qué va en el JSON descargado? → A: La pantalla solo admite números en los campos numéricos (enteros en `punto_venta` y `numero_comprobante`; decimales con punto en importes y `cantidad`), por lo que el JSON siempre lleva números en esos campos. No se valida ningún otro aspecto de los datos ingresados.
- Q: ¿Qué se permite guardar en los registros (logs) de la aplicación sobre cada proceso? → A: Solo metadatos: usuario, momento, resultado (aceptado, rechazado y motivo, falla de IA, cancelado, descargado) y duración; nunca contenido del PDF, texto extraído, campos, JSON ni secretos.
- Q: Si el mismo usuario entra a la aplicación desde dos pestañas o dos equipos a la vez, ¿cómo se comporta? → A: Se permiten varias sesiones del mismo usuario; cada una tiene su propio proceso y no ve el de las otras.
- Q: Después de descargar el JSON, ¿qué pasa con el proceso y con la pantalla? → A: Se queda en la pantalla con la descarga disponible (se puede volver a descargar) y un botón "Procesar otra factura"; al usarlo, o al subir un PDF nuevo, se borran los datos del proceso y se vuelve a la pantalla de carga.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convertir una factura A en un JSON validado (Priority: P1)

Una persona del área contable (por ejemplo, Mariela, que carga 5000 comprobantes por mes, o
Juan Manuel, que carga 800 facturas de compras con detalle de productos) inicia sesión, sube
el PDF nativo de una factura A, acepta la advertencia de que el contenido se enviará a un
servicio de IA externo, revisa los campos extraídos (encabezado, ítems, totales e
impuestos), corrige o completa los que haga falta, los confirma y descarga un archivo JSON
listo para importar en su sistema contable.

**Why this priority**: es el valor central del producto: reemplaza el tipeo manual de cada
comprobante por una revisión, reduciendo tiempo y errores de carga. Sin este flujo no hay
producto.

**Independent Test**: con un usuario válido y una factura A del Conjunto de referencia, se
recorre el flujo completo y se verifica que el JSON descargado tenga la estructura del
Esquema de salida y los valores confirmados por el usuario.

**Acceptance Scenarios**:

1. **Given** un usuario definido en la configuración de credenciales, **When** ingresa su
   usuario y contraseña correctos, **Then** se inicia su sesión y se le muestra la pantalla
   de carga (AC-24).
2. **Given** un usuario autenticado en la pantalla de carga, **When** sube un PDF con una
   sola factura A, **Then** se le muestra una advertencia de que el contenido de la factura
   se enviará al servicio de IA externo, con opciones para aceptar y rechazar, y no se envía
   nada al servicio mientras no acepte (AC-06).
3. **Given** un usuario que aceptó el consentimiento, **When** termina la extracción,
   **Then** se le muestran todos los campos del Esquema de salida con los valores extraídos
   (AC-08), en la respuesta de esa misma petición, sin consultas posteriores (AC-17), y con
   la estructura y tipos del Esquema de salida antes de cualquier edición (AC-01).
4. **Given** un PDF de factura A que no incluye algunos campos del Esquema de salida,
   **When** termina la extracción, **Then** se indican como no obtenidos exactamente los
   campos que quedaron en `null`; un campo con lista vacía no se indica como no obtenido
   (AC-11).
5. **Given** un PDF identificable como factura A que no incluye ninguno de los campos del
   Esquema de salida, **When** termina la extracción, **Then** se muestra un mensaje que
   aclara que no se pudo leer el comprobante, junto con todos los campos vacíos para
   completar (AC-13).
6. **Given** un usuario al que se le muestran los campos extraídos, **When** corrige un
   campo, o completa campos no obtenidos, y descarga el JSON, **Then** el JSON contiene los
   valores corregidos y completados (AC-09, AC-12).
7. **Given** un usuario al que se le muestran los ítems e impuestos extraídos, **When**
   agrega una fila, elimina otra y descarga el JSON, **Then** las listas `items` e
   `impuestos` del JSON reflejan exactamente las filas que quedaron en pantalla (RF-13,
   RF-16).
8. **Given** un usuario que todavía no confirmó los campos, **When** intenta descargar el
   JSON, **Then** la descarga no está disponible (AC-26).
9. **Given** un usuario que confirmó los campos, **When** pide la descarga, **Then** recibe
   un archivo con extensión `.json` cuyos valores coinciden con los campos confirmados
   (AC-23).
10. **Given** un usuario que ya descargó el JSON, **When** lo vuelve a descargar y luego
    elige "Procesar otra factura", **Then** la segunda descarga contiene los mismos valores
    confirmados y después se vuelve a la pantalla de carga sin datos del proceso anterior
    (RF-32, AC-39).
11. **Given** un PDF de 3 páginas con las copias ORIGINAL, DUPLICADO y TRIPLICADO de una misma
   factura A, una por página, **When** el usuario lo sube y acepta el consentimiento,
   **Then** el PDF no se rechaza y la lista de ítems contiene los ítems de una sola copia,
   en la misma cantidad que su JSON esperado (AC-36).

---

### User Story 2 - Rechazar documentos fuera de alcance sin enviarlos a la IA (Priority: P2)

El usuario sube por error un archivo que no corresponde (otro tipo de comprobante, un PDF
escaneado o protegido, un PDF con varias facturas o con demasiadas páginas, o un archivo que
no es PDF). El sistema lo rechaza antes de compartir su contenido con el servicio de IA
externo, le explica el motivo y lo devuelve a la pantalla de carga.

**Why this priority**: protege datos sensibles (no se envía a un tercero contenido que no se
va a procesar) y evita JSON incorrectos para comprobantes que el esquema no contempla.

**Independent Test**: se suben los PDF armados para la prueba (AC-14, AC-18, AC-33) y
archivos no PDF, y se verifica en cada caso el mensaje de rechazo, la vuelta a la pantalla
de carga y que no hubo ningún envío al servicio de IA.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado en la pantalla de carga, **When** abre el selector de
   archivos, **Then** solo puede elegir un archivo (AC-02) y solo con extensión `.pdf`
   (AC-34).
2. **Given** un usuario autenticado, **When** envía al servicio de procesamiento una
   petición con 0 archivos, con más de un archivo o con un archivo que no es PDF, **Then**
   la petición se rechaza como entidad no procesable (HTTP 422) y no se procesa ningún
   archivo (AC-19, AC-35).
3. **Given** un PDF que contiene dos o más facturas, **When** el usuario lo sube, **Then** se
   rechaza sin enviarlo al servicio de IA, se muestra un mensaje que explica que contiene
   más de una factura y se vuelve a la pantalla de carga sin entregar JSON (AC-14).
4. **Given** un PDF de nota de crédito, nota de débito, recibo, remito, liquidación, factura
   M, FCE MiPyME A, factura B, C o E, comprobante tipo X, un PDF protegido con contraseña, un
   PDF escaneado o un comprobante de tipo no identificable, **When** el usuario lo sube,
   **Then** se rechaza sin enviarlo al servicio de IA, se muestra un mensaje que indica que
   no se pudo identificar el comprobante como factura A y se vuelve a la pantalla de carga
   sin entregar JSON (AC-18).
5. **Given** un PDF de 4 páginas con una sola factura A, **When** el usuario lo sube,
   **Then** se rechaza sin enviarlo al servicio de IA, se muestra un mensaje que indica que
   supera las 3 páginas y se vuelve a la pantalla de carga sin entregar JSON (AC-33).

---

### User Story 3 - Cancelar el proceso de forma segura (Priority: P2)

El usuario puede no aceptar compartir la factura con el servicio de IA o abandonar la
validación; además, el servicio de IA puede fallar. En todos los casos el proceso se cancela,
se informa al usuario cuando corresponde y no se entrega ningún JSON.

**Why this priority**: garantiza que nunca se comparta información sin consentimiento y que
nunca se entregue un JSON no revisado o incompleto por un error.

**Independent Test**: se rechaza el consentimiento, se cancela la validación y se simulan
las tres formas de falla del servicio de IA; en cada caso se verifica la vuelta a la
pantalla de carga sin JSON.

**Acceptance Scenarios**:

1. **Given** un usuario al que se le mostró la advertencia, **When** rechaza el
   consentimiento, **Then** se vuelve a la pantalla de carga sin entregar JSON y sin enviar
   nada al servicio de IA (AC-07).
2. **Given** un usuario en el paso de validación, **When** cancela la validación, **Then** se
   vuelve a la pantalla de carga sin entregar JSON (AC-10).
3. **Given** un usuario que aceptó el consentimiento, **When** el servicio de IA devuelve un
   error, no responde en 60 segundos o devuelve una respuesta ilegible o fuera del Esquema
   de salida, **Then** se muestra un mensaje que indica que no se pudo completar la
   extracción y se vuelve a la pantalla de carga sin entregar JSON, sin reintentar (AC-32).

---

### User Story 4 - Acceso con sesión y aislamiento entre usuarios simultáneos (Priority: P3)

Hasta 5 usuarios registrados trabajan al mismo tiempo, cada uno con su propio PDF; ninguno
puede procesar sin sesión ni ver o descargar datos del proceso de otro.

**Why this priority**: es necesario para usar la aplicación en un equipo contable, pero el
valor se demuestra primero con un solo usuario.

**Independent Test**: se inicia sesión con 5 usuarios, cada uno procesa un PDF distinto del
Conjunto de referencia al mismo tiempo, y se verifica tiempo de respuesta y que cada sesión
contenga solo sus propios datos; además se prueba el acceso sin sesión y con credenciales
inválidas.

**Acceptance Scenarios**:

1. **Given** un usuario en la pantalla de inicio de sesión, **When** ingresa un usuario o
   una contraseña que no coinciden con los configurados, **Then** no se inicia la sesión ni
   se muestra la pantalla de carga (AC-25).
2. **Given** un usuario sin sesión iniciada, **When** intenta procesar un PDF, **Then** la
   petición se rechaza como no autorizada (HTTP 401) y el archivo no se procesa (AC-05).
3. **Given** 5 usuarios configurados, **When** los 5 inician sesión al mismo tiempo,
   **Then** los 5 ven la pantalla de carga (AC-28).
4. **Given** 5 usuarios con sesión activa, **When** cada uno sube al mismo tiempo un PDF
   distinto del Conjunto de referencia y acepta el consentimiento, **Then** cada uno ve en
   su sesión los campos de su propio PDF en menos de 30 segundos desde que aceptó (AC-29).
5. **Given** los usuarios A y B con sesiones activas simultáneas, **When** A procesa un PDF
   y B usa la aplicación o envía peticiones con su propia sesión, **Then** ninguna pantalla
   ni respuesta para B muestra, contiene o permite descargar datos del proceso de A (AC-04,
   AC-30).

---

### Edge Cases

- PDF con las copias ORIGINAL, DUPLICADO y TRIPLICADO de una misma factura: cuenta como una
  sola factura y los ítems no se triplican (RF-18, AC-36).
- PDF de exactamente 3 páginas: se admite; 4 o más páginas se rechaza (RF-28, AC-33).
- Factura sin ítems o sin impuestos: `items` o `impuestos` se devuelven como lista vacía y no
  se marcan como no obtenidos; si no se pudieron obtener, se devuelven en `null` y sí se
  marcan (Esquema de salida, AC-11).
- Extracción que deja todos los campos en `null` (salvo `items` e `impuestos`, que pueden
  quedar en `null` o vacíos): se muestra el mensaje de comprobante no legible (RF-17, AC-13).
- PDF protegido con contraseña, escaneado o de tipo no identificable: se rechaza como "no
  identificado como factura A" (AC-18).
- El mismo usuario abre dos sesiones (pestañas o equipos) y procesa un PDF en cada una: cada
  sesión ve y descarga solo su propio proceso (FR-003, FR-003a, RF-31, AC-38).
- El servicio de IA tarda más de 60 segundos: se cancela sin reintentar (RF-26, AC-32).
- El usuario cierra el navegador a mitad del proceso: no queda ningún archivo con el PDF o
  el JSON en el servidor (RNF-07, AC-22).
- Valores corregidos o completados por el usuario que no respetan el formato del esquema: en
  los campos numéricos la pantalla no admite texto que no sea número (FR-019a); en el resto
  se aceptan sin validar en el MVP (riesgo aceptado en el PRD).

## Requirements *(mandatory)*

### Functional Requirements

**Acceso y sesión**

- **FR-001**: El sistema DEBE autenticar al usuario con usuario y contraseña contra las
  credenciales definidas en la configuración privada de la instalación (RF-19, AC-24, AC-25).
- **FR-002**: El sistema DEBE rechazar como no autorizada (HTTP 401) toda petición de
  procesamiento de un usuario sin sesión iniciada, sin procesar el archivo (RF-09, AC-05).
- **FR-003**: El sistema DEBE aislar cada proceso en la sesión que lo inició: ningún dato del
  proceso puede mostrarse, devolverse ni descargarse en otra sesión, sea de otro usuario o
  del mismo usuario (RF-05, AC-04, AC-30).
- **FR-003a**: El sistema DEBE permitir que un mismo usuario tenga varias sesiones activas a
  la vez (por ejemplo, en dos pestañas o dos equipos); un nuevo inicio de sesión no invalida
  las anteriores y cada sesión mantiene su propio proceso (RF-31, AC-38).

**Carga y filtrado previo**

- **FR-004**: El sistema DEBE aceptar exactamente un archivo por petición; el selector
  permite elegir uno solo y una petición con 0 o más de un archivo se rechaza como entidad no
  procesable (HTTP 422) (RNF-01, AC-02, AC-19).
- **FR-005**: El sistema DEBE rechazar todo archivo que no sea PDF; el selector solo permite
  archivos `.pdf` y una petición con otro tipo de archivo se rechaza como entidad no
  procesable (HTTP 422) (RF-29, AC-34, AC-35).
- **FR-006**: El sistema DEBE rechazar, antes de enviar contenido al servicio de IA, todo PDF
  de más de 3 páginas (RF-28, AC-33).
- **FR-007**: El sistema DEBE rechazar, antes de enviar contenido al servicio de IA, todo PDF
  cuyo tipo de comprobante no pueda identificar como factura A, incluidos los PDF protegidos
  con contraseña y los escaneados (sin texto extraíble) (RF-24, AC-18).
- **FR-008**: El sistema DEBE rechazar, antes de enviar contenido al servicio de IA, todo PDF
  con más de una factura; las copias ORIGINAL, DUPLICADO y TRIPLICADO de una misma factura
  cuentan como una sola (RF-18, RNF-05, AC-14, AC-36).
- **FR-009**: Ante un rechazo por FR-006, FR-007 o FR-008, el sistema DEBE mostrar un mensaje
  con el motivo específico (más de una factura, no identificado como factura A, más de 3
  páginas) y cancelar el proceso (RF-22, RF-23).

**Consentimiento**

- **FR-010**: Antes de enviar el contenido de la factura al servicio de IA, el sistema DEBE
  mostrar una advertencia de que se enviará a ese servicio, con opciones para aceptar y
  rechazar (RF-10, AC-06).
- **FR-011**: El sistema DEBE enviar el contenido al servicio de IA solo si el usuario
  aceptó; si rechaza, DEBE cancelar el proceso sin realizar ningún envío (RF-11, RF-20,
  AC-07).

**Extracción**

- **FR-012**: El sistema DEBE extraer el encabezado (punto de venta, número, fecha,
  condición de venta y datos de emisor y receptor), el detalle de ítems con sus cantidades y
  el pie diferenciando subtotal, impuestos y total (RF-01, RF-02, RF-03, RF-04).
- **FR-013**: El sistema DEBE devolver el resultado de la extracción con la estructura, los
  tipos y los formatos del Esquema de salida (ver Key Entities) (RF-25, AC-01).
- **FR-014**: El sistema DEBE devolver los campos extraídos en la respuesta de la misma
  petición que siguió a la aceptación del consentimiento (RNF-06, AC-17).
- **FR-015**: El sistema DEBE considerar falla del servicio de IA cuando devuelve un error,
  no responde dentro de 60 segundos o su respuesta no se puede leer o no cumple el Esquema
  de salida; ante una falla DEBE mostrar un mensaje de que no se pudo completar la
  extracción y cancelar el proceso, sin reintentar (RF-26, RF-27, AC-32).

**Validación y descarga**

- **FR-016**: El sistema DEBE mostrar al usuario todos los campos del Esquema de salida con
  los valores extraídos (RF-12, AC-08).
- **FR-017**: El sistema DEBE indicar cuáles campos no pudo obtener (los que quedaron en
  `null`), incluidos los campos de cada ítem e impuesto; un campo de lista vacía no se
  indica como no obtenido (RF-15, AC-11).
- **FR-018**: Cuando la extracción deja en `null` todos los campos (salvo `items` e
  `impuestos`, que pueden quedar en `null` o vacíos), el sistema DEBE mostrar un mensaje que
  aclare que no se pudo leer el comprobante, junto con los campos vacíos para completar
  (RF-17, AC-13).
- **FR-019**: El sistema DEBE permitir corregir cualquier campo extraído y completar los no
  obtenidos antes de la descarga, sin validar los valores ingresados salvo la restricción de tipo de FR-019a (RF-13, RF-16, AC-09,
  AC-12). En las listas `items` e `impuestos` el usuario DEBE poder editar, agregar y
  eliminar filas, incluso cuando la lista vino en `null` o vacía. Agregar y eliminar filas
  se interpreta como parte de corregir y completar los campos `items` e `impuestos`
  (RF-13, RF-16); no es un requisito nuevo respecto del PRD (principio VII).
- **FR-019a**: En los campos numéricos del Esquema de salida la pantalla de validación DEBE
  admitir solo números: enteros en `punto_venta` y `numero_comprobante`, y decimales con
  punto como separador en `subtotal`, `total`, `importe`, `cantidad`, `precio_unitario` y
  `subtotal_item`; un campo numérico vacío se descarga como `null`. Fuera de esta
  restricción de tipo no se valida el contenido (formato del CUIT, de la fecha, cantidad de
  decimales, coherencia de totales) (RF-30, AC-37).
- **FR-020**: El sistema DEBE habilitar la descarga solo después de que el usuario confirma
  explícitamente los campos (RF-21, AC-26).
- **FR-021**: El sistema DEBE entregar como archivo descargable con extensión `.json` los
  valores confirmados por el usuario (RF-07, AC-23).
- **FR-021a**: Después de la descarga, el sistema DEBE mantener la pantalla con la descarga
  disponible (volver a descargar entrega el mismo JSON confirmado) y ofrecer la opción
  "Procesar otra factura". Al elegirla, o al subir un PDF nuevo, DEBE descartar de memoria
  todos los datos del proceso anterior y volver a la pantalla de carga (RF-32, AC-39).
- **FR-022**: El sistema DEBE permitir cancelar la validación; al cancelar DEBE volver a la
  pantalla de carga sin entregar JSON (RF-14, AC-10).

**Cancelación y privacidad de datos**

- **FR-023**: Cancelar el proceso DEBE significar volver a la pantalla de carga sin entregar
  ningún JSON (RF-11).
- **FR-024**: El sistema NO DEBE escribir el PDF ni el JSON en el almacenamiento del
  servidor en ningún momento del proceso, incluido el abandono por cierre del navegador
  (RNF-07, AC-22).
- **FR-025**: Los registros (logs) de la aplicación DEBEN contener solo metadatos de cada
  proceso: usuario, fecha y hora, resultado (consentimiento aceptado o rechazado, rechazo y
  su motivo, falla del servicio de IA, validación cancelada, descarga) y duración. NO DEBEN
  contener el contenido del PDF, el texto extraído, valores de campos, el JSON, contraseñas
  ni la credencial del servicio de IA (RF-33, AC-40; RNF-07; constitución, principio VI).

### Key Entities

- **Usuario**: persona registrada en la configuración privada de la instalación (usuario y
  contraseña); hasta 5. No se administra desde la aplicación.
- **Sesión**: contexto de trabajo de un usuario autenticado; un usuario puede tener varias a
  la vez. Cada sesión contiene a lo sumo un proceso en curso y no comparte datos con otras
  sesiones, ni siquiera con las del mismo usuario.
- **Comprobante (PDF)**: archivo PDF nativo de hasta 3 páginas que contiene una sola factura
  A (puede incluir sus copias ORIGINAL, DUPLICADO y TRIPLICADO). Vive solo en memoria
  durante el proceso.
- **Resultado de extracción (Esquema de salida)**: campos de encabezado —`punto_venta` y
  `numero_comprobante` (enteros sin ceros a la izquierda), `cuit_emisor` y `cuit_receptor`
  (11 dígitos sin guiones), razón social, domicilio, localidad y condición de IVA de emisor
  y receptor (texto tal como figura en el PDF), `fecha_comprobante` (`AAAA-MM-DD`),
  `condicion_venta`—; totales —`subtotal` y `total` (decimales con 2 decimales y punto)—;
  `impuestos` (lista de pares `descripcion_impuesto` e `importe`) e `items` (lista de
  ítems). Todo campo no obtenido vale `null`; `items` e `impuestos` valen `[]` cuando el
  comprobante no tiene ninguno.
- **Ítem**: `codigo` y `descripcion` (texto tal como figura en el PDF), `cantidad` (decimal
  sin redondeo), `precio_unitario` y `subtotal_item` (decimales con 2 decimales). Unidad de
  medida, bonificación, alícuota de IVA y subtotal con IVA quedan para la versión 2.
- **JSON validado**: el Resultado de extracción con las correcciones y completados del
  usuario, entregado como archivo `.json` tras su confirmación.
- **Conjunto de referencia**: 20 facturas A reales en PDF nativo, cada una con su JSON
  esperado del mismo nombre; se usa para medir precisión y tiempo y no se versiona en el
  repositorio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con un solo usuario activo, el percentil 95 del tiempo entre la aceptación del
  consentimiento y la presentación de los campos extraídos es menor a 30 segundos sobre las
  20 facturas del Conjunto de referencia procesadas de a una; el p95 se calcula por rango
  más cercano: se ordenan los 20 tiempos y se toma el 19.º (RNF-02, AC-27).
- **SC-002**: Con 5 usuarios procesando un PDF cada uno al mismo tiempo, cada uno ve sus
  campos extraídos en menos de 30 segundos desde que aceptó el consentimiento (RNF-04,
  AC-29).
- **SC-003**: Cada campo de encabezado y de totales (`subtotal`, `impuestos`, `total`)
  coincide exactamente con el JSON esperado en al menos el 90% de las facturas del Conjunto
  de referencia; `impuestos` coincide si tiene los mismos pares sin importar el orden; un
  `null` obtenido coincide con un `null` esperado y no con un valor (regla que vale también
  para SC-004) (RNF-03, AC-20, AC-21).
- **SC-004**: La cantidad de ítems coincide en al menos el 90% de las facturas, las
  cantidades de todos los ítems coinciden en al menos el 90%, y cada campo `codigo`,
  `descripcion`, `precio_unitario` y `subtotal_item` coincide en todos los ítems en al menos
  el 90%, comparando los ítems por posición (RNF-03, AC-15, AC-16, AC-31).
- **SC-005**: El 100% de las extracciones del Conjunto de referencia cumple la estructura y
  los tipos del Esquema de salida antes de cualquier edición (AC-01).
- **SC-006**: El 100% de los documentos fuera de alcance de AC-14, AC-18 y AC-33 se rechaza
  sin ningún envío al servicio de IA y con el mensaje del motivo correspondiente.
- **SC-007**: En el 0% de los casos se envía contenido al servicio de IA sin consentimiento
  ni se entrega un JSON sin confirmación explícita del usuario (AC-06, AC-07, AC-26).
- **SC-008**: Se encuentran 0 archivos con el contenido del PDF o del JSON en el servidor en
  todas las inspecciones de AC-22 (RNF-07).
- **SC-009**: Un usuario nunca recibe datos del proceso de otro usuario en ninguna de las
  pruebas de AC-04 y AC-30.
- **SC-010**: Tras procesar el Conjunto de referencia, los registros de la aplicación no
  contienen ningún valor de campo de las facturas, texto extraído ni secreto (0
  coincidencias al buscar los valores de los JSON esperados y las credenciales) (RF-33,
  AC-40).

## Assumptions

- Los usuarios son personal contable que conoce las facturas A argentinas y puede detectar y
  corregir valores erróneos durante la validación.
- Los usuarios y sus contraseñas se definen en la configuración privada de la instalación
  (archivo `.env`, fuera del repositorio), junto con la credencial del servicio de IA; la
  configuración general de la aplicación va en archivos `.ini`.
- La extracción de datos depende del servicio de IA externo API de Claude (Anthropic); la
  identificación del tipo de comprobante, la cantidad de facturas y de páginas se resuelve
  localmente, sin ese servicio, y puede fallar (riesgo aceptado en el PRD).
- La aplicación expone, además de la pantalla, un servicio de procesamiento al que se pueden
  enviar peticiones directamente; por eso AC-05, AC-19, AC-30 y AC-35 se expresan en códigos
  de respuesta HTTP.
- La sesión no se cierra ni vence en el MVP; no hay cierre de sesión.
- No se limita el tamaño en bytes del PDF.
- Facturas en moneda extranjera: los importes se extraen tal como figuran, sin indicar la
  moneda ni convertirlos; el Esquema de salida no tiene campo de moneda y agregarlo
  requiere modificar el PRD.
- Fuera de alcance (PRD): PDF escaneados y OCR, email, otros comprobantes que no sean
  factura A, lotes, integración con sistemas contables, validación de datos corregidos (salvo la restricción de tipo de FR-019a),
  gestión de usuarios, reintentos automáticos al servicio de IA y los campos de ítem de la
  versión 2.
- El Conjunto de referencia, el PDF de AC-36 y los PDF armados para las pruebas (AC-11,
  AC-13, AC-14, AC-18, AC-33) y sus JSON esperados se proveen manualmente para las pruebas y
  no se versionan.

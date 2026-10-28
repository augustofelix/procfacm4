# Contrato de la interfaz (Streamlit)

**Feature**: `001-procesar-factura-a` | Estados y transiciones en
[data-model.md](../data-model.md#estados-del-proceso-en-la-ui-rf-11-rf-14-rf-21-rf-23-rf-27-rf-32).
Idioma de la interfaz: español (CHK036). Accesibilidad: la que da Streamlit por defecto; no
se agregan requisitos (no están en el PRD).

| Pantalla | Elementos | Requisitos |
|---|---|---|
| **Inicio de sesión** | campos usuario y contraseña; botón "Ingresar"; mensaje único "Usuario o contraseña incorrectos." | RF-19, AC-24, AC-25 |
| **Carga** | selector de archivos con `type=["pdf"]` y `accept_multiple_files=False`; mensaje del rechazo anterior, si lo hubo | RNF-01, RF-29, AC-02, AC-34 |
| **Consentimiento** | advertencia: "El texto de esta factura se enviará a la API de Claude (Anthropic) para extraer sus datos. Puede contener datos sensibles de terceros."; botones "Aceptar y procesar" y "Rechazar" | RF-10, RF-11, AC-06, AC-07 |
| **Extrayendo** | indicador de espera "Extrayendo los datos de la factura…" mientras dura la petición (hasta 60 s) | CHK030 |
| **Validación** | si `comprobante_ilegible`, `st.warning("No se pudo leer el comprobante. Los campos quedaron vacíos para completarlos.")`; campos de encabezado y totales (`st.text_input` para texto, `st.number_input` para enteros e importes); tablas editables de `impuestos` e `items` con filas agregables y eliminables (`st.data_editor`, `num_rows="dynamic"`, `NumberColumn` en columnas numéricas); cada campo no obtenido marcado con la etiqueta "No obtenido" y, debajo de cada tabla, la lista de sus celdas no obtenidas (por ejemplo, "No obtenido: ítem 1, precio_unitario"); en pantalla las filas se numeran desde 1 (`items[0]` es el ítem 1); botones "Confirmar" y "Cancelar"; **sin** botón de descarga | RF-12, RF-13, RF-15, RF-16, RF-17, RF-21, RF-30, AC-08 a AC-13, AC-26, AC-37 |
| **Descargable** | los mismos campos en solo lectura; botón "Descargar JSON" (`st.download_button`, `application/json`); botón "Procesar otra factura"; selector de archivos (`type=["pdf"]`, `accept_multiple_files=False`) para subir otra factura | RF-07, RF-21, RF-32, AC-23, AC-39 |

Mensajes al volver a **Carga**:

| Causa | Mensaje |
|---|---|
| Rechazo previo | el `mensaje` que devuelve la API ([api.md](api.md)) |
| Falla de la IA | "No se pudo completar la extracción." |
| Consentimiento rechazado, validación cancelada u "otra factura" | ninguno |

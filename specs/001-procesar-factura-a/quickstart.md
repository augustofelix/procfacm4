# Quickstart: validar la feature de punta a punta

**Feature**: `001-procesar-factura-a` | Contratos: [api.md](contracts/api.md),
[ui.md](contracts/ui.md) | Modelo: [data-model.md](data-model.md)

## Requisitos previos

- Python 3.13 y `uv`.
- Archivo `.env` en la raíz (no se commitea), a partir de `.env.example`:

  ```dotenv
  ANTHROPIC_API_KEY=...
  PROCFAC_USUARIO_1=mariela
  PROCFAC_CLAVE_1=...
  PROCFAC_USUARIO_2=juan
  PROCFAC_CLAVE_2=...
  ```

- Configuración general en `config/procfac.ini` (URL de la API, modelo, esfuerzo, tiempo de
  espera de 60 s, máximo de 3 páginas).
- Para las pruebas de aceptación: copiar a mano en `tests/data/` (ignorada por git) el
  Conjunto de referencia (`referencia/*.pdf` y `*.json`), el PDF de AC-36 y los PDF armados
  de AC-11, AC-13, AC-14, AC-18 y AC-33. Borrarlos al terminar.

## Instalar y correr

```bash
uv sync
make dev        # levanta la API (uvicorn, :8000) y la UI (streamlit, :8501)
```

## Tests

```bash
uv run pytest                       # unitarios e integración, sin la API real de Claude
uv run pytest -m referencia         # aceptación con la API real y tests/data/
```

## Escenarios de validación manual

| # | Pasos | Resultado esperado | AC |
|---|---|---|---|
| 1 | Ingresar con un usuario del `.env` | Pantalla de carga | AC-24 |
| 2 | Ingresar con una clave incorrecta | "Usuario o contraseña incorrectos."; sigue en el login | AC-25 |
| 3 | Subir una factura A del Conjunto de referencia | Advertencia de consentimiento; ninguna llamada a Claude (log sin `extraccion`) | AC-06 |
| 4 | Rechazar el consentimiento | Vuelve a la carga sin JSON | AC-07 |
| 5 | Repetir 3, aceptar | Campos extraídos en menos de 30 s; descarga deshabilitada | AC-08, AC-26, AC-27 |
| 6 | Corregir un campo, agregar y quitar un ítem, confirmar y descargar | El `.json` tiene los valores en pantalla | AC-09, AC-23 |
| 7 | Descargar otra vez y "Procesar otra factura" | Mismo JSON; vuelve a la carga sin datos | AC-39 |
| 8 | Escribir letras en `total` | El campo no las admite | AC-37 |
| 9 | Subir el PDF de AC-14, AC-18 (cada caso) y AC-33 | Mensaje del motivo; vuelve a la carga | AC-14, AC-18, AC-33 |
| 10 | Subir el PDF de AC-36 | No se rechaza; los ítems son los de una sola copia | AC-36 |
| 11 | Abrir dos pestañas con el mismo usuario y procesar un PDF distinto en cada una | Cada pestaña ve solo su PDF | AC-38 |

## Comprobaciones por API

```bash
# Sin sesión → 401 (AC-05)
curl -s -o /dev/null -w '%{http_code}\n' -F archivo=@factura.pdf \
  http://127.0.0.1:8000/facturas/verificar

TOKEN=$(curl -s -H 'Content-Type: application/json' \
  -d '{"usuario":"mariela","clave":"..."}' http://127.0.0.1:8000/auth/login | jq -r .token)

# Dos archivos → 422 cantidad_de_archivos (AC-19)
curl -s -H "Authorization: Bearer $TOKEN" -F archivo=@a.pdf -F archivo=@b.pdf \
  http://127.0.0.1:8000/facturas/verificar

# Archivo que no es PDF → 422 no_es_pdf (AC-35)
curl -s -H "Authorization: Bearer $TOKEN" -F archivo=@notas.txt \
  http://127.0.0.1:8000/facturas/verificar
```

## Comprobación de logs y disco

- Después del escenario 6, buscar en la salida de la API los valores del JSON descargado:
  no debe aparecer ninguno (AC-40).
- El test `tests/integration/test_sin_archivos.py` cubre AC-22; a mano, comparar
  `ls -la /tmp` antes y después del flujo.

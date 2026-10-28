import json
import logging

from procfac.esquema import Factura, serializar_json
from tests.conftest import factura_de_ejemplo
from tests.ui.conftest import hasta_validacion, ingresar, llamadas, nueva_app, resultado, subir, widget

ADVERTENCIA = "El texto de esta factura se enviará a la API de Claude (Anthropic)"
ILEGIBLE = "No se pudo leer el comprobante. Los campos quedaron vacíos para completarlos."


def test_login_lleva_a_la_carga(api):
    at = ingresar(nueva_app())
    assert at.session_state["estado"] == "carga"
    assert at.file_uploader[0].allowed_type == [".pdf"] or at.file_uploader[0].allowed_type == ["pdf"]


def test_pdf_admitido_muestra_el_consentimiento_sin_extraer(api):
    at = subir(ingresar(nueva_app()))
    assert at.session_state["estado"] == "consentimiento"
    assert any(ADVERTENCIA in w.value for w in at.warning)
    assert at.button(key="aceptar").label == "Aceptar y procesar"
    assert at.button(key="rechazar").label == "Rechazar"
    assert llamadas(api, "extraer") == []


def test_validacion_muestra_todos_los_campos_sin_descarga(api):
    at = hasta_validacion(api)
    claves = {w.key.rsplit("-", 1)[0] for w in [*at.text_input, *at.number_input]}
    escalares = {c for c in Factura.model_fields if c not in ("items", "impuestos")}
    assert escalares <= claves
    numericos = {w.key.rsplit("-", 1)[0] for w in at.number_input}
    assert numericos == {"punto_venta", "numero_comprobante", "subtotal", "total"}
    assert len(at.dataframe) == 2  # tablas de impuestos e ítems
    assert len(at.get("download_button")) == 0
    assert "No obtenido" in widget(at.text_input, "domicilio_receptor", at).label
    assert "No obtenido" not in widget(at.text_input, "razon_social_emisor", at).label
    assert any("ítem 2, precio_unitario" in c.value for c in at.caption)


def test_comprobante_ilegible(api):
    api.resultado = resultado(Factura(), ilegible=True)
    at = hasta_validacion(api)
    assert any(w.value == ILEGIBLE for w in at.warning)
    assert widget(at.text_input, "cuit_emisor", at).value == ""


def test_corregir_confirmar_y_descargar(api, caplog):
    caplog.set_level(logging.INFO, logger="procfac")
    # AppTest no puede vaciar un number_input: el total viene en null desde la extracción.
    api.resultado = resultado(factura_de_ejemplo(total=None))
    at = hasta_validacion(api)
    widget(at.text_input, "razon_social_emisor", at).input("NUEVA S.A.")
    widget(at.text_input, "cuit_emisor", at).input("3071234567")
    widget(at.text_input, "fecha_comprobante", at).input("2026-02-30")
    widget(at.text_input, "domicilio_emisor", at).input("")
    widget(at.number_input, "punto_venta", at).set_value(7)
    widget(at.text_input, "domicilio_receptor", at).input("Calle Falsa 123")
    at.button(key="confirmar").click().run()

    assert at.session_state["estado"] == "descargable"
    assert all(w.disabled for w in [*at.text_input, *at.number_input])
    datos = json.loads(serializar_json(at.session_state["factura"]))
    assert datos["razon_social_emisor"] == "NUEVA S.A."
    assert datos["cuit_emisor"] == "3071234567"  # sin validar (FR-019)
    assert datos["fecha_comprobante"] == "2026-02-30"
    assert datos["domicilio_emisor"] is None  # texto vaciado → null (research §R8)
    assert datos["total"] is None  # numérico vacío → null (AC-37)
    assert datos["punto_venta"] == 7
    assert datos["domicilio_receptor"] == "Calle Falsa 123"

    antes = serializar_json(at.session_state["factura"])
    boton = at.get("download_button")[0]
    assert boton.label == "Descargar JSON"
    boton.click().run()
    boton = at.get("download_button")[0]
    boton.click().run()
    assert serializar_json(at.session_state["factura"]) == antes  # la descarga no cambia nada
    assert sum("operacion=descarga" in r.getMessage() for r in caplog.records) == 2

    at.button(key="otra_factura").click().run()
    assert at.session_state["estado"] == "carga"
    for clave in ("pdf", "resultado", "factura"):
        assert clave not in at.session_state


def test_subir_otro_pdf_desde_la_descarga(api):
    at = hasta_validacion(api)
    assert len(at.file_uploader) == 0  # en la validación no hay selector
    at.button(key="confirmar").click().run()
    subir(at, "otra.pdf", b"%PDF-1.4 otra factura")
    assert at.session_state["estado"] == "consentimiento"
    assert at.session_state["pdf"] == ("otra.pdf", b"%PDF-1.4 otra factura")
    assert "resultado" not in at.session_state and "factura" not in at.session_state

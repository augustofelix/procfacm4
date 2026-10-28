import logging

from procfac.ui.cliente_api import ErrorAPI
from tests.ui.conftest import hasta_validacion, ingresar, llamadas, nueva_app, subir


def _sin_datos_del_proceso(at):
    return all(clave not in at.session_state for clave in ("pdf", "resultado", "factura"))


def test_rechazar_el_consentimiento(api, caplog):
    caplog.set_level(logging.INFO, logger="procfac")
    at = subir(ingresar(nueva_app()))
    at.button(key="rechazar").click().run()
    assert at.session_state["estado"] == "carga"
    assert llamadas(api, "extraer") == []
    assert _sin_datos_del_proceso(at)
    assert any("operacion=consentimiento resultado=rechazado" in r.getMessage() for r in caplog.records)


def test_cancelar_la_validacion(api, caplog):
    caplog.set_level(logging.INFO, logger="procfac")
    at = hasta_validacion(api)
    at.button(key="cancelar").click().run()
    assert at.session_state["estado"] == "carga"
    assert len(at.get("download_button")) == 0
    assert _sin_datos_del_proceso(at)
    assert any("operacion=validacion resultado=cancelada" in r.getMessage() for r in caplog.records)


def test_falla_de_la_ia_vuelve_a_la_carga(api):
    api.error_extraer = ErrorAPI("falla_extraccion", "No se pudo completar la extracción.", 502)
    at = subir(ingresar(nueva_app()))
    at.button(key="aceptar").click().run()
    assert at.session_state["estado"] == "carga"
    assert [e.value for e in at.error] == ["No se pudo completar la extracción."]
    assert len(llamadas(api, "extraer")) == 1
    assert _sin_datos_del_proceso(at)

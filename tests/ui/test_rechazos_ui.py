import pytest

from procfac.ui.cliente_api import ErrorAPI
from tests.ui.conftest import ingresar, llamadas, nueva_app, subir

RECHAZOS = {
    "mas_de_una_factura": "El PDF contiene más de una factura.",
    "no_es_factura_a": "No se pudo identificar el comprobante como factura A.",
    "mas_de_3_paginas": "El PDF supera las 3 páginas.",
}


def test_selector_solo_pdf_y_un_archivo(api):
    selector = ingresar(nueva_app()).file_uploader[0]
    assert selector.allowed_type in (["pdf"], [".pdf"])
    assert selector.accept_multiple_files is False


@pytest.mark.parametrize("codigo", RECHAZOS)
def test_rechazo_muestra_el_motivo_y_vuelve_a_la_carga(api, codigo):
    api.error_verificar = ErrorAPI(codigo, RECHAZOS[codigo], 422)
    at = subir(ingresar(nueva_app()))
    assert at.session_state["estado"] == "carga"
    assert [e.value for e in at.error] == [RECHAZOS[codigo]]
    assert len(at.warning) == 0  # no se muestra el consentimiento
    assert "pdf" not in at.session_state
    assert llamadas(api, "extraer") == []

import builtins

import pytest

from procfac.pdf.lector import PdfIlegible, leer_pdf
from tests.conftest import TEXTO_CONTINUACION, pdf_danado, pdf_factura_a, pdf_protegido, texto_comprobante


def test_devuelve_el_texto_de_cada_pagina_en_orden():
    documento = leer_pdf(pdf_factura_a([texto_comprobante(), TEXTO_CONTINUACION]))
    assert len(documento.paginas) == 2
    assert "Comp. Nro: 00000123" in documento.paginas[0]
    assert "Arandela" in documento.paginas[1]


@pytest.mark.parametrize("contenido", [pdf_protegido(), pdf_danado()])
def test_pdf_protegido_o_danado(contenido):
    with pytest.raises(PdfIlegible):
        leer_pdf(contenido)


def test_no_escribe_archivos(monkeypatch):
    open_original = builtins.open

    def open_solo_lectura(archivo, mode="r", *args, **kwargs):
        assert not any(letra in mode for letra in "wax+"), f"se abrió {archivo!r} para escribir"
        return open_original(archivo, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_solo_lectura)
    assert leer_pdf(pdf_factura_a([texto_comprobante()])).paginas

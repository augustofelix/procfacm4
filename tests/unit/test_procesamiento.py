import logging

import pytest

from procfac import procesamiento
from procfac.api.multipart import ArchivoRecibido
from procfac.clasificacion import MotivoRechazo, Rechazo
from procfac.esquema import Factura
from tests.conftest import ExtractorFalso, factura_de_ejemplo, pdf_con_copias, pdf_factura_a, texto_comprobante


def _archivo(contenido, nombre="f.pdf"):
    return ArchivoRecibido(nombre=nombre, contenido=contenido)


def test_campos_no_obtenidos_incluye_los_anidados():
    factura = factura_de_ejemplo(impuestos=[])
    no_obtenidos = procesamiento.campos_no_obtenidos(factura)
    assert "domicilio_receptor" in no_obtenidos and "localidad_receptor" in no_obtenidos
    assert "items[1].precio_unitario" in no_obtenidos
    assert "impuestos" not in no_obtenidos  # lista vacía: no se marca (AC-11)


def test_lista_en_null_se_marca():
    assert "items" in procesamiento.campos_no_obtenidos(Factura(items=None, impuestos=[]))


@pytest.mark.parametrize(
    "factura, esperado",
    [
        (Factura(), True),
        (Factura(items=[], impuestos=[]), True),
        (Factura(items=None, impuestos=[]), True),
        (Factura(total="10"), False),
        (Factura(items=[{"codigo": "A"}]), False),
    ],
)
def test_comprobante_ilegible(factura, esperado):
    assert procesamiento.comprobante_ilegible(factura) is esperado


async def test_extraer_envia_solo_la_primera_copia():
    extractor = ExtractorFalso(factura_de_ejemplo())
    resultado = await procesamiento.extraer(_archivo(pdf_con_copias()), "ana", extractor)
    assert extractor.llamadas == 1
    assert "ORIGINAL" in extractor.textos[0] and "DUPLICADO" not in extractor.textos[0]
    assert resultado.factura == factura_de_ejemplo()
    assert resultado.comprobante_ilegible is False


async def test_extraer_rechaza_sin_llamar_al_extractor():
    extractor = ExtractorFalso(factura_de_ejemplo())
    with pytest.raises(Rechazo) as error:
        await procesamiento.extraer(_archivo(pdf_factura_a([texto_comprobante("factura_b")])), "ana", extractor)
    assert error.value.motivo == MotivoRechazo.no_es_factura_a
    assert extractor.llamadas == 0


async def test_no_es_pdf_antes_de_leer():
    with pytest.raises(Rechazo) as error:
        await procesamiento.verificar(_archivo(b"hola", "notas.txt"), "ana")
    assert error.value.motivo == MotivoRechazo.no_es_pdf


async def test_registra_solo_metadatos(caplog):
    caplog.set_level(logging.INFO, logger="procfac")
    await procesamiento.verificar(_archivo(pdf_con_copias()), "ana")
    await procesamiento.extraer(_archivo(pdf_con_copias()), "ana", ExtractorFalso(factura_de_ejemplo()))
    lineas = [r.getMessage() for r in caplog.records]
    assert any("operacion=verificar" in l and "resultado=admitido" in l for l in lineas)
    assert any("operacion=extraer" in l and "resultado=extraido" in l for l in lineas)
    assert all("usuario=ana" in l and "duracion_ms=" in l for l in lineas)
    assert not any("Tornillo" in l or "30712345678" in l or "Comp. Nro" in l for l in lineas)

"""Clasificación previa al envío a la IA (principio V: tests primero; research.md §R3)."""

import pytest

from procfac.clasificacion import MotivoRechazo, clasificar, codigo_comprobante, es_pdf, identificador
from tests.conftest import COMPROBANTES, LEYENDAS, TEXTO_CONTINUACION, texto_comprobante

PDF = b"%PDF-1.7\n..."


def _clasificar(paginas, nombre="factura.pdf", contenido=PDF):
    return clasificar(nombre, contenido, paginas)


# (1) Es PDF: extensión y contenido.
@pytest.mark.parametrize(
    "nombre, contenido",
    [("factura.txt", PDF), ("factura.pdf", b"hola"), ("notas.txt", b"hola")],
)
def test_no_es_pdf(nombre, contenido):
    assert not es_pdf(nombre, contenido)
    resultado = _clasificar([texto_comprobante()], nombre, contenido)
    assert not resultado.admitido and resultado.motivo == MotivoRechazo.no_es_pdf


def test_extension_en_mayusculas():
    assert es_pdf("FACTURA.PDF", PDF)


# (2) No se pudo abrir (protegido o dañado).
def test_ilegible():
    assert _clasificar(None).motivo == MotivoRechazo.no_es_factura_a


# (3) Páginas.
def test_tres_paginas_se_admiten():
    assert _clasificar([texto_comprobante(), TEXTO_CONTINUACION, TEXTO_CONTINUACION]).admitido


def test_mas_de_3_paginas():
    paginas = [texto_comprobante()] + [TEXTO_CONTINUACION] * 3
    assert _clasificar(paginas).motivo == MotivoRechazo.mas_de_3_paginas


# (4) Texto extraíble.
@pytest.mark.parametrize("pagina_vacia", ["", "   \n  ", "abc"])
def test_pagina_sin_texto_es_escaneado(pagina_vacia):
    resultado = _clasificar([texto_comprobante(), pagina_vacia])
    assert resultado.motivo == MotivoRechazo.no_es_factura_a


# (5) Tipo de comprobante, solo por código.
@pytest.mark.parametrize(
    "texto_codigo", ["COD. 01", "Cód. 001", "Código: 01", "CODIGO N° 01", "Código Nro001 Factura"]
)
def test_formatos_del_codigo_01(texto_codigo):
    assert codigo_comprobante(f"FACTURA A\n{texto_codigo}\nPunto de Venta: 1") == 1


def test_codigo_no_salta_de_linea():
    assert codigo_comprobante("Código\n001") is None


# Sin rótulo: el código va junto a la letra del recuadro.
@pytest.mark.parametrize(
    "texto, codigo",
    [
        ("A\n01 FACTURA\nNº: 00003-00001429", 1),
        ("ORIGINAL\nA\nComprobante: 0012 - 00075812\n001 Fecha Emisión:01/09/2026", 1),
        ("B\n06 FACTURA\nNº: 00003-00001429", 6),
    ],
)
def test_codigo_junto_a_la_letra(texto, codigo):
    assert codigo_comprobante(texto) == codigo


@pytest.mark.parametrize(
    "texto",
    [
        "A\n01/09/2026",  # fecha
        "A\n0012 - 00075812",  # número de comprobante
        "A\n1 FACTURA",  # sin cero a la izquierda
        "A\nuno\ndos\ntres\n01 FACTURA",  # lejos de la letra
        "01 FACTURA",  # sin letra
    ],
)
def test_numeros_que_no_son_el_codigo(texto):
    assert codigo_comprobante(texto) is None


def test_factura_a_con_codigo_junto_a_la_letra_se_admite():
    texto = texto_comprobante().replace("FACTURA    A\nCOD. 01", "A\n01 FACTURA")
    assert _clasificar([texto]).admitido


@pytest.mark.parametrize("tipo", [t for t in COMPROBANTES if t != "factura_a"])
def test_comprobantes_fuera_de_alcance(tipo):
    resultado = _clasificar([texto_comprobante(tipo)])
    assert not resultado.admitido and resultado.motivo == MotivoRechazo.no_es_factura_a


def test_sin_codigo():
    texto = texto_comprobante().replace("COD. 01", "")
    assert _clasificar([texto]).motivo == MotivoRechazo.no_es_factura_a


def test_palabras_de_otros_comprobantes_no_rechazan():
    texto = texto_comprobante(extra="Remito N° 0001-00000456\nRecibí conforme\nLiquidación de envío")
    resultado = _clasificar([texto])
    assert resultado.admitido, resultado


def test_continuacion_sin_encabezado_se_admite():
    resultado = _clasificar([texto_comprobante(), TEXTO_CONTINUACION])
    assert resultado.admitido
    assert resultado.paginas_a_enviar == [0, 1]
    assert resultado.copias == 1


def test_segunda_pagina_con_otro_codigo():
    paginas = [texto_comprobante(), texto_comprobante("nota_credito_a", leyenda=None)]
    assert _clasificar(paginas).motivo == MotivoRechazo.no_es_factura_a


# (6) Una sola factura.
def test_identificador_normalizado():
    assert identificador("Punto de Venta: 00001    Comp. Nro: 00000123") == (1, 123)
    assert identificador("FACTURA A  N° 0001-00000123") == (1, 123)
    assert identificador("Remito N° 0001-00000456") is None
    assert identificador(TEXTO_CONTINUACION) is None


def test_dos_facturas_distintas():
    paginas = [texto_comprobante(numero=123), texto_comprobante(numero=124)]
    assert _clasificar(paginas).motivo == MotivoRechazo.mas_de_una_factura


def test_mismo_identificador_con_y_sin_ceros():
    paginas = [
        texto_comprobante(leyenda="ORIGINAL"),
        texto_comprobante(leyenda="DUPLICADO").replace(
            "Punto de Venta: 00001    Comp. Nro: 00000123", "N° 1-123"
        ),
    ]
    resultado = _clasificar(paginas)
    assert resultado.admitido and resultado.copias == 2


def test_copias_original_duplicado_triplicado():
    resultado = _clasificar([texto_comprobante(leyenda=leyenda) for leyenda in LEYENDAS])
    assert resultado.admitido
    assert resultado.paginas_a_enviar == [0]
    assert resultado.copias == 3


def test_copias_de_dos_paginas():
    paginas = [
        texto_comprobante(leyenda="ORIGINAL"), TEXTO_CONTINUACION,
        texto_comprobante(leyenda="DUPLICADO"),
    ]
    resultado = _clasificar(paginas)
    assert resultado.admitido and resultado.paginas_a_enviar == [0, 1] and resultado.copias == 2


# Orden: se informa la primera regla que falla.
def test_primer_motivo_del_orden():
    paginas = [texto_comprobante("factura_b")] * 4
    assert _clasificar(paginas, "x.txt").motivo == MotivoRechazo.no_es_pdf
    assert _clasificar(paginas).motivo == MotivoRechazo.mas_de_3_paginas
    dos_facturas_una_b = [texto_comprobante(numero=1), texto_comprobante("factura_b", numero=2)]
    assert _clasificar(dos_facturas_una_b).motivo == MotivoRechazo.no_es_factura_a

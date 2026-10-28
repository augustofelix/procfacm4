"""Fábricas de PDF en memoria y textos de ejemplo para los tests.

Los PDF se generan con fpdf2 y se devuelven como `bytes`: nunca se escriben en disco
(RNF-07). Los textos imitan el formato de los comprobantes AFIP, sin datos reales.
"""

import asyncio
import io

from fpdf import FPDF
from PIL import Image

LEYENDAS = ("ORIGINAL", "DUPLICADO", "TRIPLICADO")

# nombre: (letra, código AFIP, título). El tipo X no lleva código.
COMPROBANTES = {
    "factura_a": ("A", "01", "FACTURA"),
    "nota_debito_a": ("A", "02", "NOTA DE DÉBITO"),
    "nota_credito_a": ("A", "03", "NOTA DE CRÉDITO"),
    "recibo_a": ("A", "04", "RECIBO"),
    "factura_b": ("B", "06", "FACTURA"),
    "factura_c": ("C", "11", "FACTURA"),
    "factura_e": ("E", "19", "FACTURA DE EXPORTACIÓN"),
    "factura_m": ("M", "51", "FACTURA"),
    "liquidacion_a": ("A", "63", "LIQUIDACIÓN"),
    "remito": ("R", "91", "REMITO"),
    "fce_mipyme_a": ("A", "201", "FACTURA DE CRÉDITO ELECTRÓNICA MiPyME (FCE)"),
    "tipo_x": ("X", None, "DOCUMENTO NO VÁLIDO COMO FACTURA"),
}


def texto_comprobante(
    tipo: str = "factura_a",
    punto_venta: int = 1,
    numero: int = 123,
    leyenda: str | None = "ORIGINAL",
    extra: str = "",
) -> str:
    """Texto de una página de comprobante con encabezado, ítems y totales."""
    letra, codigo, titulo = COMPROBANTES[tipo]
    lineas = [
        leyenda or "",
        f"{titulo}    {letra}",
        f"COD. {codigo}" if codigo else "",
        f"Punto de Venta: {punto_venta:05d}    Comp. Nro: {numero:08d}",
        "Fecha de Emisión: 15/03/2026",
        "Razón Social: EMPRESA EJEMPLO S.A.",
        "Domicilio Comercial: Av. Siempre Viva 742 - Rosario",
        "CUIT: 30-71234567-8    Condición frente al IVA: IVA Responsable Inscripto",
        "Cliente: CLIENTE DE PRUEBA S.R.L.    CUIT: 30-70000000-1",
        "Condición de venta: Contado",
        "Código    Producto / Servicio    Cantidad    Precio Unit.    Subtotal",
        "P001    Tornillo 10 mm    10,00    50,00    500,00",
        "P002    Tuerca 10 mm    5,00    100,00    500,00",
        "Importe Neto Gravado: $ 1000,00",
        "IVA 21%: $ 210,00",
        "Importe Total: $ 1210,00",
        extra,
    ]
    return "\n".join(linea for linea in lineas if linea)


TEXTO_CONTINUACION = (
    "P003    Arandela 10 mm    20,00    10,00    200,00\n"
    "P004    Bulón 10 mm    4,00    50,00    200,00\n"
    "Transporte: $ 400,00"
)


def pdf_factura_a(paginas_texto: list[str], user_password: str | None = None) -> bytes:
    """PDF con una página por texto."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=10)
    for texto in paginas_texto:
        pdf.add_page()
        pdf.multi_cell(0, 5, texto)
    if user_password is not None:
        pdf.set_encryption(owner_password="duenio", user_password=user_password)
    return bytes(pdf.output())


def pdf_con_copias(texto: str | None = None, copias=LEYENDAS) -> bytes:
    """Una página por copia de la misma factura (AC-36)."""
    return pdf_factura_a([texto_comprobante(leyenda=leyenda) for leyenda in copias])


def pdf_n_paginas(n: int) -> bytes:
    """Una factura A de `n` páginas: la primera con encabezado y el resto de continuación."""
    return pdf_factura_a([texto_comprobante()] + [TEXTO_CONTINUACION] * (n - 1))


def pdf_protegido() -> bytes:
    return pdf_factura_a([texto_comprobante()], user_password="secreta")


def pdf_escaneado() -> bytes:
    """Una página que solo tiene una imagen, sin texto extraíble."""
    imagen = io.BytesIO()
    Image.new("RGB", (200, 280), "white").save(imagen, format="PNG")
    imagen.seek(0)
    pdf = FPDF()
    pdf.add_page()
    pdf.image(imagen, x=10, y=10, w=190)
    return bytes(pdf.output())


def pdf_danado() -> bytes:
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog"


class ExtractorFalso:
    """Doble del módulo de IA: registra las llamadas y nunca usa la red.

    `resultado` es una `Factura`, una excepción a lanzar o una función texto → Factura.
    """

    def __init__(self, resultado, demora: float = 0.0):
        self.resultado = resultado
        self.demora = demora
        self.llamadas = 0
        self.textos: list[str] = []

    async def __call__(self, texto: str):
        self.llamadas += 1
        self.textos.append(texto)
        if self.demora:
            await asyncio.sleep(self.demora)
        if isinstance(self.resultado, BaseException):
            raise self.resultado
        if callable(self.resultado):
            return self.resultado(texto)
        return self.resultado


def config_de_prueba(**cambios):
    from procfac.config import Configuracion

    valores = dict(
        api_url="http://api.test", host="127.0.0.1", puerto=8000, modelo="claude-opus-5-5",
        esfuerzo="low", timeout_segundos=60, max_tokens=16000, max_paginas=3,
        min_caracteres_por_pagina=20, usuarios={"ana": "clave-ana", "beto": "clave-beto"},
        anthropic_api_key="clave-api-de-prueba",
    )
    valores.update(cambios)
    return Configuracion(**valores)


def factura_de_ejemplo(**cambios):
    from procfac.esquema import Factura, Impuesto, Item

    valores = dict(
        punto_venta=1, numero_comprobante=123, cuit_emisor="30712345678",
        razon_social_emisor="EMPRESA EJEMPLO S.A.", domicilio_emisor="Av. Siempre Viva 742",
        localidad_emisor="Rosario", condicion_iva_emisor="IVA Responsable Inscripto",
        cuit_receptor="30700000001", razon_social_receptor="CLIENTE DE PRUEBA S.R.L.",
        domicilio_receptor=None, localidad_receptor=None,
        condicion_iva_receptor="IVA Responsable Inscripto", fecha_comprobante="2026-03-15",
        condicion_venta="Contado", subtotal="1000", total="1210",
        impuestos=[Impuesto(descripcion_impuesto="IVA 21%", importe="210")],
        items=[
            Item(codigo="P001", descripcion="Tornillo 10 mm", cantidad="10", precio_unitario="50",
                 subtotal_item="500"),
            Item(codigo="P002", descripcion="Tuerca 10 mm", cantidad="5", precio_unitario=None,
                 subtotal_item="500"),
        ],
    )
    valores.update(cambios)
    return Factura(**valores)

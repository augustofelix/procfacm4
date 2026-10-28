"""Lectura del texto del PDF en memoria con pdfplumber (RNF-07)."""

import io
from dataclasses import dataclass

import pdfplumber


class PdfIlegible(Exception):
    """El PDF está protegido con contraseña o dañado."""


@dataclass(frozen=True)
class DocumentoPDF:
    paginas: list[str]


def leer_pdf(contenido: bytes) -> DocumentoPDF:
    try:
        with pdfplumber.open(io.BytesIO(contenido)) as pdf:
            return DocumentoPDF([pagina.extract_text(layout=True) or "" for pagina in pdf.pages])
    except Exception as error:  # pdfminer lanza excepciones de varios tipos.
        raise PdfIlegible() from error

"""Principio I: solo procfac.ia importa el SDK de Anthropic."""

import ast
from pathlib import Path

RAIZ = Path(__file__).parents[2] / "src" / "procfac"


def _importados(archivo: Path) -> set[str]:
    modulos = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module)
    return modulos


def test_solo_ia_importa_anthropic():
    culpables = [
        str(archivo.relative_to(RAIZ))
        for archivo in RAIZ.rglob("*.py")
        if "ia" not in archivo.relative_to(RAIZ).parts[:1]
        and any(m == "anthropic" or m.startswith("anthropic.") for m in _importados(archivo))
    ]
    assert culpables == []


def test_la_ui_no_importa_la_logica_de_la_api():
    prohibidos = ("procfac.ia", "procfac.clasificacion", "procfac.procesamiento")
    culpables = [
        str(archivo.relative_to(RAIZ))
        for archivo in (RAIZ / "ui").rglob("*.py")
        if any(m.startswith(prohibidos) for m in _importados(archivo))
    ]
    assert culpables == []

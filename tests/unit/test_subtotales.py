"""Advertencia de subtotales: suma de subtotal_item contra subtotal (RF-34)."""

from decimal import Decimal

from procfac.esquema import FacturaEditada, ItemEditado
from procfac.ui.validacion import diferencia_subtotales
from tests.conftest import factura_de_ejemplo


def _editada(subtotal, *subtotales_item, items_null=False):
    items = None if items_null else [ItemEditado(subtotal_item=s) for s in subtotales_item]
    return FacturaEditada(subtotal=subtotal, items=items)


def test_sin_diferencia_cuando_coinciden():
    assert diferencia_subtotales(factura_de_ejemplo()) is None  # 500 + 500 = 1000


def test_diferencia_devuelve_suma_y_subtotal():
    assert diferencia_subtotales(factura_de_ejemplo(subtotal="900")) == (Decimal("1000.00"), Decimal("900.00"))


def test_igualdad_exacta_a_dos_decimales():
    assert diferencia_subtotales(_editada(Decimal("100.01"), Decimal("100"))) is not None
    assert diferencia_subtotales(_editada(Decimal("100.00"), Decimal("60.50"), Decimal("39.50"))) is None


def test_null_vale_cero():
    assert diferencia_subtotales(_editada(Decimal("500"), Decimal("500"), None)) is None
    assert diferencia_subtotales(_editada(None, None)) is None
    assert diferencia_subtotales(_editada(None, Decimal("10"))) == (Decimal("10.00"), Decimal("0.00"))


def test_items_null_o_vacios_suman_cero():
    assert diferencia_subtotales(_editada(None, items_null=True)) is None
    assert diferencia_subtotales(_editada(Decimal("0"))) is None
    assert diferencia_subtotales(_editada(Decimal("100"), items_null=True)) == (Decimal("0.00"), Decimal("100.00"))

from tests.aceptacion.metricas import comparar, p95, precision

ESPERADO = {
    "punto_venta": 1, "numero_comprobante": 123, "cuit_emisor": "30712345678", "domicilio_receptor": None,
    "subtotal": 1000, "total": 1210.5,
    "impuestos": [{"descripcion_impuesto": "IVA 21%", "importe": 210}, {"descripcion_impuesto": "Perc. IIBB", "importe": 0.5}],
    "items": [
        {"codigo": "A", "descripcion": "Uno", "cantidad": 1, "precio_unitario": 10, "subtotal_item": 10},
        {"codigo": "B", "descripcion": "Dos", "cantidad": 2.5, "precio_unitario": 4, "subtotal_item": 10},
    ],
}


def _copia(**cambios):
    import copy

    obtenido = copy.deepcopy(ESPERADO)
    obtenido.update(cambios)
    return obtenido


def test_todo_coincide_y_los_numeros_se_normalizan():
    obtenido = _copia(subtotal=1000.0, impuestos=list(reversed(ESPERADO["impuestos"])))
    assert all(comparar(obtenido, ESPERADO).values())


def test_null_coincide_solo_con_null():
    assert comparar(_copia(), ESPERADO)["domicilio_receptor"]
    assert not comparar(_copia(domicilio_receptor="Calle 1"), ESPERADO)["domicilio_receptor"]
    assert not comparar(_copia(total=None), ESPERADO)["total"]


def test_impuestos_distintos():
    assert not comparar(_copia(impuestos=ESPERADO["impuestos"][:1]), ESPERADO)["impuestos"]


def test_items_por_posicion():
    obtenido = _copia(items=list(reversed(ESPERADO["items"])))
    resultado = comparar(obtenido, ESPERADO)
    assert resultado["items_cantidad"]
    assert not resultado["items_codigo"] and not resultado["items_cantidades"]


def test_cantidad_de_items_distinta_invalida_los_campos_de_item():
    resultado = comparar(_copia(items=ESPERADO["items"][:1]), ESPERADO)
    assert not resultado["items_cantidad"]
    assert not any(v for k, v in resultado.items() if k.startswith("items_"))


def test_precision_y_p95():
    assert precision([{"a": True}, {"a": False}, {"a": True}, {"a": True}]) == {"a": 0.75}
    assert p95(list(range(20, 0, -1))) == 19

import pytest

from procfac.auth import Autenticador, CredencialesInvalidas, NoAutorizado


@pytest.fixture
def autenticador():
    return Autenticador({"ana": "clave-ana", "beto": "clave-beto"})


def test_login_devuelve_un_token_nuevo_por_llamada(autenticador):
    primero = autenticador.login("ana", "clave-ana")
    segundo = autenticador.login("ana", "clave-ana")
    assert primero != segundo
    assert autenticador.usuario_de(primero) == "ana"
    assert autenticador.usuario_de(segundo) == "ana"


@pytest.mark.parametrize("usuario, clave", [("ana", "mal"), ("nadie", "clave-ana"), ("", "")])
def test_credenciales_incorrectas(autenticador, usuario, clave):
    with pytest.raises(CredencialesInvalidas) as error:
        autenticador.login(usuario, clave)
    assert "usuario" not in str(error.value).lower() or "contraseña" in str(error.value).lower()


@pytest.mark.parametrize("token", ["inventado", "", None])
def test_token_invalido(autenticador, token):
    with pytest.raises(NoAutorizado):
        autenticador.usuario_de(token)

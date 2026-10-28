from tests.ui.conftest import ingresar, nueva_app, subir


def test_credenciales_incorrectas(api):
    at = ingresar(nueva_app(), "ana", "mal")
    assert at.session_state["estado"] == "login"
    assert [e.value for e in at.error] == ["Usuario o contraseña incorrectos."]
    assert len(at.file_uploader) == 0


def test_sin_token_solo_se_ve_el_login(api):
    at = nueva_app()
    at.session_state["estado"] = "carga"
    at.run()
    assert at.session_state["estado"] == "login"
    assert len(at.file_uploader) == 0
    assert at.button(key="ingresar")


def test_dos_pestanas_del_mismo_usuario_no_comparten_datos(api):
    primera = subir(ingresar(nueva_app()), "uno.pdf", b"%PDF-1.4 uno")
    segunda = ingresar(nueva_app())
    assert primera.session_state["estado"] == "consentimiento"
    assert segunda.session_state["estado"] == "carga"
    assert "pdf" not in segunda.session_state
    assert primera.session_state["token"] != segunda.session_state["token"]

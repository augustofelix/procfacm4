"""UI de ProcFac: máquina de estados por sesión de navegador (data-model.md → Estados).

Cada pestaña tiene su propio `st.session_state`, así que cada sesión tiene su proceso
(RF-31). El PDF y la factura viven solo en memoria (RNF-07).
"""

import time

import streamlit as st

from procfac.config import url_api
from procfac.esquema import FacturaEditada, nombre_archivo, serializar_json
from procfac.logs import configurar_logs, registrar_proceso
from procfac.ui import cliente_api
from procfac.ui.cliente_api import ErrorAPI
from procfac.ui.validacion import mostrar_campos, registrar_descarga

ADVERTENCIA = (
    "El texto de esta factura se enviará a la API de Claude (Anthropic) para extraer sus "
    "datos. Puede contener datos sensibles de terceros."
)
MENSAJE_FALLA = "No se pudo completar la extracción."
MENSAJE_ILEGIBLE = "No se pudo leer el comprobante. Los campos quedaron vacíos para completarlos."
DATOS_DEL_PROCESO = ("pdf", "resultado", "factura", "inicio_proceso")

ss = st.session_state


def _cliente() -> cliente_api.ClienteAPI:
    return cliente_api.ClienteAPI(url_api())


def _duracion_ms() -> int:
    return int((time.time() - ss.get("inicio_proceso", time.time())) * 1000)


def _registrar(operacion: str, resultado: str) -> None:
    registrar_proceso(ss.usuario_activo, operacion, resultado, None, _duracion_ms())


def volver_a_carga(aviso: str | None = None) -> None:
    """Descarta de memoria los datos del proceso y vuelve a la pantalla de carga."""
    for clave in DATOS_DEL_PROCESO:
        ss.pop(clave, None)
    ss.aviso = aviso
    ss.estado = "carga"
    ss.selector = ss.get("selector", 0) + 1  # selector de archivos nuevo, vacío


def _sesion_vencida() -> None:
    # La API se reinició y perdió los tokens: hay que volver a ingresar.
    for clave in (*DATOS_DEL_PROCESO, "token"):
        ss.pop(clave, None)
    ss.estado = "login"


def _subir(nombre: str, contenido: bytes) -> None:
    volver_a_carga()
    ss.inicio_proceso = time.time()
    try:
        _cliente().verificar(ss.token, nombre, contenido)
    except ErrorAPI as error:
        if error.codigo == "no_autorizado":
            _sesion_vencida()
        else:
            volver_a_carga(error.mensaje)
        return
    ss.pdf = (nombre, contenido)
    ss.estado = "consentimiento"


def _selector_de_archivos(etiqueta: str) -> None:
    archivo = st.file_uploader(
        etiqueta, type=["pdf"], accept_multiple_files=False, key=f"selector-{ss.get('selector', 0)}"
    )
    if archivo is not None:
        _subir(archivo.name, archivo.getvalue())
        st.rerun()


def pantalla_login() -> None:
    st.title("ProcFac")
    usuario = st.text_input("Usuario", key="usuario")
    clave = st.text_input("Contraseña", type="password", key="clave")
    if st.button("Ingresar", key="ingresar"):
        try:
            ss.token = _cliente().login(usuario, clave)
        except ErrorAPI as error:
            st.error(error.mensaje)
            return
        ss.usuario_activo = usuario
        volver_a_carga()
        st.rerun()


def pantalla_carga() -> None:
    st.title("Cargar factura A")
    if ss.get("aviso"):
        st.error(ss.aviso)
    _selector_de_archivos("Factura A en PDF")


def pantalla_consentimiento() -> None:
    st.title("Consentimiento")
    st.warning(ADVERTENCIA)
    aceptar, rechazar = st.columns(2)
    if aceptar.button("Aceptar y procesar", key="aceptar"):
        _registrar("consentimiento", "aceptado")
        ss.estado = "extrayendo"
        st.rerun()
    if rechazar.button("Rechazar", key="rechazar"):
        _registrar("consentimiento", "rechazado")
        volver_a_carga()
        st.rerun()


def pantalla_extrayendo() -> None:
    nombre, contenido = ss.pdf
    with st.spinner("Extrayendo los datos de la factura…"):
        try:
            resultado = _cliente().extraer(ss.token, nombre, contenido)
        except ErrorAPI as error:
            if error.codigo == "no_autorizado":
                _sesion_vencida()
            else:
                volver_a_carga(MENSAJE_FALLA if error.codigo == "falla_extraccion" else error.mensaje)
            st.rerun()
    ss.resultado = resultado
    ss.factura = FacturaEditada.model_validate(resultado.factura.model_dump())
    ss.proceso = ss.get("proceso", 0) + 1  # widgets nuevos para cada proceso
    ss.estado = "validacion"
    st.rerun()


def pantalla_validacion() -> None:
    st.title("Validar los datos")
    if ss.resultado.comprobante_ilegible:
        st.warning(MENSAJE_ILEGIBLE)
    factura = mostrar_campos(ss.factura, True, ss.resultado.campos_no_obtenidos, str(ss.proceso))
    confirmar, cancelar = st.columns(2)
    if confirmar.button("Confirmar", key="confirmar"):
        ss.factura = factura
        ss.estado = "descargable"
        st.rerun()
    if cancelar.button("Cancelar", key="cancelar"):
        _registrar("validacion", "cancelada")
        volver_a_carga()
        st.rerun()


def pantalla_descargable() -> None:
    st.title("Descargar el JSON")
    mostrar_campos(ss.factura, False, ss.resultado.campos_no_obtenidos, f"{ss.proceso}-confirmado")
    st.download_button(
        "Descargar JSON",
        data=serializar_json(ss.factura),
        file_name=nombre_archivo(ss.factura),
        mime="application/json",
        on_click=registrar_descarga,
        args=(ss.usuario_activo, ss.inicio_proceso),
    )
    if st.button("Procesar otra factura", key="otra_factura"):
        volver_a_carga()
        st.rerun()
    _selector_de_archivos("Subir otra factura")


PANTALLAS = {
    "login": pantalla_login,
    "carga": pantalla_carga,
    "consentimiento": pantalla_consentimiento,
    "extrayendo": pantalla_extrayendo,
    "validacion": pantalla_validacion,
    "descargable": pantalla_descargable,
}

st.set_page_config(page_title="ProcFac")
configurar_logs()
if not ss.get("token"):
    ss.estado = "login"
ss.setdefault("estado", "login")
PANTALLAS[ss.estado]()

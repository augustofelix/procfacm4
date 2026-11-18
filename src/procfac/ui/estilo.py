"""Estilo visual de la UI: tokens, login dividido y barra lateral del template.

Solo presentación: no cambia textos, estados ni flujo (contracts/ui.md). Los colores
base están en `.streamlit/config.toml`; acá va lo que el tema de Streamlit no cubre.
"""

import html

import streamlit as st

TOKENS = """
:root {
  --brand-ink: #173f67;
  --brand-action: #1769aa;
  --brand-hover: #12598f;
  --brand-pressed: #0e4b78;
  --brand-soft: #eef6fc;
  --nav-header: #d5e0e9;
  --nav-active: #cbe0ee;
  --nav-active-text: #0f5f9a;
  --nav-icon: #647b8e;
  --nav-text: #203f59;
  --nav-border: #bccbd8;
  --surface-base: #ffffff;
  --surface-canvas: #f4f7f9;
  --text-primary: #172433;
  --text-secondary: #3f5062;
  --text-tertiary: #68798a;
  --border-soft: #e7ecf1;
  --border-standard: #d9e1e8;
  --radius-control: 8px;
  --radius-card: 10px;
}
"""

COMUN = """
[data-testid="stHeader"] { background: transparent; }
h1 {
  font-weight: 720 !important;
  letter-spacing: -.04em;
  color: var(--text-primary);
}
.stButton button, .stDownloadButton button {
  min-height: 40px;
  font-weight: 600;
  border-radius: var(--radius-control);
}
.stButton button[kind="primary"]:hover,
.stDownloadButton button[kind="primary"]:hover {
  background: var(--brand-hover);
  border-color: var(--brand-hover);
}
.stButton button[kind="primary"]:active,
.stDownloadButton button[kind="primary"]:active {
  background: var(--brand-pressed);
  border-color: var(--brand-pressed);
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within {
  box-shadow: 0 0 0 3px #1769aa1f;
}
[data-testid="stWidgetLabel"] p {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}
"""

LOGIN = """
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--surface-base); }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
[data-testid="stMainBlockContainer"] { max-width: 100%; padding: 0; }
.panel-login {
  display: flex;
  flex-direction: column;
  gap: 48px;
  min-height: 100vh;
  padding: 34px clamp(28px, 4vw, 58px) 80px;
  background: linear-gradient(145deg, rgba(12, 42, 70, .94), rgba(23, 63, 103, .78)), #173f67;
}
.panel-login .marca strong { color: #fff; }
.panel-login .marca small { color: #ffffffa3; }
.panel-login .propuesta {
  margin-top: auto;
  max-width: 520px;
}
.panel-login .propuesta span {
  color: #8dd0f4;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: .11em;
  text-transform: uppercase;
}
.panel-login .propuesta h2 {
  margin: 12px 0 14px;
  padding: 0;
  color: #fff;
  font-size: clamp(26px, 2.8vw, 42px);
  font-weight: 680;
  line-height: 1.04;
  letter-spacing: -.045em;
}
.panel-login .propuesta p { margin: 0; color: #ffffffb8; font-size: 14px; line-height: 1.55; }
.st-key-formulario-login {
  max-width: 420px;
  margin: 18vh auto 0;
  padding: 0 24px;
}
.st-key-formulario-login .stButton button { width: 100%; min-height: 44px; margin-top: 12px; }
@media (max-width: 640px) {
  .panel-login { display: none; }
  .st-key-formulario-login { margin-top: 32px; }
}
"""

TRABAJO = """
[data-testid="stSidebar"] { border-right: 1px solid var(--nav-border); }
[data-testid="stSidebarHeader"] { display: none; }
[data-testid="stSidebarUserContent"] { padding: 0; }
.cabecera-menu {
  min-height: 72px;
  padding: 15px 16px;
  background: var(--nav-header);
  border-bottom: 1px solid var(--nav-border);
}
.cabecera-menu .marca strong { color: var(--text-primary); }
.cabecera-menu .marca small { color: var(--nav-icon); }
.grupo-menu {
  margin: 18px 16px 8px;
  color: var(--nav-icon);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .09em;
  text-transform: uppercase;
}
.item-menu {
  position: relative;
  margin: 2px 8px;
  padding: 10px 11px;
  border-radius: 8px;
  color: var(--nav-text);
  font-size: 13.5px;
}
.item-menu.activo {
  background: var(--nav-active);
  color: var(--nav-active-text);
  font-weight: 600;
}
.item-menu.activo::before {
  content: "";
  position: absolute;
  top: 9px;
  bottom: 9px;
  left: -8px;
  width: 3px;
  border-radius: 0 4px 4px 0;
  background: var(--brand-action);
}
.usuario-menu {
  margin: 24px 16px 0;
  padding-top: 14px;
  border-top: 1px solid var(--nav-border);
  color: var(--nav-text);
  font-size: 12.5px;
}
.usuario-menu span {
  display: block;
  color: var(--nav-icon);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .09em;
  text-transform: uppercase;
}
[data-testid="stMainBlockContainer"] {
  max-width: 1100px;
  margin: 32px auto;
  padding: 28px 32px;
  background: var(--surface-base);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
}
[data-testid="stMainBlockContainer"] h1 {
  padding-left: 14px;
  border-left: 4px solid var(--brand-action);
  font-size: 26px;
}
"""

MARCA = """
<style>
.marca {{ display: flex; align-items: center; gap: 11px; }}
.marca .sello {{
  display: grid; place-items: center; width: 40px; height: 40px; flex: 0 0 40px;
  border-radius: 11px; background: {fondo_sello}; color: #fff;
  font-size: 14px; font-weight: 750; letter-spacing: -.02em;
}}
.marca div {{ display: flex; flex-direction: column; gap: 4px; }}
.marca strong {{ font-size: 16px; font-weight: 720; line-height: 1; letter-spacing: -.02em; }}
.marca small {{
  font-size: 9px; font-weight: 700; line-height: 1; letter-spacing: .1em; text-transform: uppercase;
}}
</style>
"""

PASOS = (
    ("Cargar factura", ("carga",)),
    ("Consentimiento", ("consentimiento", "extrayendo")),
    ("Validar datos", ("validacion",)),
    ("Descargar JSON", ("descargable",)),
)


def _css(*bloques: str) -> None:
    st.html("<style>" + "".join(bloques) + "</style>")


def _marca(fondo_sello: str) -> str:
    return MARCA.format(fondo_sello=fondo_sello) + (
        '<div class="marca"><span class="sello">PF</span>'
        "<div><strong>ProcFac</strong><small>Facturas A a JSON</small></div></div>"
    )


def aplicar_login() -> None:
    _css(TOKENS, COMUN, LOGIN)


def panel_login() -> None:
    """Panel izquierdo del login: marca y propósito de la app (PRD, Objetivos)."""
    st.html(
        '<div class="panel-login">'
        + _marca("#1769aa")
        + '<div class="propuesta"><span>Procesamiento de facturas</span>'
        "<h2>Facturas A en PDF a un JSON estandarizado</h2>"
        "<p>Lee el encabezado, los ítems y los totales e impuestos de la factura y "
        "devuelve un JSON, validado por el usuario antes de descargarlo, para que otros "
        "sistemas contables lo importen.</p></div></div>"
    )


def aplicar_trabajo(estado: str, usuario: str) -> None:
    """Pantallas con sesión: tarjeta central y barra lateral con los pasos del proceso."""
    _css(TOKENS, COMUN, TRABAJO)
    pasos = "".join(
        f'<div class="item-menu{" activo" if estado in estados else ""}">{nombre}</div>'
        for nombre, estados in PASOS
    )
    with st.sidebar:
        st.html(
            '<div class="cabecera-menu">'
            + _marca("#173f67")
            + '</div><div class="grupo-menu">Proceso</div>'
            + pasos
            + f'<div class="usuario-menu"><span>Usuario</span>{html.escape(usuario)}</div>'
        )

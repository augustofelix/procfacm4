"""Usuarios del .env, login y tokens de sesión en memoria (RF-09, RF-19, RF-31)."""

import hmac
import secrets
import threading


class CredencialesInvalidas(Exception):
    def __init__(self):
        super().__init__("Usuario o contraseña incorrectos.")


class NoAutorizado(Exception):
    pass


class Autenticador:
    """Sin vencimiento ni cierre de sesión (fuera de alcance del MVP)."""

    def __init__(self, usuarios: dict[str, str]):
        self._usuarios = dict(usuarios)
        self._tokens: dict[str, str] = {}
        self._lock = threading.Lock()

    def login(self, usuario: str, clave: str) -> str:
        valido = False
        for nombre, clave_configurada in self._usuarios.items():
            # Se comparan todos para no revelar por el tiempo qué usuario existe.
            coincide_usuario = hmac.compare_digest(nombre.encode(), usuario.encode())
            coincide_clave = hmac.compare_digest(clave_configurada.encode(), clave.encode())
            valido |= coincide_usuario and coincide_clave
        if not valido:
            raise CredencialesInvalidas()
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = usuario
        return token

    def usuario_de(self, token: str | None) -> str:
        with self._lock:
            usuario = self._tokens.get(token or "")
        if usuario is None:
            raise NoAutorizado()
        return usuario

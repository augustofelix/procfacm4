"""Cliente HTTP de la UI hacia la API (contracts/api.md). El PDF viaja desde memoria."""

import httpx

from procfac.esquema import ResultadoExtraccion

# Más que los 60 s de la API de Claude, para que el corte lo informe la API.
TIMEOUT_SEGUNDOS = 75.0


class ErrorAPI(Exception):
    def __init__(self, codigo: str, mensaje: str, status: int):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.status = status


class ClienteAPI:
    def __init__(self, url: str):
        self._url = url.rstrip("/")

    def _post(self, ruta: str, token: str | None = None, **kwargs) -> dict:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            with httpx.Client(base_url=self._url, timeout=TIMEOUT_SEGUNDOS) as cliente:
                respuesta = cliente.post(ruta, headers=headers, **kwargs)
        except httpx.TimeoutException as error:
            raise ErrorAPI("falla_extraccion", "No se pudo completar la extracción.", 0) from error
        except httpx.HTTPError as error:
            raise ErrorAPI("sin_conexion", "No se pudo conectar con el servicio.", 0) from error
        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = {}
        if respuesta.is_success:
            return cuerpo
        if isinstance(cuerpo, dict) and "codigo" in cuerpo:
            raise ErrorAPI(cuerpo["codigo"], cuerpo["mensaje"], respuesta.status_code)
        raise ErrorAPI("error_inesperado", "No se pudo completar la operación.", respuesta.status_code)

    def login(self, usuario: str, clave: str) -> str:
        return self._post("/auth/login", json={"usuario": usuario, "clave": clave})["token"]

    def verificar(self, token: str, nombre: str, contenido: bytes) -> dict:
        return self._post("/facturas/verificar", token, files={"archivo": (nombre, contenido, "application/pdf")})

    def extraer(self, token: str, nombre: str, contenido: bytes) -> ResultadoExtraccion:
        cuerpo = self._post(
            "/facturas/extraer", token,
            files={"archivo": (nombre, contenido, "application/pdf")},
            data={"consentimiento": "true"},
        )
        return ResultadoExtraccion.model_validate(cuerpo)

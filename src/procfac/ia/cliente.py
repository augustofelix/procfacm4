"""Llamada a la API de Claude: una sola vez, sin reintentos y con tiempo de espera (RF-26)."""

import anthropic
import pydantic

from procfac.config import Configuracion
from procfac.esquema import Factura
from procfac.ia.modelos import FacturaIA, a_factura
from procfac.ia.prompt import INSTRUCCIONES


class ExtractorClaude:
    def __init__(self, config: Configuracion, cliente=None):
        self._config = config
        # max_retries=0: el SDK reintenta 2 veces por defecto y RF-26 lo prohíbe.
        # Sin `fallbacks`: reenviar a otro modelo también sería un reintento.
        self.cliente = cliente or anthropic.AsyncAnthropic(
            api_key=config.anthropic_api_key,
            timeout=float(config.timeout_segundos),
            max_retries=0,
        )

    async def __call__(self, texto: str) -> Factura:
        """Una sola llamada; cualquier problema es `FallaExtraccionIA`, sin volver a llamar."""
        from procfac.ia import FallaExtraccionIA

        try:
            respuesta = await self.cliente.messages.parse(
                model=self._config.modelo,
                max_tokens=self._config.max_tokens,
                system=INSTRUCCIONES,
                output_config={"effort": self._config.esfuerzo},
                output_format=FacturaIA,
                messages=[{"role": "user", "content": texto}],
            )
        # APIConnectionError incluye APITimeoutError (los 60 s).
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as error:
            raise FallaExtraccionIA() from error
        except (pydantic.ValidationError, ValueError) as error:  # salida que no parsea
            raise FallaExtraccionIA() from error
        # `refusal`, `max_tokens` o cualquier otro corte deja la respuesta incompleta.
        if respuesta.stop_reason != "end_turn" or respuesta.parsed_output is None:
            raise FallaExtraccionIA()
        return a_factura(respuesta.parsed_output)

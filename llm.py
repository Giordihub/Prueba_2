"""Cliente compartido para llamadas al modelo de lenguaje."""
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MODEL = os.getenv("MODEL", "claude-opus-5-5")


def get_client() -> anthropic.Anthropic:
    """Usa ANTHROPIC_API_KEY (desde .env o el entorno) o, si no existe,
    el perfil creado con `ant auth login`. Si no hay ninguno, falla con un mensaje claro."""
    try:
        client = anthropic.Anthropic()
        client.models.retrieve(MODEL)  # llamada liviana para validar credenciales
        return client
    except anthropic.AuthenticationError:
        raise SystemExit("La credencial no es válida. Revisa la clave en .env o repite `ant auth login`.")
    except Exception as e:  # sin credencial alguna
        if "api_key" in str(e).lower() or "credential" in str(e).lower():
            raise SystemExit(
                "No hay credenciales. Opción A: pega tu clave en .env (ANTHROPIC_API_KEY=...). "
                "Opción B: instala el CLI con `brew install anthropics/tap/ant` y ejecuta `ant auth login`."
            )
        raise


def check_refusal(response) -> None:
    if response.stop_reason == "refusal":
        detalle = response.stop_details.explanation if response.stop_details else "sin detalle"
        raise RuntimeError(f"El modelo rechazó la solicitud: {detalle}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Respuesta truncada por max_tokens; aumenta el límite.")


def parse_json(client, *, system: str, user: str, modelo, max_tokens: int = 16000, reintentos: int = 2):
    """Pide al modelo un JSON que cumpla el esquema de `modelo` (clase Pydantic) y lo valida.
    Se usa en lugar de messages.parse() porque el esquema clínico completo supera el límite
    de tamaño de la gramática de salidas estructuradas de la API.
    Si la validación falla, reenvía el error al modelo para que corrija (hasta `reintentos` veces)."""
    import json
    from pydantic import ValidationError

    esquema = json.dumps(modelo.model_json_schema(), ensure_ascii=False)
    instrucciones = (
        f"{system}\n\nResponde ÚNICAMENTE con un objeto JSON válido que cumpla exactamente este "
        f"JSON Schema (sin texto antes ni después, sin bloques de código):\n{esquema}"
    )
    messages = [{"role": "user", "content": user}]
    ultimo_error = None
    for _ in range(reintentos + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=instrucciones, messages=messages)
        check_refusal(response)
        texto = "".join(b.text for b in response.content if b.type == "text").strip()
        if texto.startswith("```"):
            texto = texto.strip("`")
            texto = texto[texto.find("{"):texto.rfind("}") + 1]
        try:
            return modelo.model_validate_json(texto)
        except (ValidationError, ValueError) as e:
            ultimo_error = e
            messages += [
                {"role": "assistant", "content": texto},
                {"role": "user", "content": f"El JSON no cumple el esquema. Error:\n{e}\n"
                                            f"Devuelve el JSON corregido completo."},
            ]
    raise RuntimeError(f"No se obtuvo JSON válido tras {reintentos + 1} intentos: {ultimo_error}")

"""Servidor MCP de DaVinci Flow.

Publica las operaciones del producto como herramientas MCP (JSON-RPC 2.0 sobre stdio)
para que cualquier agente pueda operarlo sin conocer la interfaz gráfica:

- estado del transporte y de las credenciales,
- captura de subtítulos y catálogo de plantillas,
- propuesta editorial (siempre **sin aplicar**) y su aplicación revisada,
- inserción de títulos nativos de Resolve (Text+, Fade On, Headline…),
- creación de efectos Fusion editables,
- locución con Minimax y sus subtítulos alineados,
- autocorrector de subtítulos con diff auditable,
- escritura en la pista nativa de subtítulos,
- consulta de la API de scripting de Resolve a través del MCP oficial.

Uso:
    python -m davinci_flow.mcp_server
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from davinci_flow.ai.credentials import has_provider_api_key
from davinci_flow.ai.providers.base import provider_names
from davinci_flow.ai.providers.factory import build_text_provider
from davinci_flow.editorial import resolve_bridge
from davinci_flow.editorial.model import EditorialOptions, Proposal
from davinci_flow.editorial.planner import propose
from davinci_flow.editorial.preferences import Preferences
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.subtitles.autocorrect import SubtitleAutocorrector
from davinci_flow.subtitles.model import SubtitleCue
from davinci_flow.voice.tts import MinimaxSpeechClient, SpeechRequest

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_NAME = "davinci-flow"
SERVER_VERSION = "0.2.0"
VOICE_OUTPUT_DIR = Path.home() / ".davinci_flow" / "voice"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Una herramienta publicada por el servidor."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def _schema(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    """Construye un esquema JSON simple para el parámetro de una herramienta."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def _string(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def _number(description: str, minimum: float | None = None, maximum: float | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "number", "description": description}
    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _integer(description: str, minimum: int | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "integer", "description": description}
    if minimum is not None:
        schema["minimum"] = minimum
    return schema


def _boolean(description: str) -> dict[str, Any]:
    return {"type": "boolean", "description": description}


def _array(description: str, item_type: str = "object") -> dict[str, Any]:
    return {"type": "array", "description": description, "items": {"type": item_type}}


# --------------------------------------------------------------------------- outils


def tool_status(arguments: dict[str, Any]) -> dict[str, Any]:
    """Estado del transporte de Resolve, del proveedor de IA y de las credenciales."""
    preferences = Preferences.load()
    credentials = {name: has_provider_api_key(name) for name in provider_names()}
    status: dict[str, Any] = {
        "proveedor": preferences.provider,
        "modelo": preferences.model,
        "credenciales": credentials,
    }
    try:
        status["resolve"] = resolve_bridge.connection_status()
    except DaVinciFlowError as error:
        status["resolve"] = {"error": str(error)}
    return status


def tool_templates(arguments: dict[str, Any]) -> dict[str, Any]:
    """Catálogo de plantillas de títulos disponible en el Media Pool."""
    templates = resolve_bridge.read_titles()
    return {"plantillas": [asdict(template) for template in templates]}


def tool_capture(arguments: dict[str, Any]) -> dict[str, Any]:
    """Captura los subtítulos de la línea de tiempo activa."""
    snapshot, templates = resolve_bridge.read_resolve(
        track=int(arguments.get("track", 1)),
        first=int(arguments.get("first", 1)),
        last=int(arguments.get("last", 120)),
    )
    data = asdict(snapshot)
    data["cues"] = [asdict(cue) for cue in snapshot.cues]
    data["cuts"] = [list(cut) for cut in getattr(snapshot, "cuts", ())]
    return {"snapshot": data, "plantillas": [asdict(template) for template in templates]}


def tool_propose(arguments: dict[str, Any]) -> dict[str, Any]:
    """Genera una propuesta editorial con el proveedor activo. No escribe nada en Resolve."""
    preferences = Preferences.load()
    snapshot, templates = resolve_bridge.read_resolve(
        track=int(arguments.get("track", 1)),
        first=int(arguments.get("first", 1)),
        last=int(arguments.get("last", 120)),
    )
    requested = arguments.get("templates") or []
    selected = tuple(
        template for template in templates if not requested or template.id in requested
    )
    if not selected:
        return {
            "propuesta": None,
            "aviso": "Ninguna plantilla del catálogo coincide con la selección.",
            "catalogo": [template.id for template in templates],
        }

    options = EditorialOptions(
        str(arguments.get("mode", preferences.mode)),
        str(arguments.get("format", preferences.format)),
        str(arguments.get("density", preferences.density)),
        str(arguments.get("direction", preferences.direction)),
        track_mode=str(arguments.get("track_mode", preferences.track_mode)),
    )
    provider = build_text_provider(preferences.provider, preferences.model)
    result = propose(snapshot, selected, provider, options=options)

    proposal_path = Path(arguments.get("proposal_path") or (Path.home() / ".davinci_flow" / "proposals" / "mcp-proposal.json"))
    result.save(proposal_path)
    return {
        "propuesta": result.to_dict(),
        "ruta": str(proposal_path),
        "estado": "generada; requiere revisión antes de aplicarse",
    }


def tool_apply(arguments: dict[str, Any]) -> dict[str, Any]:
    """Aplica una propuesta ya revisada en la línea de tiempo."""
    if arguments.get("reviewed") is not True:
        return {
            "aplicado": False,
            "aviso": "La propuesta debe marcarse como revisada (reviewed: true) antes de aplicarla.",
        }
    proposal_path = str(arguments.get("proposal_path") or "")
    if not proposal_path:
        return {"aplicado": False, "aviso": "Falta la ruta de la propuesta."}
    proposal = Proposal.load(proposal_path)
    record = resolve_bridge.apply(proposal)
    return {"aplicado": True, "registro": record.to_dict()}


def tool_undo(arguments: dict[str, Any]) -> dict[str, Any]:
    """Deshace la última aplicación registrada."""
    record = resolve_bridge.undo()
    return {"deshecho": True, "registro": record.to_dict()}


def tool_insert_native_title(arguments: dict[str, Any]) -> dict[str, Any]:
    """Inserta un título nativo de Resolve (Text+, Fade On, Headline…) editable."""
    result = resolve_bridge.request(
        "native_title",
        template_name=str(arguments.get("template_name") or "Text+"),
        start_frame=float(arguments.get("start_frame", 0)),
        duration_frames=float(arguments.get("duration_frames", 120)),
        track_index=arguments.get("track_index"),
    )
    return {"insertado": True, "detalle": result}


def tool_create_fusion_effect(arguments: dict[str, Any]) -> dict[str, Any]:
    """Crea un efecto Fusion (Text+ con animación) editable y lo inserta en la línea de tiempo."""
    spec = {
        "text": str(arguments.get("text") or ""),
        "role": str(arguments.get("role") or "main"),
        "animation_preset": str(arguments.get("animation_preset") or "fade_smooth"),
        "position_x": float(arguments.get("position_x", 0.5)),
        "position_y": float(arguments.get("position_y", 0.15)),
        "glow": float(arguments.get("glow", 0.0)),
        "theme": str(arguments.get("theme") or "ely"),
    }
    result = resolve_bridge.request(
        "fusion_effect",
        spec=spec,
        start_frame=float(arguments.get("start_frame", 0)),
        duration_frames=float(arguments.get("duration_frames", 120)),
        track_index=arguments.get("track_index"),
    )
    return {"insertado": True, "detalle": result}


def tool_synthesize_speech(arguments: dict[str, Any]) -> dict[str, Any]:
    """Genera una locución con Minimax y guarda el audio con sus subtítulos alineados."""
    client = MinimaxSpeechClient()
    request = SpeechRequest(
        text=str(arguments.get("text") or ""),
        voice_id=str(arguments.get("voice_id") or "English_Graceful_Lady"),
        model=str(arguments.get("model") or "speech-2.8-hd"),
        speed=float(arguments.get("speed", 1.0)),
        emotion=str(arguments.get("emotion") or ""),
        language_boost=str(arguments.get("language_boost") or "auto"),
        audio_format=str(arguments.get("audio_format") or "wav"),
    )
    output = Path(arguments.get("output_path") or (VOICE_OUTPUT_DIR / "locucion.wav"))
    result, path = client.synthesize_to_file(request, output)
    return {
        "archivo": str(path),
        "duracion_ms": result.duration_ms,
        "voz": result.voice_id,
        "modelo": result.model,
        "subtítulos": [
            {"texto": cue.text, "inicio_ms": cue.start_ms, "fin_ms": cue.end_ms}
            for cue in result.cues
        ],
    }


def tool_autocorrect(arguments: dict[str, Any]) -> dict[str, Any]:
    """Corrige subtítulos y devuelve el diff por etapa."""
    preferences = Preferences.load()
    use_ai = arguments.get("use_ai", True) is not False

    cues: tuple[SubtitleCue, ...]
    if arguments.get("cues"):
        cues = tuple(SubtitleCue(**cue) for cue in arguments["cues"])
    else:
        snapshot, _ = resolve_bridge.read_resolve(
            track=int(arguments.get("track", 1)),
            first=int(arguments.get("first", 1)),
            last=int(arguments.get("last", 120)),
        )
        cues = snapshot.cues

    provider = None
    if use_ai:
        provider = build_text_provider(
            str(arguments.get("provider") or preferences.provider),
            str(arguments.get("model") or preferences.model),
        )

    corrector = SubtitleAutocorrector(provider=provider, glossary=arguments.get("glossary"))
    result = corrector.correct(cues, use_ai=use_ai)
    return {
        "resumen": result.summary(),
        "cambios": [
            {
                "indice": change.index,
                "original": change.original,
                "corregido": change.corrected,
                "etapas": list(change.stages),
            }
            for change in result.changes
            if change.is_modified
        ],
    }


def tool_write_subtitles(arguments: dict[str, Any]) -> dict[str, Any]:
    """Escribe subtítulos en la pista nativa de subtítulos de Resolve."""
    raw_cues = arguments.get("cues")
    if not raw_cues:
        return {"escrito": False, "aviso": "No se recibieron subtítulos."}
    cues = [SubtitleCue(**cue) for cue in raw_cues]
    result = resolve_bridge.request(
        "subtitles",
        cues=[{"text": cue.text, "start_frame": cue.start_frame, "end_frame": cue.end_frame, "track_index": cue.track_index} for cue in cues],
        track_index=arguments.get("track_index"),
        file_name=str(arguments.get("file_name") or "davinci-flow"),
    )
    return {"escrito": True, "detalle": result}


def _official_mcp_call(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Llama a una herramienta del MCP oficial de Resolve."""
    from davinci_flow.resolve.mcp_client import ResolveMCP, find_mcp_executable

    executable = find_mcp_executable()
    if executable is None:
        raise DaVinciFlowError(
            "No se encontró el MCP oficial de Resolve. Instala Resolve Studio 21.1 "
            "o configura DAVINCIFLOW_RESOLVE_MCP."
        )
    with ResolveMCP(executable) as client:
        return client.call_tool(tool, arguments)


def tool_scripting_api_search(arguments: dict[str, Any]) -> dict[str, Any]:
    """Busca en la API de scripting de Resolve (a través del MCP oficial)."""
    pattern = str(arguments.get("pattern") or "")
    if not pattern:
        return {"resultado": None, "aviso": "Falta el patrón de búsqueda."}
    return _official_mcp_call("search_scripting_api", {"pattern": pattern, "api": arguments.get("api", "DaVinciResolveScript.pyi")})


def tool_scripting_docs(arguments: dict[str, Any]) -> dict[str, Any]:
    """Lee la documentación oficial de la API de scripting (a través del MCP oficial)."""
    return _official_mcp_call(
        "get_scripting_docs",
        {"document": arguments.get("document", "README.md"), "section": arguments.get("section", "TOC")},
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="davinciflow_status",
        description="Estado de DaVinci Flow: transporte de Resolve, proveedor de IA activo, modelo y credenciales disponibles.",
        input_schema=_schema({}),
        handler=tool_status,
    ),
    ToolSpec(
        name="davinciflow_capture",
        description="Captura los subtítulos de la línea de tiempo activa de Resolve con sus fotogramas.",
        input_schema=_schema(
            {
                "track": _integer("Pista de subtítulos a leer.", 1),
                "first": _integer("Primer subtítulo a leer.", 1),
                "last": _integer("Último subtítulo a leer.", 1),
            }
        ),
        handler=tool_capture,
    ),
    ToolSpec(
        name="davinciflow_templates",
        description="Catálogo de plantillas de títulos y efectos disponible en el Media Pool de Resolve.",
        input_schema=_schema({}),
        handler=tool_templates,
    ),
    ToolSpec(
        name="davinciflow_propose",
        description="Genera una propuesta editorial con el proveedor de IA activo. No escribe nada: la propuesta queda pendiente de revisión.",
        input_schema=_schema(
            {
                "templates": _array("Identificadores de las plantillas a usar; vacío significa todas."),
                "mode": _string("Modo editorial: highlights o captions."),
                "format": _string("Formato: auto, horizontal o vertical."),
                "density": _string("Densidad editorial."),
                "direction": _string("Dirección del guion."),
                "track_mode": _string("Modo de pistas: single, double o triple."),
                "proposal_path": _string("Ruta donde guardar la propuesta generada."),
            }
        ),
        handler=tool_propose,
    ),
    ToolSpec(
        name="davinciflow_apply",
        description="Aplica en Resolve una propuesta editorial ya revisada.",
        input_schema=_schema(
            {
                "proposal_path": _string("Ruta del archivo de propuesta."),
                "reviewed": _boolean("Debe ser true: confirma que la propuesta fue revisada."),
            },
            required=("proposal_path", "reviewed"),
        ),
        handler=tool_apply,
    ),
    ToolSpec(
        name="davinciflow_undo",
        description="Deshace la última aplicación registrada en la línea de tiempo.",
        input_schema=_schema({}),
        handler=tool_undo,
    ),
    ToolSpec(
        name="davinciflow_insert_native_title",
        description="Inserta un título nativo de Resolve (Text+, Fade On, Headline…) en la línea de tiempo, editable en el Inspector.",
        input_schema=_schema(
            {
                "template_name": _string("Nombre del título nativo, por ejemplo Text+ o Fade On."),
                "start_frame": _number("Fotograma de inicio."),
                "duration_frames": _number("Duración en fotogramas."),
                "track_index": _integer("Pista de vídeo de destino."),
            },
            required=("template_name",),
        ),
        handler=tool_insert_native_title,
    ),
    ToolSpec(
        name="davinciflow_create_fusion_effect",
        description="Genera un efecto Fusion (Text+ con animación y brillo opcional) y lo inserta como composición editable.",
        input_schema=_schema(
            {
                "text": _string("Texto del efecto."),
                "role": _string("Rol tipográfico: main, context o accent."),
                "animation_preset": _string("Animación: none, pop_bounce, slide_up, fade_smooth, kinetic_pulse o typewriter."),
                "position_x": _number("Posición horizontal (0 a 1).", 0.0, 1.0),
                "position_y": _number("Posición vertical (0 a 1).", 0.0, 1.0),
                "glow": _number("Intensidad del brillo (0 a 1).", 0.0, 1.0),
                "theme": _string("Tema de marca: ely o aurora."),
                "start_frame": _number("Fotograma de inicio."),
                "duration_frames": _number("Duración en fotogramas."),
                "track_index": _integer("Pista de vídeo de destino."),
            },
            required=("text",),
        ),
        handler=tool_create_fusion_effect,
    ),
    ToolSpec(
        name="davinciflow_synthesize_speech",
        description="Genera una locución con Minimax, la guarda en disco y devuelve los subtítulos alineados a la voz.",
        input_schema=_schema(
            {
                "text": _string("Texto que se locuta."),
                "voice_id": _string("Identificador de la voz de Minimax."),
                "model": _string("Modelo de voz, por ejemplo speech-2.8-hd."),
                "speed": _number("Velocidad de la voz.", 0.5, 2.0),
                "emotion": _string("Emoción: happy, sad, angry, calm, whisper…"),
                "language_boost": _string("Idioma forzado, por ejemplo Spanish; auto para detección."),
                "output_path": _string("Ruta del archivo de audio de salida."),
            },
            required=("text",),
        ),
        handler=tool_synthesize_speech,
    ),
    ToolSpec(
        name="davinciflow_autocorrect",
        description="Corrige subtítulos con reglas deterministas y con IA, y devuelve el diff por etapa.",
        input_schema=_schema(
            {
                "cues": _array("Subtítulos a corregir; si se omite, se capturan de la línea de tiempo."),
                "use_ai": _boolean("Activa la etapa de corrección con IA."),
                "provider": _string("Proveedor de IA para la corrección."),
                "model": _string("Modelo de IA para la corrección."),
                "glossary": _string("Glosario de términos en formato clave:valor o JSON."),
                "track": _integer("Pista de subtítulos a capturar."),
            }
        ),
        handler=tool_autocorrect,
    ),
    ToolSpec(
        name="davinciflow_write_subtitles",
        description="Escribe subtítulos en la pista nativa de subtítulos de Resolve y devuelve el archivo SRT generado.",
        input_schema=_schema(
            {
                "cues": _array("Subtítulos a escribir, con texto, start_frame, end_frame y track_index."),
                "track_index": _integer("Pista de subtítulos de destino."),
                "file_name": _string("Nombre base del archivo SRT."),
            },
            required=("cues",),
        ),
        handler=tool_write_subtitles,
    ),
    ToolSpec(
        name="davinciflow_scripting_api_search",
        description="Busca en la API de scripting de DaVinci Resolve usando el MCP oficial.",
        input_schema=_schema(
            {
                "pattern": _string("Expresión regular para buscar."),
                "api": _string("Stub a consultar: DaVinciResolveScript.pyi, fusion_api.pyi o ui_api.pyi."),
            },
            required=("pattern",),
        ),
        handler=tool_scripting_api_search,
    ),
    ToolSpec(
        name="davinciflow_scripting_docs",
        description="Lee la documentación oficial de la API de scripting de Resolve usando el MCP oficial.",
        input_schema=_schema(
            {
                "document": _string("Documento: README.md o DCTLReadme.txt."),
                "section": _string("Sección del documento; vacío devuelve todo."),
            }
        ),
        handler=tool_scripting_docs,
    ),
)


class DaVinciFlowMCPServer:
    """Servidor MCP por stdio para DaVinci Flow."""

    def __init__(self, tools: tuple[ToolSpec, ...] = TOOLS) -> None:
        self.tools = {tool.name: tool for tool in tools}

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Atiende un mensaje JSON-RPC; devuelve ``None`` en las notificaciones."""
        method = message.get("method")
        message_id = message.get("id")

        if method == "initialize":
            return self._result(
                message_id,
                {
                    "protocolVersion": self._negotiate_version(message.get("params") or {}),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            )
        if method in {"notifications/initialized", "initialized", "notifications/cancelled"}:
            return None
        if method == "ping":
            return self._result(message_id, {})
        if method == "tools/list":
            return self._result(message_id, {"tools": [tool.describe() for tool in self.tools.values()]})
        if method == "tools/call":
            return self._call_tool(message_id, message.get("params") or {})
        if message_id is None:
            return None
        return self._error(message_id, -32601, f"Método no soportado: {method}")

    def _call_tool(self, message_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta una herramienta y devuelve su contenido o su error."""
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        tool = self.tools.get(name)
        if tool is None:
            return self._error(message_id, -32602, f"Herramienta desconocida: {name}")
        try:
            payload = tool.handler(arguments)
        except DaVinciFlowError as error:
            return self._result(
                message_id,
                {"content": [{"type": "text", "text": str(error)}], "isError": True},
            )
        except Exception as error:  # pragma: no cover - red de seguridad del protocolo
            return self._result(
                message_id,
                {"content": [{"type": "text", "text": f"Error inesperado: {error}"}], "isError": True},
            )
        return self._result(
            message_id,
            {
                "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
                "structuredContent": payload if isinstance(payload, dict) else {"resultado": payload},
                "isError": False,
            },
        )

    @staticmethod
    def _negotiate_version(params: dict[str, Any]) -> str:
        """Elige la versión de protocolo común con el cliente."""
        requested = str(params.get("protocolVersion") or "")
        return requested if requested in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION

    @staticmethod
    def _result(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    @staticmethod
    def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def main() -> None:
    """Atiende el protocolo MCP por entrada y salida estándar."""
    server = DaVinciFlowMCPServer()
    output = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict):
            continue
        response = server.handle(message)
        if response is None:
            continue
        output.write(json.dumps(response, ensure_ascii=False) + "\n")
        output.flush()


if __name__ == "__main__":
    main()

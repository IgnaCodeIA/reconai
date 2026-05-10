from __future__ import annotations

from typing import Any

from ai.query_engine import (
    get_patients_list,
    get_patient_by_name,
    get_patient_sessions,
    get_session_summary,
    get_session_metrics,
    get_patient_evolution,
    get_all_metrics_latest_session,
    compare_sessions,
)
from core.logger import get_logger

log = get_logger("ai.tools")


TOOLS_DEFINITION: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_patients_list",
            "description": (
                "Devuelve la lista completa de pacientes registrados en el sistema, "
                "con su ID, nombre, edad y género. Úsalo cuando el usuario pregunte "
                "cuántos pacientes hay, quiénes están registrados o necesites "
                "localizar el ID de un paciente por nombre."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_by_name",
            "description": (
                "Busca pacientes cuyo nombre contenga el texto dado. "
                "Úsalo cuando el usuario mencione un nombre pero no des por sentado "
                "que conoces el ID exacto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Fragmento del nombre del paciente a buscar. "
                            "Ejemplo: 'María', 'García', 'Juan García'."
                        ),
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_sessions",
            "description": (
                "Devuelve todas las sesiones registradas de un paciente: fecha, "
                "ejercicio realizado, notas y número de métricas. "
                "Úsalo para saber cuántas sesiones tiene un paciente, qué ejercicios "
                "ha hecho o para obtener IDs de sesión concretas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "integer",
                        "description": "ID numérico del paciente.",
                    }
                },
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_session_summary",
            "description": (
                "Devuelve el resumen completo de una sesión: datos del paciente, "
                "ejercicio, fecha y todas las métricas (mínimo, máximo, rango de "
                "ángulos articulares). Úsalo cuando el usuario pida información "
                "detallada sobre una sesión concreta o quiera un resumen clínico."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "integer",
                        "description": "ID numérico de la sesión.",
                    }
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_session_metrics",
            "description": (
                "Devuelve únicamente las métricas (min, max, rango) de una sesión, "
                "sin los datos del paciente. Úsalo cuando ya tienes contexto del "
                "paciente y solo necesitas los valores numéricos de la sesión."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "integer",
                        "description": "ID numérico de la sesión.",
                    }
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_evolution",
            "description": (
                "Devuelve la evolución temporal de una métrica para un paciente, "
                "ordenada cronológicamente. Úsalo para responder preguntas sobre "
                "progreso, mejora o empeoramiento a lo largo del tiempo. "
                "Puedes indicar la métrica exacta (p.ej. 'angle_arm_r_max') "
                "o la serie base (p.ej. 'angle_arm_r') para obtener min, max y rango."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "integer",
                        "description": "ID numérico del paciente.",
                    },
                    "metric_name": {
                        "type": "string",
                        "description": (
                            "Nombre de la métrica o serie a analizar. "
                            "Valores posibles: 'angle_arm_r', 'angle_arm_l', "
                            "'angle_leg_r', 'angle_leg_l', "
                            "'angle_arm_r_min', 'angle_arm_r_max', 'angle_arm_r_range', "
                            "'symmetry_angle_arm', 'symmetry_angle_leg', etc."
                        ),
                    },
                },
                "required": ["patient_id", "metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_metrics_latest_session",
            "description": (
                "Devuelve todas las métricas de la sesión más reciente de un paciente. "
                "Úsalo para dar un resumen del estado actual del paciente sin necesitar "
                "un session_id concreto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "integer",
                        "description": "ID numérico del paciente.",
                    }
                },
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_sessions",
            "description": (
                "Compara las métricas de dos sesiones del mismo paciente, calculando "
                "la diferencia y el porcentaje de cambio. Úsalo cuando el usuario "
                "quiera comparar la primera y la última sesión, o dos sesiones "
                "específicas, para valorar la progresión."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id_a": {
                        "type": "integer",
                        "description": "ID de la sesión de referencia (base, más antigua).",
                    },
                    "session_id_b": {
                        "type": "integer",
                        "description": "ID de la sesión a comparar (más reciente).",
                    },
                },
                "required": ["session_id_a", "session_id_b"],
            },
        },
    },
]


def _wrap(fn):
    def wrapper(**kwargs) -> Any:
        try:
            return fn(**kwargs)
        except TypeError as exc:
            log.error("[tools] Invalid arguments for '%s': %s", fn.__name__, exc)
            return {"error": f"Argumentos inválidos: {exc}"}
        except Exception as exc:
            log.error("[tools] Error executing '%s': %s", fn.__name__, exc)
            return {"error": str(exc)}
    wrapper.__name__ = fn.__name__
    return wrapper


TOOL_REGISTRY: dict[str, Any] = {
    "get_patients_list":             _wrap(get_patients_list),
    "get_patient_by_name":           _wrap(get_patient_by_name),
    "get_patient_sessions":          _wrap(get_patient_sessions),
    "get_session_summary":           _wrap(get_session_summary),
    "get_session_metrics":           _wrap(get_session_metrics),
    "get_patient_evolution":         _wrap(get_patient_evolution),
    "get_all_metrics_latest_session":_wrap(get_all_metrics_latest_session),
    "compare_sessions":              _wrap(compare_sessions),
}


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Dispatch a tool call by name through TOOL_REGISTRY. Returns the function result or {'error': ...}."""
    log.debug("execute_tool called with tool_name=%s, arguments=%s", tool_name, arguments)
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        log.warning("[tools] Unknown tool: '%s'", tool_name)
        return {"error": f"Tool '{tool_name}' no reconocida."}

    log.info("[tools] Executing tool '%s' with args: %s", tool_name, arguments)
    return fn(**arguments)

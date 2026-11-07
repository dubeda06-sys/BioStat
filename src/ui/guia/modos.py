"""Los cuatro modos de uso y su persistencia entre sesiones."""
from enum import Enum

from PyQt6.QtCore import QSettings


class Modo(str, Enum):
    NORMAL = "normal"
    ASISTENTE = "asistente"
    DOCENCIA = "docencia"
    RUEDITAS = "rueditas"


INFO_MODOS = {
    Modo.NORMAL: {
        "nombre": "Normal", "color": "#475569", "suave": "#f1f5f9",
        "lema": "Sin guía: todas las herramientas a mano.",
        "para": "Ya sabés qué prueba querés y cómo leerla.",
    },
    Modo.ASISTENTE: {
        "nombre": "Asistente", "color": "#0e7490", "suave": "#e4f1f5",
        "lema": "Te digo dónde va cada dato y qué falta.",
        "para": "Sabés qué querés averiguar pero no cómo armar la tabla.",
    },
    Modo.DOCENCIA: {
        "nombre": "Docencia", "color": "#7c3aed", "suave": "#f3eefe",
        "lema": "Te explico cada paso y para qué sirve cada prueba.",
        "para": "Querés aprender estadística mientras analizás.",
    },
    Modo.RUEDITAS: {
        "nombre": "Rueditas", "color": "#ea580c", "suave": "#fff1e8",
        "lema": "Preguntas simples, respuestas simples. Sin jerga.",
        "para": "Nunca hiciste estadística y querés una respuesta clara.",
    },
}

_CLAVE = "guia/modo"


def _ajustes():
    return QSettings("BioStat", "BioStat")


def modo_guardado() -> Modo | None:
    """El modo de la última sesión, o None si nunca se eligió."""
    valor = _ajustes().value(_CLAVE, None)
    try:
        return Modo(valor) if valor else None
    except ValueError:
        return None


def guardar_modo(modo: Modo) -> None:
    _ajustes().setValue(_CLAVE, Modo(modo).value)

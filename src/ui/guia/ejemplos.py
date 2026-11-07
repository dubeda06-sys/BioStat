"""Objetivos de análisis en lenguaje llano y datos de ejemplo para cada uno.

Los datos son sintéticos y con semilla fija: el mismo ejemplo da siempre el
mismo resultado, así la explicación que lo acompaña nunca queda desfasada.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Rol:
    """Una columna que el objetivo necesita."""
    clave: str
    pregunta: str          # cómo se le pregunta al usuario
    tipo: str              # "numero" | "categoria"
    ayuda: str


@dataclass(frozen=True)
class Objetivo:
    clave: str
    titulo: str                     # la pregunta, en criollo
    ejemplo: str                    # una situación cotidiana
    tipo_caso: str                  # Caso.tipo del motor que lo responde
    roles: tuple = field(default_factory=tuple)
    como_armar: str = ""            # cómo va la tabla


OBJETIVOS = {
    "grupos": Objetivo(
        clave="grupos",
        titulo="¿Mis grupos son distintos?",
        ejemplo="¿La glucosa es distinta entre los pacientes tratados y los no tratados?",
        tipo_caso="¿Los grupos difieren?",
        roles=(
            Rol("grupo", "¿Qué columna dice a qué grupo pertenece cada caso?", "categoria",
                "Una columna con palabras o códigos: «tratado» / «control», «A» / «B» / «C»."),
            Rol("valor", "¿Qué columna tiene el número que querés comparar?", "numero",
                "Una columna con números: la medición de cada caso."),
        ),
        como_armar=("Una fila por paciente (o muestra). Una columna dice el grupo y otra "
                    "el valor medido. No pongas cada grupo en una columna separada."),
    ),
    "relacion": Objetivo(
        clave="relacion",
        titulo="¿Dos medidas suben y bajan juntas?",
        ejemplo="¿A más edad, más presión arterial?",
        tipo_caso="¿Se mueven juntas?",
        roles=(
            Rol("x", "Primera medida", "numero", "Una columna con números."),
            Rol("y", "Segunda medida", "numero", "Otra columna con números, medida en los mismos casos."),
        ),
        como_armar="Una fila por caso, con las dos medidas de ese caso en la misma fila.",
    ),
    "metodos": Objetivo(
        clave="metodos",
        titulo="¿Dos métodos o equipos dan el mismo resultado?",
        ejemplo="¿El analizador nuevo mide igual que el de referencia?",
        tipo_caso="¿Los dos métodos dan lo mismo?",
        roles=(
            Rol("ref", "Resultado con el método de siempre (referencia)", "numero",
                "Los valores del método conocido."),
            Rol("nuevo", "Resultado con el método nuevo", "numero",
                "Los valores del método que querés validar, de las mismas muestras."),
        ),
        como_armar=("Una fila por muestra. En la misma fila, el resultado de cada método "
                    "para esa muestra. Las dos columnas en la misma unidad."),
    ),
    "asociacion": Objetivo(
        clave="asociacion",
        titulo="¿Dos características van de la mano?",
        ejemplo="¿Fumar se asocia con tener la enfermedad?",
        tipo_caso="¿Las categorías se asocian?",
        roles=(
            Rol("a", "Primera característica", "categoria", "Una columna con categorías (sí/no, A/B…)."),
            Rol("b", "Segunda característica", "categoria", "Otra columna con categorías."),
        ),
        como_armar=("Una fila por persona, con una palabra o código en cada columna. "
                    "No hace falta armar la tabla cruzada: BioStat la cuenta sola."),
    ),
    "describir": Objetivo(
        clave="describir",
        titulo="¿Cómo son mis datos?",
        ejemplo="¿Cuánto da la hemoglobina en promedio y cuánto varía?",
        tipo_caso="Descripción de una variable",
        roles=(Rol("v", "¿Qué columna querés conocer?", "numero", "Una columna con números."),),
        como_armar="Una columna con los valores, uno por fila.",
    ),
}


def dataset(clave: str) -> pd.DataFrame:
    """Datos de ejemplo para un objetivo. Siempre los mismos (semilla fija)."""
    rng = np.random.default_rng(20261107)
    if clave == "grupos":
        n = 30
        return pd.DataFrame({
            "paciente": [f"P{i:03d}" for i in range(1, 2 * n + 1)],
            "tratamiento": ["control"] * n + ["tratado"] * n,
            "glucosa_mg_dl": np.round(np.r_[rng.normal(118, 14, n), rng.normal(102, 13, n)], 1),
        })
    if clave == "relacion":
        n = 45
        edad = rng.integers(25, 80, n)
        return pd.DataFrame({
            "paciente": [f"P{i:03d}" for i in range(1, n + 1)],
            "edad_anios": edad,
            "presion_sistolica": np.round(95 + 0.55 * edad + rng.normal(0, 9, n), 0),
        })
    if clave == "metodos":
        n = 40
        real = rng.uniform(60, 320, n)
        return pd.DataFrame({
            "muestra": [f"M{i:03d}" for i in range(1, n + 1)],
            "glucosa_referencia": np.round(real + rng.normal(0, 4, n), 1),
            "glucosa_equipo_nuevo": np.round(1.02 * real + 2 + rng.normal(0, 5, n), 1),
        })
    if clave == "asociacion":
        n = 160
        fuma = rng.choice(["sí", "no"], n, p=[0.35, 0.65])
        prob = np.where(fuma == "sí", 0.45, 0.18)
        return pd.DataFrame({
            "persona": [f"I{i:03d}" for i in range(1, n + 1)],
            "fuma": fuma,
            "enfermedad": np.where(rng.random(n) < prob, "sí", "no"),
        })
    if clave == "describir":
        n = 50
        return pd.DataFrame({
            "paciente": [f"P{i:03d}" for i in range(1, n + 1)],
            "hemoglobina_g_dl": np.round(rng.normal(13.8, 1.4, n), 1),
        })
    raise KeyError(clave)


# Qué columnas del ejemplo cumplen cada rol (para pre-llenar el asistente).
COLUMNAS_EJEMPLO = {
    "grupos": {"grupo": "tratamiento", "valor": "glucosa_mg_dl"},
    "relacion": {"x": "edad_anios", "y": "presion_sistolica"},
    "metodos": {"ref": "glucosa_referencia", "nuevo": "glucosa_equipo_nuevo"},
    "asociacion": {"a": "fuma", "b": "enfermedad"},
    "describir": {"v": "hemoglobina_g_dl"},
}

"""De la hoja a los arreglos que recibe el core, contando lo que se descarta.

Un análisis pareado compara cada fila consigo misma. El panel limpiaba cada
columna por separado y después las cortaba al mismo largo: con una celda vacía,
desde ahí cada valor se comparaba con el del paciente siguiente
(`tests/test_pares_alineados.py`). Este módulo es el único lugar donde se decide
qué filas entran.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.resultado.modelo import Entrada


def columnas_faltantes(df: pd.DataFrame, *cols) -> str | None:
    """Motivo de rechazo si alguna columna no está en la hoja, o None."""
    faltan = [c for c in dict.fromkeys(cols) if c not in df.columns]
    if not faltan:
        return None
    if len(faltan) == 1:
        return f"La columna «{faltan[0]}» no está en la hoja."
    return "Las columnas " + ", ".join(f"«{c}»" for c in faltan) + " no están en la hoja."


def filas_completas(df: pd.DataFrame, *cols) -> tuple[pd.DataFrame, Entrada]:
    """Las filas con dato en TODAS las columnas pedidas, sin reindexar.

    Devuelve también la `Entrada` con cuántas filas incompletas quedaron afuera:
    las que tenían dato en alguna columna y no en todas. Las filas vacías del
    todo no cuentan, porque son el final de la planilla y no pares rotos; avisar
    por ellas haría que el aviso saliera siempre, y un aviso que sale siempre
    enseña a no leerlo.

    Una columna repetida (el mismo método elegido dos veces) entra una sola vez.
    """
    unicas = list(dict.fromkeys(cols))
    sub = df[unicas]
    presentes = sub.notna()
    descartadas = int((presentes.any(axis=1) & ~presentes.all(axis=1)).sum())
    completas = sub.dropna()
    return completas, Entrada(columnas=tuple(unicas), n=len(completas),
                              descartadas=descartadas)


@dataclass
class Grupos:
    """Una respuesta numérica partida por un código de grupo (formato largo)."""
    etiquetas: list | None
    datos: list | None
    entrada: Entrada | None
    motivo: str | None = None


def grupos(df: pd.DataFrame, respuesta, grupo, max_grupos: int = 20) -> Grupos:
    """Formato largo: una fila por sujeto, la medición y su grupo.

    Rechaza con motivo lo que suele ser un error de uso: la misma columna en los
    dos lugares, texto en la respuesta, un solo grupo, o un «grupo» con tantos
    valores distintos que es una medición.
    """
    falta = columnas_faltantes(df, respuesta, grupo)
    if falta:
        return Grupos(None, None, None, falta)
    if respuesta == grupo:
        return Grupos(None, None, None, "La respuesta y el grupo son la misma columna.")
    pares, entrada = filas_completas(df, respuesta, grupo)
    y = pd.to_numeric(pares[respuesta], errors="coerce")
    if y.isna().any():
        return Grupos(None, None, entrada,
                      f"«{respuesta}» (la respuesta) tiene valores que no son números.")
    partes = [(str(k), g.to_numpy(dtype=float)) for k, g in y.groupby(pares[grupo])]
    k, n = len(partes), len(pares)
    if k < 2:
        return Grupos(None, None, entrada, f"«{grupo}» (el grupo) tiene un solo valor.")
    if k > max_grupos or k > n / 2:
        return Grupos(None, None, entrada,
                      f"«{grupo}» tiene {k} valores distintos para {n} filas: parece una "
                      "medición, no un código de grupo. La primera variable es la respuesta "
                      "y la segunda el grupo (por ejemplo 1, 2, 3 o A, B, C).")
    return Grupos([p[0] for p in partes], [p[1] for p in partes], entrada)


@dataclass
class Columna:
    """Una columna lista para el core: sus números finitos y lo que quedó afuera."""
    valores: np.ndarray | None
    entrada: Entrada | None
    no_finitos: int = 0         # ±∞: se sacan, y el informe lo dice
    motivo: str | None = None   # rechazo: la columna no está o tiene texto


def una(df: pd.DataFrame, col) -> Columna:
    """Los valores numéricos de una columna, sin tirar nada en silencio.

    Las celdas vacías son el final de la planilla o un dato que no se midió, y
    no cuentan. Una celda con texto en una columna de números, en cambio, suele
    ser un error de carga («<0,5», «hemolizada», una coma de más): se rechaza y
    se muestra un ejemplo, en vez de convertirla en vacía y seguir como si nada.
    """
    falta = columnas_faltantes(df, col)
    if falta:
        return Columna(None, None, motivo=falta)
    presentes = df[col].dropna()
    numeros = pd.to_numeric(presentes, errors="coerce")
    texto = presentes[numeros.isna()]
    if len(texto):
        return Columna(None, None, motivo=(
            f"La columna «{col}» tiene {len(texto)} celda(s) que no son números (por "
            f"ejemplo «{texto.iloc[0]}»): corregilas o elegí otra columna."))
    valores = numeros.to_numpy(dtype=float)
    finitos = np.isfinite(valores)
    return Columna(valores[finitos], Entrada(columnas=(col,), n=int(finitos.sum())),
                   no_finitos=int((~finitos).sum()))

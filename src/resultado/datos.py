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


_POSITIVOS = {"1", "1.0", "si", "sí", "s", "positivo", "positiva", "pos", "+", "yes", "y",
              "true", "verdadero", "reactivo", "detectado", "presente", "enfermo", "expuesto",
              "evento", "anormal", "caso"}


def _niveles_binarios(serie, nombre):
    """(positivo, negativo, aviso) de una variable con dos valores, o (None, None, motivo)."""
    valores = list(pd.unique(serie))
    if len(valores) != 2:
        return None, None, (f"«{nombre}» tiene {len(valores)} valor(es) distinto(s); para una "
                            "tabla 2×2 hacen falta exactamente 2 (por ejemplo 0/1).")
    if all(isinstance(v, (int, float, np.integer, np.floating)) for v in valores):
        bajo, alto = sorted(valores, key=float)
        if (float(bajo), float(alto)) == (0.0, 1.0):
            return alto, bajo, ""
        return alto, bajo, (f"«{nombre}» no está codificada 0/1: se tomó {float(alto):g} como "
                            f"positivo y {float(bajo):g} como negativo. Si es al revés, "
                            "recodificá a 0/1.")
    texto = [str(v).strip().lower() for v in valores]
    es_pos = [i for i, t in enumerate(texto) if t in _POSITIVOS]
    if len(es_pos) == 1:
        i = es_pos[0]
        return valores[i], valores[1 - i], ""
    pos, neg = sorted(valores, key=str)
    return pos, neg, (f"No se reconoce cuál valor de «{nombre}» es el positivo: se tomó "
                      f"«{pos}». Si es al revés, recodificá a 0/1.")


@dataclass
class Tabla2x2:
    """a, b / c, d con filas = Variable 1 (positivo arriba), columnas = Variable 2."""
    a: int = 0
    b: int = 0
    c: int = 0
    d: int = 0
    filas: tuple = ()
    columnas: tuple = ()
    lectura: str = ""
    avisos: list | None = None
    entrada: Entrada | None = None
    motivo: str | None = None

    @property
    def celdas(self):
        return self.a, self.b, self.c, self.d


def tabla_2x2(df: pd.DataFrame, c1, c2) -> Tabla2x2:
    """Tabla 2×2 de dos variables binarias, una fila por sujeto.

    Si la selección tiene exactamente 2 filas de conteos enteros que no son
    todos 0/1, se lee como tabla ya armada, y la lectura lo dice (auditoría
    2026-09, K3: antes se tomaban SIEMPRE las dos primeras filas como conteos).
    """
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return Tabla2x2(motivo=falta)
    if c1 == c2:
        return Tabla2x2(motivo="Variable 1 y Variable 2 son la misma columna.")
    pares, entrada = filas_completas(df, c1, c2)
    v1, v2 = pares[c1], pares[c2]
    if len(pares) == 2:
        try:
            cuentas = np.array([[float(v1.iloc[0]), float(v2.iloc[0])],
                                [float(v1.iloc[1]), float(v2.iloc[1])]])
        except (TypeError, ValueError):
            cuentas = None
        if (cuentas is not None and np.all(cuentas >= 0)
                and np.allclose(cuentas, np.round(cuentas))
                and not set(cuentas.ravel()) <= {0.0, 1.0}):
            a, b, c, d = (int(x) for x in cuentas.ravel())
            return Tabla2x2(a, b, c, d, ("fila 1", "fila 2"), (str(c1), str(c2)),
                            f"Se leyó como tabla de conteos ya armada (2 filas): [{a}, {b}] / "
                            f"[{c}, {d}].", [], Entrada((c1, c2), a + b + c + d))
    pos1, neg1, av1 = _niveles_binarios(v1, c1)
    if pos1 is None:
        return Tabla2x2(motivo=av1, entrada=entrada)
    pos2, neg2, av2 = _niveles_binarios(v2, c2)
    if pos2 is None:
        return Tabla2x2(motivo=av2, entrada=entrada)
    a = int(np.sum((v1 == pos1) & (v2 == pos2)))
    b = int(np.sum((v1 == pos1) & (v2 == neg2)))
    c = int(np.sum((v1 == neg1) & (v2 == pos2)))
    d = int(np.sum((v1 == neg1) & (v2 == neg2)))
    return Tabla2x2(a, b, c, d, (f"{c1} = {pos1}", f"{c1} = {neg1}"),
                    (f"{c2} = {pos2}", f"{c2} = {neg2}"),
                    f"Tabla armada con {len(pares)} filas, una por sujeto: filas = «{c1}» "
                    f"({pos1} / {neg1}), columnas = «{c2}» ({pos2} / {neg2}).",
                    [x for x in (av1, av2) if x], entrada)


def tabla_rxc(df: pd.DataFrame, c1, c2, max_niveles: int = 10):
    """(tabla de contingencia, entrada, motivo) de dos variables categóricas."""
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return None, None, falta
    if c1 == c2:
        return None, None, "Variable 1 y Variable 2 son la misma columna."
    pares, entrada = filas_completas(df, c1, c2)
    tabla = pd.crosstab(pares[c1], pares[c2])
    if tabla.shape[0] > max_niveles or tabla.shape[1] > max_niveles:
        return None, entrada, (f"«{c1}» tiene {tabla.shape[0]} categorías y «{c2}» "
                               f"{tabla.shape[1]}: esta prueba es para variables categóricas "
                               f"(hasta {max_niveles} categorías cada una).")
    if tabla.shape[0] < 2 or tabla.shape[1] < 2:
        return None, entrada, "Cada variable necesita al menos 2 categorías con datos."
    return tabla, entrada, None


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

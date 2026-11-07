"""Diagnóstico de la tabla cargada, en lenguaje llano (modo Asistente).

Usa el mismo clasificador de columnas que el Omnianálisis (`tipo_de_columna`),
así lo que el asistente dice de una columna coincide con lo que el motor hará.
No modifica los datos: solo describe y sugiere.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.analysis.omni_analyzer import (
    AMBIGUOUS, BINARY, CATEGORICAL_NOMINAL, CATEGORICAL_ORDINAL, DATETIME,
    NUMERIC_CONTINUOUS, NUMERIC_DISCRETE, tipo_de_columna,
)
from src.ui.guia.ejemplos import OBJETIVOS

_NUMERICOS = {NUMERIC_CONTINUOUS, NUMERIC_DISCRETE}
_CATEGORICOS = {CATEGORICAL_NOMINAL, CATEGORICAL_ORDINAL, BINARY}
_MAX_CATEGORIAS = 20


@dataclass
class Columna:
    nombre: str
    tipo: str                # el del motor
    rol: str                 # numero | categoria | fecha | identificador | vacia | dudosa
    n_validos: int
    n_faltantes: int
    n_unicos: int
    ejemplo: str = ""

    @property
    def rol_llano(self) -> str:
        return {
            "numero": "números", "categoria": "categorías", "fecha": "fechas",
            "identificador": "identificador (no se analiza)", "vacia": "vacía",
            "dudosa": "dudosa",
        }[self.rol]


@dataclass
class Aviso:
    gravedad: str            # error | atencion | ok
    texto: str
    columna: str | None = None


@dataclass
class Diagnostico:
    filas: int
    columnas: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    posibles: dict = field(default_factory=dict)     # objetivo -> {rol: [columnas]}
    formato_ancho: list = field(default_factory=list)  # columnas que parecen grupos

    @property
    def numericas(self):
        return [c.nombre for c in self.columnas if c.rol == "numero"]

    @property
    def categoricas(self):
        return [c.nombre for c in self.columnas if c.rol == "categoria"]

    @property
    def listo(self) -> bool:
        return self.filas > 0 and not any(a.gravedad == "error" for a in self.avisos)


def _es_identificador(s: pd.Series, info: dict) -> bool:
    validos = s.dropna()
    n = len(validos)
    if n < 5 or info["n_unique"] != n:
        return False
    if validos.dtype == object:
        return True
    try:
        v = np.sort(validos.astype(float).to_numpy())
        return bool(np.all(np.diff(v) == 1))  # 1, 2, 3, ... : es un número de orden
    except (TypeError, ValueError):
        return False


def _rol(s: pd.Series, info: dict) -> str:
    tipo = info["tipo"]
    if info["n_valid"] == 0:
        return "vacia"
    if _es_identificador(s, info):
        return "identificador"
    if tipo in _NUMERICOS:
        return "numero"
    if tipo in _CATEGORICOS:
        return "categoria"
    if tipo == DATETIME:
        return "fecha"
    return "dudosa"


def diagnosticar(df: pd.DataFrame | None) -> Diagnostico:
    if df is None or df.empty:
        d = Diagnostico(filas=0)
        d.avisos.append(Aviso("error", "La tabla está vacía. Cargá un archivo o escribí los datos."))
        return d

    d = Diagnostico(filas=len(df))
    for nombre in df.columns:
        s = df[nombre]
        info = tipo_de_columna(s)
        rol = _rol(s, info)
        validos = s.dropna()
        d.columnas.append(Columna(
            nombre=str(nombre), tipo=info["tipo"], rol=rol,
            n_validos=int(info["n_valid"]), n_faltantes=int(len(s) - info["n_valid"]),
            n_unicos=int(info["n_unique"]),
            ejemplo=str(validos.iloc[0]) if len(validos) else ""))
        _avisos_de_columna(d, s, info, rol, str(nombre))

    _avisos_de_tabla(d, df)
    _posibles(d)
    if not d.avisos:
        d.avisos.append(Aviso("ok", "La tabla está bien armada: cada columna es una "
                                    "variable y cada fila un caso."))
    return d


def _avisos_de_columna(d, s, info, rol, nombre):
    n = len(s)
    if rol == "vacia":
        d.avisos.append(Aviso("atencion", f"«{nombre}» está vacía: podés borrarla.", nombre))
        return
    faltan = n - info["n_valid"]
    if n and faltan / n > 0.3:
        d.avisos.append(Aviso("atencion",
                              f"A «{nombre}» le faltan {faltan} de {n} valores "
                              f"({faltan / n:.0%}). Esos casos quedan fuera de los análisis "
                              f"que la usen.", nombre))
    if str(nombre).lower().startswith(("unnamed", "columna ")) or not str(nombre).strip():
        d.avisos.append(Aviso("atencion",
                              f"La columna «{nombre}» no tiene un nombre claro: ponele uno "
                              f"(doble clic en el encabezado).", nombre))
    if rol == "dudosa" and info.get("nota"):
        d.avisos.append(Aviso("atencion", f"«{nombre}»: {info['nota']}", nombre))
    if rol == "categoria":
        conteo = s.dropna().astype(str).value_counts()
        if len(conteo) == 1:
            d.avisos.append(Aviso("atencion",
                                  f"«{nombre}» tiene un solo valor ({conteo.index[0]}): "
                                  f"así no sirve para comparar.", nombre))
        elif len(conteo) > _MAX_CATEGORIAS:
            d.avisos.append(Aviso("atencion",
                                  f"«{nombre}» tiene {len(conteo)} valores distintos. ¿Son "
                                  f"números escritos como texto, o un código por caso?", nombre))
        else:
            solos = [str(k) for k, v in conteo.items() if v == 1]
            if solos:
                lista = ", ".join(f"«{x}»" for x in solos[:3]) + ("…" if len(solos) > 3 else "")
                d.avisos.append(Aviso("atencion",
                                      f"En «{nombre}», {lista} aparece una sola vez: con un "
                                      f"solo caso no se puede comparar ese grupo.", nombre))


def _avisos_de_tabla(d, df):
    ultima = df.iloc[-1].astype(str).str.lower()
    if any(v.strip().startswith(("total", "suma", "promedio")) for v in ultima):
        d.avisos.insert(0, Aviso("error",
                                 "La última fila parece un total o un promedio. Borrala: "
                                 "BioStat calcula esos resúmenes solo y, si la dejás, la "
                                 "cuenta como un caso más."))
    repetidas = [c for c in df.columns if str(c).endswith((".1", ".2"))]
    if repetidas:
        d.avisos.append(Aviso("atencion",
                              "Hay columnas con el mismo nombre (" + ", ".join(map(str, repetidas))
                              + "). Renombralas para no confundirlas."))
    # Formato ancho: varias columnas numéricas y ninguna que diga el grupo.
    num, cat = d.numericas, d.categoricas
    if len(num) >= 2 and not cat:
        d.formato_ancho = list(num)
        d.avisos.append(Aviso("atencion",
                              "Si cada columna numérica es un GRUPO distinto (por ejemplo "
                              "«control» y «tratado»), la tabla está en formato ancho. Para "
                              "comparar grupos, BioStat necesita una columna con el grupo y "
                              "otra con el valor. El asistente puede convertirla. Si en cambio "
                              "son dos medidas del mismo caso, está bien así."))


def _posibles(d):
    num, cat = d.numericas, [c for c in d.categoricas]
    cat_ok = [c.nombre for c in d.columnas
              if c.rol == "categoria" and 2 <= c.n_unicos <= _MAX_CATEGORIAS]
    for clave, obj in OBJETIVOS.items():
        roles = {}
        for rol in obj.roles:
            roles[rol.clave] = list(num) if rol.tipo == "numero" else list(cat_ok)
        necesarios = {"numero": sum(r.tipo == "numero" for r in obj.roles),
                      "categoria": sum(r.tipo == "categoria" for r in obj.roles)}
        if len(num) >= necesarios["numero"] and len(cat_ok) >= necesarios["categoria"]:
            d.posibles[clave] = roles
    _ = cat  # (las categóricas con demasiadas categorías no sirven de grupo)


def a_formato_largo(df: pd.DataFrame, columnas: list[str],
                    nombre_grupo: str = "grupo", nombre_valor: str = "valor") -> pd.DataFrame:
    """Pasa 'un grupo por columna' a 'una columna de grupo y una de valor'.

    Las filas vacías (grupos de distinto tamaño) se descartan: no son casos.
    """
    largo = df[columnas].melt(var_name=nombre_grupo, value_name=nombre_valor)
    return largo.dropna(subset=[nombre_valor]).reset_index(drop=True)

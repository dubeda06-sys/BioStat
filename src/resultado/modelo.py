"""La envoltura `Resultado`: lo que un análisis tiene para decir, sin HTML.

Hoy cada análisis del panel arma su HTML a mano (`src/ui/analysis_methods.py`),
así que el número, la fórmula, la cita y la lectura viven mezclados con el
estilo, y cada rama los escribe a su manera. Acá el análisis devuelve datos y un
solo renderizador decide cómo se ven. Propuesta completa:
`docs/plans/2026-09-26-envoltura-resultado.md`.

Sin Qt ni matplotlib en tiempo de importación: se prueba sin levantar ventana.
"""
from __future__ import annotations

import numbers
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from matplotlib.figure import Figure


@dataclass(frozen=True)
class Cita:
    texto: str          # "Bland JM, Altman DG. Lancet 1986;327:307-310"
    url: str = ""


@dataclass
class Entrada:
    """Con qué datos se corrió."""
    columnas: tuple[str, ...]
    n: int
    descartadas: int = 0   # filas con dato en alguna columna y no en todas


@dataclass
class Valor:
    """Un número del informe, con su intervalo si lo tiene."""
    nombre: str
    valor: Any
    ic: tuple | None = None
    decimales: int = 4
    nota: str = ""
    unidad: str = ""        # "%" se pega al número: 12.34%

    def texto(self) -> str:
        texto = _formatear(self.valor, self.decimales)
        return texto + self.unidad if self.unidad and texto != "—" else texto

    def texto_ic(self) -> str:
        if self.ic is None or len(self.ic) != 2:
            return ""
        return (f"{_formatear(self.ic[0], self.decimales)} a "
                f"{_formatear(self.ic[1], self.decimales)}")


@dataclass
class Metodo:
    """Qué se corrió y por qué ese y no otro."""
    nombre: str
    porque: str = ""


@dataclass
class Supuesto:
    """Una decisión del análisis, contada de forma auditable.

    Mismos campos que `omni_caso.Paso`, a propósito: ese formato ya se probó en
    el Omnianálisis, y el día que migre no hay que traducir nada. Lo que lo hace
    auditable es `alternativa`: sin decir qué habría pasado si el número daba al
    revés, la decisión parece un veredicto en vez de una regla.
    """
    pregunta: str
    medicion: str
    respuesta: str
    consecuencia: str
    alternativa: str = ""
    ok: bool = True


@dataclass(frozen=True)
class Figura:
    """Un gráfico del informe. Se dibuja cuando se lo va a mostrar.

    `dibujar` y no una `Figure` ya hecha: el Resultado se puede construir, y
    probar, sin pagar el costo de dibujar; y cada vista (panel, ventana de
    informe) recibe su propia figura en vez de compartir una.
    """
    titulo: str
    dibujar: Callable[[], Figure]


class ResultadoComoBooleano(TypeError):
    """`if resultado:` sobre un `Resultado`. Hay que preguntar `.ok`."""


@dataclass(eq=False)
class Resultado:
    analisis: str                   # id estable: "bland_altman"
    titulo: str
    entrada: Entrada | None = None
    valores: list[Valor] = field(default_factory=list)
    metodo: Metodo | None = None
    supuestos: list[Supuesto] = field(default_factory=list)
    formula: str = ""
    citas: list[Cita] = field(default_factory=list)
    lectura: str = ""               # qué dice, en castellano llano
    matiz: str = ""                 # qué NO se puede concluir
    advertencias: list[str] = field(default_factory=list)
    figuras: list[Figura] = field(default_factory=list)
    crudo: dict = field(default_factory=dict)
    error: str | None = None
    # Los análisis que corrió un asistente, cada uno con su informe completo:
    # el asistente da el veredicto y las partes muestran de dónde sale.
    partes: list[Resultado] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    def __bool__(self):
        # El core devuelve {"error": motivo} al rechazar, y un dict con una
        # clave es verdadero: `if res:` lo dejaba pasar y reventaba al indexar.
        # Acá ese uso falla la primera vez que corre, no en un informe.
        raise ResultadoComoBooleano(
            "Un Resultado no es verdadero ni falso: preguntá `resultado.ok`.")

    @classmethod
    def rechazo(cls, analisis: str, titulo: str, motivo: str,
                entrada: Entrada | None = None) -> Resultado:
        return cls(analisis=analisis, titulo=titulo, entrada=entrada, error=motivo)

    @classmethod
    def rechazo_del_core(cls, analisis: str, titulo: str, res,
                         entrada: Entrada | None = None) -> Resultado | None:
        """El rechazo que trae la respuesta del core, o None si calculó.

        El core rechaza de dos formas: `None` (las funciones viejas) o
        `{"error": motivo}` (las que pasan por `guards.py`). Se prefiere el
        motivo específico: "Se necesitan al menos 3 pares; hay 2" le dice al
        usuario qué arreglar, "No se pudo calcular" no.
        """
        if res is None:
            return cls.rechazo(analisis, titulo, "El cálculo no devolvió resultado "
                               "con estos datos.", entrada)
        if isinstance(res, dict) and res.get("error"):
            return cls.rechazo(analisis, titulo, str(res["error"]), entrada)
        return None


def _formatear(v, decimales: int) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, str):
        return v
    if isinstance(v, numbers.Integral):   # incluye np.int64: un n no lleva decimales
        return str(int(v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:
        return "—"
    return f"{f:.{decimales}f}"

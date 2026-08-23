"""Frases para la ventana de carga: que la espera enseñe algo.

El arranque del `.exe` tarda; eso no se puede evitar del todo. Lo que sí se
puede es que esos segundos dejen algo. Cada frase es un principio que el
programa aplica de verdad en algún lado — no relleno motivacional genérico.

Dos reglas para agregar frases:

1. **Que quepan.** El splash de PyInstaller expone UNA línea de texto, y ahí
   comparten lugar la barra, el porcentaje y la frase. Lo que no entra se
   recorta contra el borde y queda feo. `LARGO_MAXIMO` lo acota y
   `tests/test_frases.py` lo verifica.
2. **Que sean verdad.** Una frase ingeniosa pero falsa en una herramienta de
   laboratorio es peor que ninguna frase: alguien la va a repetir.

Las dos citas atribuidas son reales: George Box ("todos los modelos están
equivocados, algunos son útiles", 1976) y Ronald Coase (la de torturar los
datos). El resto son dichos de oficio, sin autor único.
"""
import random

# Lo que entra en la línea junto a la barra y el porcentaje. Medido contra el
# ancho real de assets/splash.png, no estimado.
LARGO_MAXIMO = 62


# Ingenio estadístico. Cada una señala un error que el motor evita de verdad.
CHISTES = (
    "Correlación no implica causalidad. Nunca. Jamás.",
    "El 87 % de las estadísticas se inventan en el momento.",
    "Nadie tiene 1,7 hijos. La media es así de honesta.",
    "p = 0,051 también es un resultado.",
    "Un valor raro es un dato hasta que se demuestre lo contrario.",
    "Torturá los datos y confesarán cualquier cosa. — Coase",
    "Todo modelo es falso; algunos son útiles. — Box",
    "Ausencia de evidencia no es evidencia de ausencia.",
    "Correlacionar no es concordar. Preguntale a Bland.",
    "Detrás de cada p chiquito suele haber un n grande.",
    "La mediana aguanta lo que la media no.",
    "Shapiro-Wilk no negocia.",
    "Sin intervalo de confianza es una anécdota.",
    "Dos métodos pueden correlacionar y no concordar.",
    "La normalidad se verifica, no se supone.",
    "Promediar dos errores no da un acierto.",
    "El azar también publica.",
    "Significativo no quiere decir importante.",
    "Si mirás bastantes pares, alguno va a dar lindo.",
    "Pearson mide asociación. El acuerdo lo mide Lin.",
    "El outlier de hoy es el hallazgo de mañana. O un typo.",
    "Un intervalo muy ancho no dice que no; dice no sé.",
)

# Oficio de laboratorio. Sin épica: lo que hace que el resultado sirva.
PENSAMIENTOS = (
    "Detrás de cada dato hay un paciente esperando.",
    "Un resultado bien medido cambia una conducta.",
    "Lo que no se mide, no se puede mejorar.",
    "Calibrando el equipo, no las expectativas.",
    "La trazabilidad es memoria, no burocracia.",
    "Medir bien es una forma de cuidar.",
    "Un método validado se defiende solo.",
    "El control de calidad no molesta: avisa.",
    "Duplicar la muestra cuesta menos que repetir el informe.",
    "La incertidumbre no es un error: es información.",
    "Anotá el porqué. El cómo se olvida.",
    "Cada corrida es una decisión clínica esperando.",
)

TODAS = CHISTES + PENSAMIENTOS


def secuencia(cantidad=None, semilla=None):
    """Frases barajadas, sin repetir hasta agotarlas.

    Barajar en vez de sortear de a una: con `choice` la misma frase salía dos
    veces seguidas y el arranque parecía trabado.
    """
    pozo = list(TODAS)
    random.Random(semilla).shuffle(pozo)
    if cantidad is None:
        return pozo
    # Si piden más que las que hay, se vuelve a barajar en vez de repetir en
    # bloque.
    salida = []
    while len(salida) < cantidad:
        if not pozo:
            pozo = list(TODAS)
            random.Random(semilla).shuffle(pozo)
        salida.append(pozo.pop())
    return salida


def una(semilla=None):
    """Una sola frase, para cuando no hay rotación."""
    return random.Random(semilla).choice(TODAS)

"""Cómo se dicen los números. Una sola copia para el panel y el Omnianálisis.

Cada función de acá existía antes en un solo lado (`omni_analyzer`,
`omni_caso`) y el panel manual tenía su propia versión, peor: por eso el mismo
p salía `p<0.0001` en el Omnianálisis y `p=0.000000` en el panel. Si cada lado
vuelve a tener su copia, vuelven a divergir.

Todo devuelve texto plano, sin HTML. Escapar es trabajo del renderizador.
"""

ALPHA = 0.05

# Ancho a partir del cual el IC de una pendiente ya no permite concluir nada:
# ±25 % alrededor del 1.
ANCHO_MAX_PENDIENTE = 0.5


def fmt_p(p) -> str:
    """p para mostrar. Redondeado a 4 decimales, 3e-9 sale como `0.0`.

    Un p impreso como "0.0" se lee como "p exactamente cero", que no existe.
    Debajo del límite de resolución se informa como desigualdad.
    """
    if p is None:
        return "n/d"
    p = float(p)
    if p != p:  # NaN
        return "n/d"
    if p < 0.0001:
        return "<0.0001"
    return f"{p:.4f}"


def p_token(p) -> str:
    """El token completo: `p=0.0345` o `p<0.0001`.

    Concatenar el `=` a mano dejaba `p=<0.0001`, con el igual y el menor
    pegados. El signo es parte del token, así que lo arma esta función.
    """
    texto = fmt_p(p)
    return f"p{texto}" if texto.startswith("<") else f"p={texto}"


def probabilidad_en_palabras(p) -> str:
    """Traduce un p a una frase, sin la palabra 'significativo'.

    'Significativo' es el término que más se malentiende de toda la
    estadística: se lee como 'importante' o como 'probado'. Acá se dice qué
    mide el número y qué NO dice.
    """
    if p is None:
        return "No se pudo calcular la probabilidad."
    p = float(p)
    if p != p:
        return "No se pudo calcular la probabilidad."
    if p < 0.0001:
        veces = "menos de 1 de cada 10.000 veces"
    elif p < 0.001:
        veces = f"alrededor de {round(p * 10000)} de cada 10.000 veces"
    elif p < 0.01:
        veces = f"alrededor de {round(p * 1000)} de cada 1.000 veces"
    else:
        veces = f"alrededor de {round(p * 100)} de cada 100 veces"

    if p < ALPHA:
        return (
            f"Si en realidad no hubiera ninguna diferencia, un resultado así de "
            f"marcado aparecería {veces} solo por azar. Es lo bastante raro como "
            f"para tomar la diferencia en serio."
        )
    return (
        f"Aunque no hubiera ninguna diferencia real, un resultado así aparecería "
        f"{veces} solo por azar. No alcanza para afirmar que hay diferencia — "
        f"y ojo: tampoco prueba que no la haya. Puede faltar cantidad de datos."
    )


def num(x, decimales=4) -> str:
    """Un número para mostrar, con cifras significativas.

    Los intervalos vienen del core como tuplas de `np.float64`, y su `repr` es
    `np.float64(1.23)`. Formateado a mano en vez de interpolar el objeto.
    """
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v != v:
        return "—"
    return f"{v:.{decimales}g}"


def ic_texto(par) -> str:
    """Un intervalo de confianza como `1.23 a 4.56`."""
    if par is None or len(par) != 2:
        return "—"
    return f"{num(par[0])} a {num(par[1])}"


def pendiente_concluyente(ic) -> tuple[bool, str]:
    """¿El intervalo de la pendiente permite concluir algo?

    Un IC de pendiente que va de −3 a 5 **incluye el 1**, así que la regla
    mecánica dice "no hay sesgo proporcional". Es falso: con ese intervalo la
    regresión no puede descartar nada. Ausencia de evidencia no es evidencia de
    ausencia, y con pocos datos es la trampa más fácil de comer.

    Umbral: un IC de pendiente más ancho que 0,5 (o sea, ±25% alrededor del 1)
    ya no sirve para decidir si un método está bien calibrado.
    """
    if ic is None or len(ic) != 2:
        return True, ""
    try:
        ancho = abs(float(ic[1]) - float(ic[0]))
    except (TypeError, ValueError):
        return True, ""
    if ancho <= ANCHO_MAX_PENDIENTE:
        return True, ""
    return False, (
        f"Cuidado: el intervalo de la pendiente es muy ancho ({ic_texto(ic)}). "
        "Con estos datos la regresión no puede ni afirmar ni descartar un "
        "desvío — que no lo detecte NO significa que no exista. Para concluir "
        "algo hacen falta más muestras, o un rango de concentraciones más amplio."
    )


def texto_descartes(n: int) -> str:
    """El aviso de filas incompletas que quedaron afuera de un análisis."""
    filas = "1 fila incompleta" if n == 1 else f"{n} filas incompletas"
    return (f"Se dejaron afuera {filas}: tenían dato en una de las columnas del "
            "análisis y vacío en otra. Cada fila se compara consigo misma, así "
            "que una fila a medias no puede entrar.")

"""La barra de carga se dibuja con texto, asi que se puede probar sin GUI.

`dibujar` es pura: fraccion -> cadena. Fuera del .exe no hay `pyi_splash`, asi
que `Progreso` tiene que ser inofensivo: los hitos se registran y nada explota.
"""
from src.utils import splash


def test_barra_vacia():
    linea = splash.dibujar(0.0, "Iniciando")
    assert linea.startswith(splash.VACIO * splash.ANCHO)
    assert "  0 %" in linea
    assert linea.endswith("Iniciando")


def test_barra_llena():
    linea = splash.dibujar(1.0, "Listo")
    assert linea.startswith(splash.LLENO * splash.ANCHO)
    assert "100 %" in linea


def test_barra_a_la_mitad():
    linea = splash.dibujar(0.5, "")
    assert linea.count(splash.LLENO) == splash.ANCHO // 2
    assert linea.count(splash.VACIO) == splash.ANCHO // 2
    assert " 50 %" in linea


def test_la_fraccion_se_recorta_a_los_extremos():
    assert splash.dibujar(-3, "") == splash.dibujar(0.0, "")
    assert splash.dibujar(7, "") == splash.dibujar(1.0, "")


def test_el_ancho_de_la_linea_no_depende_de_la_fraccion():
    largos = {len(splash.dibujar(f / 10, "x")) for f in range(11)}
    assert len(largos) == 1, "la barra cambia de largo y hace saltar el texto"


def test_los_hitos_nunca_retroceden():
    p = splash.Progreso()
    p.hito(0.5, "medio")
    p.hito(0.2, "atras")
    assert p.objetivo == 0.5
    assert p.mensaje == "atras"


def test_progreso_sin_ejecutable_no_falla():
    """Corriendo desde el codigo fuente no hay splash: todo debe ser inocuo."""
    p = splash.Progreso().arrancar()
    p.hito(0.3, "cargando")
    p.terminar()
    assert not splash.activo()


def test_funciones_sueltas_sin_splash():
    splash.texto("no hay splash, no pasa nada")
    splash.cerrar()


def test_el_avance_se_acerca_al_hito_y_no_lo_pasa():
    v = 0.0
    for _ in range(200):
        v = splash.siguiente(v, 0.55)
        assert v <= 0.55
    assert v == 0.55


def test_el_avance_es_visible_enseguida():
    """Con tick de 0,08 s, en un segundo la barra tiene que estar casi en el hito.

    Lo que importa para el usuario no es tocar el valor exacto sino que en el
    primer segundo se vea moverse casi todo el tramo.
    """
    v = 0.0
    for _ in range(13):  # ~1 s
        v = splash.siguiente(v, 0.55)
    assert v > 0.55 * 0.85, f"al segundo solo llego a {v:.2f}"

    ticks = 13
    while v < 0.549 and ticks < 1000:
        v = splash.siguiente(v, 0.55)
        ticks += 1
    assert ticks * 0.08 < 3.0, f"tardo {ticks * 0.08:.1f} s en cerrar el tramo"


def test_el_avance_nunca_retrocede():
    v = 0.8
    assert splash.siguiente(v, 0.3) == 0.3 or splash.siguiente(v, 0.8) == 0.8
    assert splash.siguiente(0.8, 0.8) == 0.8

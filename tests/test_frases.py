"""Las frases del splash comparten renglón con la barra: si no entran, se cortan.

Y como las lee gente del laboratorio, una frase ingeniosa pero **falsa** es peor
que ninguna: alguien la va a repetir en un informe.
"""
from src.utils import frases, splash


def test_ninguna_frase_se_pasa_del_largo():
    largas = [(len(f), f) for f in frases.TODAS if len(f) > frases.LARGO_MAXIMO]
    assert largas == [], (
        f"frases que se cortan contra el borde (máx {frases.LARGO_MAXIMO}): {largas}"
    )


def test_el_largo_maximo_entra_en_la_linea_del_splash():
    """El tope de `frases` no puede ser mayor que el que recorta `splash`."""
    assert frases.LARGO_MAXIMO <= splash.MAX_MENSAJE


def test_la_frase_mas_larga_no_se_recorta_al_dibujarla():
    mas_larga = max(frases.TODAS, key=len)
    linea = splash.dibujar(0.5, mas_larga)
    assert mas_larga in linea, "la frase más larga sale con puntos suspensivos"


def test_no_hay_frases_repetidas():
    assert len(set(frases.TODAS)) == len(frases.TODAS)


def test_ninguna_frase_esta_vacia():
    assert all(f.strip() for f in frases.TODAS)


def test_hay_de_los_dos_tipos():
    assert len(frases.CHISTES) >= 10
    assert len(frases.PENSAMIENTOS) >= 6
    assert set(frases.TODAS) == set(frases.CHISTES) | set(frases.PENSAMIENTOS)


def test_la_secuencia_no_repite_hasta_agotar_el_pozo():
    seq = frases.secuencia(len(frases.TODAS), semilla=1)
    assert len(set(seq)) == len(frases.TODAS)


def test_la_secuencia_sirve_aunque_pidan_de_mas():
    seq = frases.secuencia(len(frases.TODAS) + 5, semilla=1)
    assert len(seq) == len(frases.TODAS) + 5


def test_la_semilla_hace_reproducible_el_orden():
    assert frases.secuencia(8, semilla=42) == frases.secuencia(8, semilla=42)


def test_una_devuelve_algo_del_pozo():
    assert frases.una(semilla=3) in frases.TODAS


# ---------------- Rotación en el splash ----------------

def test_despues_de_un_hito_manda_el_nombre_de_la_etapa():
    """Si el arranque se cuelga, la etapa es la única pista de dónde quedó."""
    p = splash.Progreso(semilla_frases=0)
    p.hito(0.5, "Cargando modulos")
    assert p.acompanamiento(ahora=p._t_hito + 0.1) == "Cargando modulos"


def test_pasado_el_momento_de_la_etapa_entran_las_frases():
    p = splash.Progreso(semilla_frases=0)
    p.hito(0.5, "Cargando modulos")
    texto = p.acompanamiento(ahora=p._t_hito + splash.MOSTRAR_ETAPA + 0.1)
    assert texto in frases.TODAS


def test_la_frase_rota_con_el_tiempo():
    p = splash.Progreso(semilla_frases=0)
    base = 1000.0
    vistas = []
    for i in range(6):
        vistas.append(p.acompanamiento(ahora=base + i * splash.ROTACION))
    assert len(set(vistas)) > 1, "la frase quedó congelada"


def test_la_frase_no_cambia_en_cada_tick():
    """Con tick de 0,08 s, cambiar en cada uno sería un parpadeo ilegible."""
    p = splash.Progreso(semilla_frases=0)
    base = 1000.0
    vistas = [p.acompanamiento(ahora=base + i * 0.08) for i in range(10)]
    assert len(set(vistas)) == 1, f"cambió {len(set(vistas))} veces en menos de 1 s"

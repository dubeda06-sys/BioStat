"""Genera assets/splash.png, la ventana de carga del ejecutable.

Uso:
    python scripts/make_splash.py

El PNG NO se versiona: lleva el commit dibujado, asi que build_exe.py lo
regenera en cada compilacion. Correr este script a mano solo hace falta para
ver como quedo un cambio de diseno sin compilar todo. Paleta tomada de src/ui/styles.py.

El ancho manda: en la unica linea de texto que expone el splash de PyInstaller
conviven la barra, el porcentaje y la frase que rota (src/utils/frases.py).
Con los 520 px de antes la frase entraba recortada, asi que la ventana pasa a
700 px y la linea de estado arranca mas a la izquierda.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import __version__          # noqa: E402
from src.version import info         # noqa: E402

W, H = 700, 330

# La linea de texto la dibuja Tk, no este script: aca solo se reserva el lugar.
# Tiene que coincidir con text_pos en biostat.spec.
TEXTO_X, TEXTO_Y = 34, 246

SURFACE = "#ffffff"
BORDER = "#e2e8f0"
INK = "#1e293b"
MUTED = "#64748b"
PRIMARY = "#0e7490"
PRIMARY_SOFT = "#e0f2f1"
BANDA = "#f8fafc"


def _font(name, size):
    """Carga una fuente de Windows; si no esta, cae a la por defecto."""
    for candidate in (name, os.path.join(r"C:\Windows\Fonts", name)):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build():
    img = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(img)

    # Marco y franja de acento superior.
    d.rectangle([0, 0, W - 1, H - 1], outline=BORDER, width=1)
    d.rectangle([0, 0, W, 5], fill=PRIMARY)

    # Glifo: barras tipo grafico de control con su linea de media.
    gx, gy, gw, gh = 40, 58, 96, 76
    d.rectangle([gx, gy, gx + gw, gy + gh], fill=PRIMARY_SOFT)
    alturas = [0.45, 0.70, 0.35, 0.85, 0.55]
    ancho_barra = 12
    sep = (gw - len(alturas) * ancho_barra) // (len(alturas) + 1)
    for i, frac in enumerate(alturas):
        x0 = gx + sep + i * (ancho_barra + sep)
        alto = int(gh * frac)
        d.rectangle([x0, gy + gh - alto, x0 + ancho_barra, gy + gh], fill=PRIMARY)
    d.line([gx, gy + int(gh * 0.42), gx + gw, gy + int(gh * 0.42)],
           fill=INK, width=1)

    # Titulo y bajada.
    d.text((158, 58), "BioStat", font=_font("segoeuib.ttf", 48), fill=INK)
    d.text((161, 121), "Software estadistico para laboratorio clinico",
           font=_font("segoeui.ttf", 14), fill=MUTED)

    # Identidad de la compilacion, arriba a la derecha. Se HORNEA en el PNG en
    # vez de escribirse en la linea de estado porque esa linea es una sola y la
    # ocupa la barra de progreso. Asi ademas queda visible los ~16 s enteros.
    #
    # La fecha y el commit son el dato util, no el semantico: lo que hay que
    # poder contestar mirando la pantalla es "¿este es el build actual?", y
    # `v0.1.0` no lo contesta. Ver src/version.py.
    v = info()
    d.text((W - 34, 62), f"v{__version__}", anchor="ra",
           font=_font("segoeuib.ttf", 17), fill=PRIMARY)
    if v["commit"] != "desconocido":
        detalle = f"{v['fecha']} · {v['commit']}"
        if v["rama"] not in ("desconocido", "HEAD"):
            detalle = f"{v['fecha']} · {v['rama']} · {v['commit']}"
        d.text((W - 34, 88), detalle, anchor="ra",
               font=_font("segoeui.ttf", 12), fill=MUTED)
        if v["sucio"]:
            # Un build con cambios sin commitear no es reproducible desde su
            # hash. Decirlo en la pantalla evita que alguien cite ese commit
            # como si describiera lo que corrio.
            d.text((W - 34, 106), "cambios sin commitear", anchor="ra",
                   font=_font("segoeui.ttf", 11), fill="#b45309")
    else:
        d.text((W - 34, 88), "sin datos de compilacion", anchor="ra",
               font=_font("segoeui.ttf", 12), fill=MUTED)

    # Banda de estado: da contraste a la linea que escribe Tk encima, para que
    # la frase no quede flotando sobre el blanco.
    d.rectangle([1, 216, W - 2, 282], fill=BANDA)
    d.line([1, 216, W - 2, 216], fill=BORDER, width=1)
    d.line([1, 282, W - 2, 282], fill=BORDER, width=1)

    # Nota al pie: explica por que la primera apertura tarda.
    d.text((34, 294),
           "La primera apertura descomprime la aplicacion (~150 MB). "
           "Puede tardar unos segundos.",
           font=_font("segoeui.ttf", 12), fill=MUTED)

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "splash.png")
    img.save(out)
    print(f"Escrito: {out}  ({W}x{H})")
    return out


if __name__ == "__main__":
    sys.exit(0 if build() else 1)

"""El único renderizador de `Resultado` a HTML.

Lo primero es lo que se viene a buscar: cómo se lee el resultado y qué no se
puede concluir, y enseguida las advertencias que lo condicionan. Después los
números, el método, lo que se verificó, la fórmula y las referencias. Antes el
orden era el del cálculo: quince filas de números arriba y la lectura en
castellano abajo, fuera de la vista en el recuadro del panel (27 sep).

Lo dibuja `QTextEdit`, que entiende un subconjunto de HTML: un `div` no toma
`padding` ni bordes, así que los recuadros de antes se veían como texto pegado
a un fondo. Acá cada recuadro es una tabla de una fila: una celda angosta de
color hace de filete y la otra lleva el texto con su margen. Se ve igual en el
panel, al imprimir y en el navegador (Guardar como HTML).

Los colores son los del tema (`src/ui/styles.py`): el acento teal para lo que
se lee primero, ámbar para lo que condiciona el resultado, verde y ámbar para
cada supuesto según se cumplió o no.

Todo texto que viene del `Resultado` se escapa: los nombres de columna los
escribe el usuario, y una columna llamada `<b>` no puede romper el informe.
"""
from __future__ import annotations

from html import escape

from src.resultado.lenguaje import texto_descartes
from src.resultado.modelo import Resultado

_ACENTO = "#0e7490"
_TINTA = "#1a1a1a"
_GRIS = "#5b6573"
_CEBRA = "#f4f7f9"
_MONO = "Consolas, 'Cascadia Mono', monospace"

# (filete, fondo) de cada clase de recuadro.
_TONOS = {
    "lectura": (_ACENTO, "#edf6f8"),
    "atencion": ("#c27803", "#fdf6e7"),
    "ok": ("#15803d", "#f0f8f2"),
    "rechazo": ("#b42318", "#fdf1f0"),
    "formula": ("#b8c2cc", "#f6f8fa"),
}


def _recuadro(contenido: str, tono: str, arriba: int = 8) -> str:
    filete, fondo = _TONOS[tono]
    return (f"<table width='100%' cellspacing='0' cellpadding='0' "
            f"style='margin-top:{arriba}px;'><tr>"
            f"<td width='3' style='background-color:{filete};'></td>"
            f"<td style='background-color:{fondo};padding:7px 10px;'>{contenido}</td>"
            f"</tr></table>")


def _seccion(titulo: str) -> str:
    return (f"<p style='margin:16px 0 5px 0;font-weight:700;color:{_ACENTO};'>"
            f"{titulo}</p>")


def _encabezado(res: Resultado, parte: bool) -> str:
    tamano = 13 if parte else 16
    h = (f"<p style='margin:0;font-size:{tamano}px;font-weight:700;color:{_TINTA};'>"
         f"{escape(res.titulo)}</p>")
    e = res.entrada
    if e is not None:
        cols = ", ".join(escape(c) for c in e.columnas)
        h += f"<p style='margin:2px 0 0 0;color:{_GRIS};'>n = {e.n} · {cols}</p>"
    return h


def _conclusion(res: Resultado) -> str:
    h = ""
    if res.lectura:
        h += (f"<p style='margin:0 0 3px 0;font-weight:700;color:{_ACENTO};'>Cómo se lee</p>"
              f"<p style='margin:0;font-size:13px;color:{_TINTA};'>{escape(res.lectura)}</p>")
    if res.matiz:
        h += (f"<p style='margin:{6 if h else 0}px 0 0 0;color:{_GRIS};'>"
              f"<b>Qué NO se puede concluir.</b> {escape(res.matiz)}</p>")
    return _recuadro(h, "lectura", 12) if h else ""


def _advertencias(res: Resultado) -> str:
    return "".join(_recuadro(f"<b>Atención:</b> {escape(a)}", "atencion", 6)
                   for a in res.advertencias)


def _descartes(res: Resultado) -> str:
    if res.entrada is None or not res.entrada.descartadas:
        return ""
    return _recuadro(escape(texto_descartes(res.entrada.descartadas)), "atencion", 6)


def _valores(res: Resultado) -> str:
    if not res.valores:
        return ""
    filas = []
    for i, v in enumerate(res.valores):
        celda = f"<b>{escape(v.texto())}</b>"
        ic = v.texto_ic()
        if ic:
            celda += (f"&nbsp;&nbsp;<span style='color:{_GRIS};'>"
                      f"IC {escape(v.nivel_ic)}: {escape(ic)}</span>")
        if v.nota:
            celda += (f"<br><span style='color:{_GRIS};font-style:italic;'>"
                      f"{escape(v.nota)}</span>")
        fondo = f"background-color:{_CEBRA};" if i % 2 else ""
        filas.append(f"<tr style='{fondo}'>"
                     f"<td style='padding:3px 16px 3px 6px;color:{_GRIS};'>{escape(v.nombre)}</td>"
                     f"<td style='padding:3px 6px;'>{celda}</td></tr>")
    return (_seccion("Resultados")
            + f"<table cellspacing='0' cellpadding='0'>{''.join(filas)}</table>")


def _metodo(res: Resultado) -> str:
    m = res.metodo
    if m is None:
        return ""
    texto = f"<b>{escape(m.nombre)}.</b>"
    if m.porque:
        texto += f" {escape(m.porque)}"
    return _seccion("Método") + f"<p style='margin:0;'>{texto}</p>"


def _supuestos(res: Resultado) -> str:
    if not res.supuestos:
        return ""
    h = _seccion("Qué se verificó y qué se decidió")
    for i, s in enumerate(res.supuestos):
        tono = "ok" if s.ok else "atencion"
        color = _TONOS[tono][0]
        texto = (f"<b>{escape(s.pregunta)}</b> {escape(s.medicion)} → "
                 f"<b style='color:{color};'>{escape(s.respuesta)}</b><br>"
                 f"{escape(s.consecuencia)}")
        if s.alternativa:
            texto += (f"<br><span style='color:{_GRIS};font-style:italic;'>"
                      f"Si hubiera dado al revés: {escape(s.alternativa)}</span>")
        h += _recuadro(texto, tono, 0 if i == 0 else 6)
    return h


def _formula(res: Resultado) -> str:
    if not res.formula:
        return ""
    cuerpo = escape(res.formula).replace("\n", "<br>")
    return (_seccion("Fórmula")
            + _recuadro(f"<span style='font-family:{_MONO};color:{_TINTA};'>{cuerpo}</span>",
                        "formula", 0))


def _citas(res: Resultado) -> str:
    if not res.citas:
        return ""
    items = []
    for c in res.citas:
        texto = escape(c.texto)
        if c.url:
            texto = f"<a href='{escape(c.url, quote=True)}' style='color:{_ACENTO};'>{texto}</a>"
        items.append(f"<li>{texto}</li>")
    return (_seccion("Referencias")
            + f"<ul style='margin:0;font-size:11px;color:{_GRIS};'>{''.join(items)}</ul>")


def _partes(res: Resultado) -> str:
    """Cada análisis que corrió el asistente, con su informe entero debajo."""
    if not res.partes:
        return ""
    h = _seccion("De dónde sale: el informe de cada análisis")
    for parte in res.partes:
        h += "<hr>" + _informe(parte, parte=True)
    return h


def _informe(res: Resultado, parte: bool) -> str:
    h = _encabezado(res, parte)
    if not res.ok:
        return (h + _recuadro(f"<b>No se puede calcular:</b> {escape(res.error)}", "rechazo", 10)
                + _descartes(res))
    return (h + _conclusion(res) + _advertencias(res) + _descartes(res)
            + _valores(res) + _metodo(res) + _supuestos(res)
            + _formula(res) + _citas(res) + _partes(res))


def render_html(res: Resultado) -> str:
    """El informe completo. Un rechazo muestra el motivo del core, nada más."""
    return _informe(res, parte=False)

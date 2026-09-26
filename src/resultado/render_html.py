"""El único renderizador de `Resultado` a HTML.

Reproduce el estilo que ya tenía el panel (`_h`, `_r` y los recuadros de
color de `analysis_methods`) para que un análisis migrado no se note distinto
de uno viejo. Rediseñar el informe es otra discusión.

Todo texto que viene del `Resultado` se escapa: los nombres de columna los
escribe el usuario, y una columna llamada `<b>` no puede romper el informe.
"""
from __future__ import annotations

from html import escape

from src.resultado.lenguaje import texto_descartes
from src.resultado.modelo import Resultado

_AZUL = "#4f6ef7"
_TINTA = "#2c3650"
_GRIS = "#8892a4"


def _recuadro(contenido: str, fondo: str, borde: str) -> str:
    return (f"<div style='margin-top:8px;padding:8px 10px;border-radius:6px;"
            f"background:{fondo};border-left:3px solid {borde};font-size:12px;'>"
            f"{contenido}</div>")


def _info(contenido):
    return _recuadro(contenido, "#f0f9fb", "#0e7490")


def _atencion(contenido):
    return _recuadro(contenido, "#fdf6ec", "#d97706")


def _encabezado(titulo: str) -> str:
    return (f"<div style='border-bottom:2px solid {_AZUL};padding-bottom:5px;"
            f"margin-bottom:10px;'><b style='color:{_TINTA};font-size:14px;'>"
            f"{escape(titulo)}</b></div>")


def _fila(rotulo: str, valor: str) -> str:
    return (f"<tr><td style='padding:2px 12px 2px 0;color:{_GRIS};'>{rotulo}</td>"
            f"<td style='padding:2px 0;font-weight:600;'>{valor}</td></tr>")


def _entrada(res: Resultado) -> str:
    e = res.entrada
    if e is None:
        return ""
    cols = ", ".join(escape(c) for c in e.columnas)
    return (f"<div style='font-size:12px;color:{_GRIS};margin-bottom:6px;'>"
            f"n = {e.n} · {cols}</div>")


def _descartes(res: Resultado) -> str:
    if res.entrada is None or not res.entrada.descartadas:
        return ""
    return _atencion(escape(texto_descartes(res.entrada.descartadas)))


def _valores(res: Resultado) -> str:
    if not res.valores:
        return ""
    h = "<table style='font-size:12px;'>"
    for v in res.valores:
        celda = escape(v.texto())
        ic = v.texto_ic()
        if ic:
            celda += f" <span style='font-weight:400;color:{_GRIS};'>(IC 95 %: {escape(ic)})</span>"
        if v.nota:
            celda += f" <span style='font-weight:400;font-style:italic;'>{escape(v.nota)}</span>"
        h += _fila(escape(v.nombre), celda)
    return h + "</table>"


def _metodo(res: Resultado) -> str:
    m = res.metodo
    if m is None:
        return ""
    texto = f"<b>Método:</b> {escape(m.nombre)}."
    if m.porque:
        texto += f" {escape(m.porque)}"
    return _info(texto)


def _supuestos(res: Resultado) -> str:
    if not res.supuestos:
        return ""
    h = "<div style='margin-top:10px;font-size:12px;'><b>Qué se verificó y qué se decidió</b>"
    for s in res.supuestos:
        color = "#16a34a" if s.ok else "#d97706"
        h += (f"<div style='margin-top:6px;padding-left:8px;border-left:3px solid {color};'>"
              f"<b>{escape(s.pregunta)}</b> {escape(s.medicion)} → "
              f"<b style='color:{color};'>{escape(s.respuesta)}</b><br>"
              f"{escape(s.consecuencia)}")
        if s.alternativa:
            h += f"<br><i>Si hubiera dado al revés: {escape(s.alternativa)}</i>"
        h += "</div>"
    return h + "</div>"


def _lectura(res: Resultado) -> str:
    h = ""
    if res.lectura:
        h += _atencion(f"<b>Cómo se lee.</b> {escape(res.lectura)}")
    if res.matiz:
        h += _info(f"<b>Qué NO se puede concluir.</b> {escape(res.matiz)}")
    return h


def _advertencias(res: Resultado) -> str:
    return "".join(_atencion(f"<b>Atención:</b> {escape(a)}") for a in res.advertencias)


def _formula(res: Resultado) -> str:
    if not res.formula:
        return ""
    cuerpo = escape(res.formula).replace("\n", "<br>")
    return (f"<div style='margin-top:10px;font-size:12px;'><b>Fórmula</b><br>"
            f"<span style='font-family:Consolas,monospace;color:{_AZUL};'>{cuerpo}</span></div>")


def _citas(res: Resultado) -> str:
    if not res.citas:
        return ""
    items = []
    for c in res.citas:
        texto = escape(c.texto)
        if c.url:
            texto = f"<a href='{escape(c.url, quote=True)}'>{texto}</a>"
        items.append(f"<li>{texto}</li>")
    return (f"<div style='margin-top:10px;font-size:11px;color:{_GRIS};'><b>Referencias</b>"
            f"<ul style='margin:2px 0 0 0;'>{''.join(items)}</ul></div>")


def render_html(res: Resultado) -> str:
    """El informe completo. Un rechazo muestra el motivo del core, nada más."""
    h = _encabezado(res.titulo)
    if not res.ok:
        h += f"<b>No se puede calcular:</b> {escape(res.error)}"
        return h + _descartes(res)
    return (h + _entrada(res) + _valores(res) + _metodo(res) + _supuestos(res)
            + _lectura(res) + _advertencias(res) + _descartes(res)
            + _formula(res) + _citas(res))

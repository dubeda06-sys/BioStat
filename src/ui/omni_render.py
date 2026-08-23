"""Texto didáctico del Omnianálisis: el resumen en castellano llano.

El informe técnico ya existe y está bien, pero abre con una tabla de tipos de
columna. Quien audita necesita antes tres respuestas: qué se analizó, qué
decidió el motor, y qué encontró. Eso arma este módulo.

Separado del panel a propósito: `omni_panel` es cableado de Qt; el texto que
lee una persona se escribe y se revisa acá.
"""
from src.analysis.omni_analyzer import _p
from src.analysis.omni_auditoria import DESCARTADO, EJECUTADO, NO_APLICA

CSS_RESUMEN = """
<style>
body{font-family:'Segoe UI',sans-serif;color:#1e293b;font-size:13px;}
h2{color:#0e7490;font-size:15px;margin:14px 0 6px;border-bottom:1px solid #cbd5e1;padding-bottom:3px;}
p{margin:5px 0;line-height:1.45;}
.tarjetas{margin:8px 0;}
.n{font-size:20px;font-weight:bold;color:#0e7490;}
.rotulo{color:#64748b;font-size:11px;}
ul{margin:4px 0 4px 18px;padding:0;}
li{margin:3px 0;line-height:1.4;}
.sig{color:#15803d;font-weight:bold;}
.nosig{color:#64748b;}
.aviso{background:#fef3c7;border-left:4px solid #d97706;padding:6px 10px;margin:5px 0;border-radius:0 4px 4px 0;}
.nota{color:#64748b;font-size:12px;font-style:italic;}
table{border-collapse:collapse;width:100%;margin:6px 0;font-size:12px;}
th{background:#e0f2fe;color:#0c4a6e;padding:4px 8px;text-align:left;border-bottom:1px solid #7dd3fc;}
td{padding:4px 8px;border-bottom:1px solid #e2e8f0;vertical-align:top;}
</style>
"""

_RAMAS = {
    "A": ("Rama A — una sola columna",
          "Con una variable no hay asociaciones posibles: el motor la describe "
          "y decide, según su distribución, si el resumen honesto es media o "
          "mediana."),
    "B": ("Rama B — dos columnas",
          "Describe cada variable y además las cruza. La combinación de tipos "
          "elige la prueba; no hay criterio discrecional."),
    "C": ("Rama C — tres o más columnas",
          "Describe cada variable, cruza todos los pares y agrega lo que solo "
          "tiene sentido con varias a la vez. Con muchas comparaciones a la vez "
          "aparecen significativos por azar, así que la corrección por "
          "multiplicidad es obligatoria."),
}


def _tarjetas(auditoria):
    r = auditoria.get("resumen") or {}
    if not r:
        return ""
    celdas = [
        (r.get("ejecuciones", 0), "ensayos ejecutados"),
        (r.get("tipos_ejecutados", 0), f"tipos distintos (de {r.get('catalogo', 0)})"),
        (r.get("tipos_descartados", 0), "descartados con motivo"),
        (r.get("bloques", 0), "bloques de informe"),
    ]
    h = "<table class='tarjetas'><tr>"
    for n, rotulo in celdas:
        h += (f"<td style='border:none;text-align:center;'>"
              f"<div class='n'>{n}</div><div class='rotulo'>{rotulo}</div></td>")
    return h + "</tr></table>"


def _hallazgos(report):
    """Lo significativo y lo concluyente, sin la aritmética intermedia."""
    sig, no_sig = [], 0
    for b in report.get("blocks", []) or []:
        titulo = b.get("titulo", "")
        for pr in b.get("pruebas", []) or []:
            if pr.get("significativo"):
                # `_p` evita el "p=0.0" que se lee como p exactamente cero.
                sig.append(f"<b>{titulo}</b> — {pr['prueba']}: {_p(pr.get('p'))}")
            else:
                no_sig += 1

    h = ""
    if sig:
        h += "<p>Diferencias o asociaciones <span class='sig'>significativas</span>:</p><ul>"
        for s in sig:
            h += f"<li>{s}</li>"
        h += "</ul>"
    if no_sig:
        h += (f"<p class='nota'>Otras {no_sig} prueba(s) no dieron significativas. "
              "No significativo no es lo mismo que \"no hay efecto\": puede ser "
              "falta de n.</p>")
    if not sig and not no_sig:
        h += "<p class='nota'>No se corrieron pruebas de hipótesis en esta corrida.</p>"
    return h


def _concordancias(report):
    bloques = [b for b in (report.get("blocks") or []) if b.get("tipo") == "concordancia"]
    if not bloques:
        return ""
    h = "<h2>Comparación de métodos</h2>"
    for b in bloques:
        res = b.get("resultados", {})
        ba = res.get("bland_altman", {})
        sesgo = ba.get("sesgo", ba.get("sesgo_mediana"))
        reg = res.get("regresion", {})
        h += f"<p><b>{b.get('titulo','')}</b></p><ul>"
        h += (f"<li>Sesgo ({ba.get('tipo','?')}): <b>{sesgo}</b>. "
              f"Estructura de la diferencia: {res.get('estructura_diferencia','?')}.</li>")
        if res.get("ccc") is not None:
            h += (f"<li>Acuerdo (CCC de Lin): <b>{res['ccc']}</b>"
                  + (f" — {res['ccc_fuerza']}" if res.get("ccc_fuerza") else "")
                  + ". Es acuerdo, no correlación.</li>")
        if reg:
            h += (f"<li>{reg.get('metodo','Regresión')}: pendiente "
                  f"{reg.get('pendiente')}, intercepto {reg.get('intercepto')} → "
                  f"sesgo proporcional: <b>{'sí' if reg.get('sesgo_proporcional') else 'no'}</b>, "
                  f"sesgo constante: <b>{'sí' if reg.get('sesgo_constante') else 'no'}</b>.</li>")
        h += "</ul>"
    return h


def _por_que_no(auditoria, maximo=8):
    """Las decisiones de NO correr algo, que es lo que un auditor pregunta."""
    descartados = (auditoria.get("por_estado") or {}).get(DESCARTADO, [])
    if not descartados:
        return ""
    h = ("<h2>Qué no se corrió, y por qué</h2>"
         "<p class='nota'>Descartar no es una falla: es el motor eligiendo la "
         "rama correcta. Estas son las decisiones, con su motivo.</p>"
         "<table><tr><th>Ensayo</th><th>Motivo</th></tr>")
    for f in descartados[:maximo]:
        motivo = f["motivos"][0] if f["motivos"] else "—"
        h += f"<tr><td>{f['nombre']}</td><td>{motivo}</td></tr>"
    h += "</table>"
    if len(descartados) > maximo:
        h += (f"<p class='nota'>… y {len(descartados) - maximo} más. "
              "La lista completa está en la pestaña Auditoría.</p>")
    return h


def resumen_html(report: dict, auditoria: dict) -> str:
    """El texto de la pestaña Resumen."""
    if not report or "error" in (report or {}):
        return (CSS_RESUMEN +
                f"<p style='color:#b91c1c;'>{(report or {}).get('error', 'Sin corrida.')}</p>")

    perfil = report.get("profile", {})
    rama = report.get("branch", "?")
    titulo_rama, explica_rama = _RAMAS.get(rama, (f"Rama {rama}", ""))

    h = CSS_RESUMEN
    h += "<h2>Qué se analizó</h2>"
    h += (f"<p>{perfil.get('n_rows', '?')} filas y "
          f"{perfil.get('n_columns', '?')} columna(s). "
          f"Estructura: {perfil.get('shape', '?')}. "
          f"Filas duplicadas: {perfil.get('full_duplicates', 0)}.</p>")
    h += f"<p><b>{titulo_rama}.</b> {explica_rama}</p>"

    h += "<h2>Qué hizo el motor</h2>"
    h += _tarjetas(auditoria)
    h += ("<p class='nota'>El motor es un árbol de decisiones: en cada nodo "
          "verifica el supuesto y después elige la prueba. Nunca corre una "
          "prueba cuyo supuesto no se cumplió. El árbol completo, con el camino "
          "que recorrió esta corrida, está en la pestaña "
          "<b>Árbol de decisión</b>.</p>")

    h += "<h2>Qué encontró</h2>"
    h += _hallazgos(report)
    h += _concordancias(report)

    avisos = report.get("warnings_globales") or []
    bloque_avisos = []
    for b in report.get("blocks", []) or []:
        bloque_avisos.extend(b.get("advertencias", []) or [])
    todos = avisos + bloque_avisos
    if todos:
        h += "<h2>Advertencias activas</h2>"
        vistos = set()
        for a in todos:
            if a in vistos:
                continue
            vistos.add(a)
            h += f"<div class='aviso'>{a}</div>"

    h += _por_que_no(auditoria)
    return h


def leyenda_arbol() -> str:
    """Texto corto que acompaña al dibujo del árbol."""
    return (
        "<div style=\"font-family:'Segoe UI',sans-serif;font-size:12px;color:#334155;\">"
        "<b>Cómo leerlo.</b> Cada caja es un ensayo; cada caja azul, la pregunta "
        "que bifurca. En <span style='color:#15803d;font-weight:bold;'>verde</span> "
        "lo que corrió (con las veces que corrió); en gris lo que el motor evaluó "
        "y descartó; en punteado lo que no aplica a estos datos. Las flechas "
        "verdes marcan el camino recorrido."
        "</div>"
    )


ESTADOS_ORDEN = (EJECUTADO, DESCARTADO, NO_APLICA)

"""Auditoria de una corrida de Omnianalisis.

Cruza el catalogo (`omni_catalogo.ENSAYOS`) contra lo que el motor realmente
ejecuto y devuelve, para cada ensayo, uno de tres estados:

  EJECUTADO   corrio; con cuantas veces, sobre que bloques y con que resultado.
  DESCARTADO  el motor lo evaluo y eligio no correrlo; con el motivo.
  NO_APLICA   nunca se llego a ese nodo del arbol: los datos no abren esa rama.

La diferencia entre DESCARTADO y NO_APLICA es la que hace auditable al motor.
"No corri Fisher" no dice nada; "no corri Fisher porque la frecuencia esperada
minima fue 12,4 y el chi-cuadrado si aplicaba" es una decision defendible ante
un auditor.

Ademas separa dos conteos que se confunden:
  - tipos de ensayo (cuantos del catalogo se tocaron)
  - ejecuciones (cuantas veces corrieron, sumando columnas y pares)
Con 8 columnas el univariado corre 8 veces y el bivariado 28: el numero de
ejecuciones es mucho mayor que el de tipos, y es el que suele citarse.
"""
from src.analysis.omni_catalogo import ENSAYOS, ETAPAS, POR_ID

EJECUTADO = "ejecutado"
DESCARTADO = "descartado"
NO_APLICA = "no aplica"

# Etiquetas cortas para la UI y el dibujo del arbol.
ETIQUETA = {
    EJECUTADO: "Ejecutado",
    DESCARTADO: "Descartado por el árbol",
    NO_APLICA: "No aplica a estos datos",
}


def _origenes(report: dict):
    """Devuelve (nombre_del_ambito, lista_de_marcas) por cada fuente de marcas.

    El informe global lleva sus propias marcas (perfilado, rama C) ademas de
    las de cada bloque.
    """
    yield "Informe", report.get("ensayos", []) or []
    for b in report.get("blocks", []) or []:
        yield b.get("titulo", "(bloque sin titulo)"), b.get("ensayos", []) or []


def auditar(report: dict) -> dict:
    """Estado de cada ensayo del catalogo para esta corrida.

    Devuelve:
      filas:       lista por ensayo, en orden de catalogo, con estado y detalle.
      por_estado:  {estado: [filas]}
      resumen:     conteos de tipos y de ejecuciones.
      por_etapa:   {etapa: {estado: n}} para el resumen visual.
      estado:      {id: estado} — atajo para el dibujo del arbol.
    """
    if not isinstance(report, dict) or "error" in report:
        return {"filas": [], "por_estado": {}, "resumen": {}, "por_etapa": {},
                "estado": {}, "error": (report or {}).get("error", "informe vacio")}

    ejecuciones: dict[str, list] = {}
    descartes: dict[str, list] = {}

    for ambito, marcas in _origenes(report):
        for m in marcas:
            id_ = m.get("id")
            if id_ not in POR_ID:
                # Marca sin entrada de catalogo: la deja ver el test, no la UI.
                continue
            if m.get("estado") == "descartado":
                descartes.setdefault(id_, []).append(
                    {"ambito": ambito, "motivo": m.get("motivo", "")}
                )
            else:
                ejecuciones.setdefault(id_, []).append(
                    {"ambito": ambito, "detalle": m.get("detalle", "")}
                )

    filas = []
    for e in ENSAYOS:
        corridas = ejecuciones.get(e.id, [])
        rechazos = descartes.get(e.id, [])
        if corridas:
            estado = EJECUTADO
        elif rechazos:
            estado = DESCARTADO
        else:
            estado = NO_APLICA

        # Motivos distintos, conservando el orden de aparicion.
        motivos = []
        for r in rechazos:
            if r["motivo"] and r["motivo"] not in motivos:
                motivos.append(r["motivo"])

        filas.append({
            "id": e.id,
            "nombre": e.nombre,
            "etapa": e.etapa,
            "estado": estado,
            "veces": len(corridas),
            "descartes": len(rechazos),
            "ambitos": [c["ambito"] for c in corridas],
            "detalles": [c["detalle"] for c in corridas if c["detalle"]],
            "motivos": motivos,
            "gatillo": e.gatillo,
            "porque": e.porque,
            "alternativa": e.alternativa,
            "norma": e.norma,
        })

    por_estado: dict[str, list] = {EJECUTADO: [], DESCARTADO: [], NO_APLICA: []}
    for f in filas:
        por_estado[f["estado"]].append(f)

    por_etapa = {}
    for etapa in ETAPAS:
        de_etapa = [f for f in filas if f["etapa"] == etapa]
        por_etapa[etapa] = {
            EJECUTADO: sum(1 for f in de_etapa if f["estado"] == EJECUTADO),
            DESCARTADO: sum(1 for f in de_etapa if f["estado"] == DESCARTADO),
            NO_APLICA: sum(1 for f in de_etapa if f["estado"] == NO_APLICA),
            "total": len(de_etapa),
        }

    resumen = {
        "catalogo": len(ENSAYOS),
        "tipos_ejecutados": len(por_estado[EJECUTADO]),
        "tipos_descartados": len(por_estado[DESCARTADO]),
        "tipos_no_aplican": len(por_estado[NO_APLICA]),
        "ejecuciones": sum(f["veces"] for f in filas),
        "decisiones": sum(f["veces"] + f["descartes"] for f in filas),
        "bloques": len(report.get("blocks", []) or []),
        "rama": report.get("branch", "?"),
    }

    return {"filas": filas, "por_estado": por_estado, "resumen": resumen,
            "por_etapa": por_etapa,
            "estado": {f["id"]: f["estado"] for f in filas}}


def resumen_en_una_linea(auditoria: dict) -> str:
    """La frase que va arriba de la pestana de auditoria."""
    r = auditoria.get("resumen") or {}
    if not r:
        return "Sin corrida que auditar."
    return (
        f"{r['ejecuciones']} ejecución(es) de {r['tipos_ejecutados']} tipo(s) de ensayo, "
        f"sobre un catálogo de {r['catalogo']}. "
        f"{r['tipos_descartados']} tipo(s) evaluado(s) y descartado(s) con motivo; "
        f"{r['tipos_no_aplican']} no aplican a estos datos."
    )

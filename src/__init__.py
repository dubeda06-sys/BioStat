"""BioStat - Software estadistico para laboratorio clinico."""
# 1.0.0 marca la auditoria numerica del 23 de agosto de 2026: hasta 0.9.0 habia
# 12 defectos de calculo, varios de ellos capaces de cambiar una decision
# clinica. Todo build anterior a esta version produce numeros equivocados en
# Passing-Bablok, Cox, tamano muestral y AUC con puntajes empatados.
# 1.1.0 marca la segunda auditoria, del 26 de septiembre: 42 defectos mas,
# entre ellos los pares desalineados con una sola celda vacia, y la envoltura
# Resultado en los 78 analisis.
# 1.2.0 es de interfaz (los calculos son los de 1.1.0): el informe empieza por
# la conclusion, la hoja dice el tipo de cada columna y el tema se renovo.
# Ver CHANGELOG.md.
__version__ = "1.2.0"

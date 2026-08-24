"""BioStat - Software estadistico para laboratorio clinico."""
# 1.0.0 marca la auditoria numerica del 23 de agosto de 2026: hasta 0.9.0 habia
# 12 defectos de calculo, varios de ellos capaces de cambiar una decision
# clinica. Todo build anterior a esta version produce numeros equivocados en
# Passing-Bablok, Cox, tamano muestral y AUC con puntajes empatados.
# Ver CHANGELOG.md.
__version__ = "1.0.0"

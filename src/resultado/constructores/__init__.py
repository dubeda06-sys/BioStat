"""Un constructor por análisis: de la hoja a un `Resultado`, sin Qt.

Cada constructor recibe el DataFrame, las columnas y las opciones de método, y
devuelve un `Resultado`. No dibuja: deja `Figura`s que se dibujan al mostrarse.
El panel los llama desde su `dispatch`; los tests, directamente.

`CONSTRUCTORES` es la lista de los ya migrados. Los tests de contrato la
recorren entera: todo lo que entra acá tiene que tener ficha, no decir
«significativo» y no imprimir un p como cero.
"""
from src.resultado.constructores.comparacion import bland_altman

CONSTRUCTORES = {
    "bland_altman": bland_altman,
}

__all__ = ["CONSTRUCTORES", "bland_altman"]

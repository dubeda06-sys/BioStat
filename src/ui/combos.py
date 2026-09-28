"""Rellenar un combo sin perder lo que el usuario ya eligió."""


def rellenar(combo, items, defecto=0):
    """Pone `items` en `combo` y conserva la elección anterior si sigue estando.

    Los paneles vuelven a cargar las columnas cada vez que se entra a su
    pestaña. Antes eso borraba lo elegido: se elegía la Variable 2, se miraba
    la hoja y al volver estaba otra vez en la primera columna, igual que la
    Variable 1 (27 sep). Si la elección ya no existe (se renombró la columna),
    queda en `defecto`.
    """
    anterior = combo.currentText()
    combo.blockSignals(True)
    combo.clear()
    combo.addItems([str(i) for i in items])
    indice = combo.findText(anterior) if anterior else -1
    if indice < 0:
        indice = min(defecto, combo.count() - 1)
    combo.setCurrentIndex(indice)
    combo.blockSignals(False)

"""La envoltura `Resultado` y su renderizador. Ver `modelo.py`."""
from src.resultado.modelo import (
    Cita, Entrada, Metodo, Resultado, ResultadoComoBooleano, Supuesto, Valor,
)
from src.resultado.render_html import render_html

__all__ = ["Cita", "Entrada", "Metodo", "Resultado", "ResultadoComoBooleano",
           "Supuesto", "Valor", "render_html"]

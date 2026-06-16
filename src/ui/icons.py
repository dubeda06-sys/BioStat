"""Icons for BioStat using QPixmap."""
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QSize, QRect
import os


def create_colored_icon(char, size=24, color="#4f6ef7", bg_color=None):
    """Create QIcon from character with color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent if bg_color is None else QColor(bg_color))
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    if bg_color:
        painter.setBrush(QColor(bg_color))
        painter.drawEllipse(2, 2, size-4, size-4)
    
    painter.setPen(QColor(color))
    font = QFont("Arial", int(size * 0.5), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, char)
    painter.end()
    
    return QIcon(pixmap)


def create_shape_icon(shape, size=24, color="#4f6ef7"):
    """Create QIcon from shape."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    margin = 4
    
    if shape == 'folder':
        # Folder shape
        painter.drawRoundedRect(margin, margin+4, size-2*margin, size-2*margin-4, 2, 2)
        painter.drawLine(margin, margin+4, margin+6, margin+4)
        painter.drawLine(margin+6, margin+4, margin+8, margin+2)
        painter.drawLine(margin+8, margin+2, margin+16, margin+2)
    elif shape == 'disk':
        # Floppy disk shape
        painter.drawRect(margin+2, margin, size-2*margin-4, size-2*margin)
        painter.drawRect(margin+6, margin, size-2*margin-12, 6)
        painter.fillRect(margin+4, size-margin-8, size-2*margin-8, 4, QColor(color))
    elif shape == 'arrow_up':
        # Upload arrow
        cx, cy = size//2, size//2
        painter.drawLine(cx, margin+2, cx, size-margin-2)
        painter.drawLine(cx-5, margin+7, cx, margin+2)
        painter.drawLine(cx+5, margin+7, cx, margin+2)
        painter.drawLine(margin+2, size-margin-2, size-margin-2, size-margin-2)
    elif shape == 'arrow_down':
        # Download arrow
        cx, cy = size//2, size//2
        painter.drawLine(cx, margin+2, cx, size-margin-2)
        painter.drawLine(cx-5, size-margin-7, cx, size-margin-2)
        painter.drawLine(cx+5, size-margin-7, cx, size-margin-2)
        painter.drawLine(margin+2, margin+2, size-margin-2, margin+2)
    elif shape == 'play':
        # Play triangle
        cx = size // 2
        cy = size // 2
        points = [
            (margin+3, margin+2),
            (margin+3, size-margin-2),
            (size-margin-3, cy)
        ]
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
        polygon = QPolygon([QPoint(x, y) for x, y in points])
        painter.setBrush(QColor(color))
        painter.drawPolygon(polygon)
    elif shape == 'chart':
        # Bar chart
        bar_w = (size - 4*margin) // 4
        heights = [0.6, 0.8, 0.5, 0.9]
        for i, h in enumerate(heights):
            x = margin + i * (bar_w + 2)
            bar_h = int((size - 2*margin - 4) * h)
            y = size - margin - bar_h
            painter.fillRect(x, y, bar_w, bar_h, QColor(color))
    elif shape == 'x':
        # X mark
        painter.drawLine(margin+3, margin+3, size-margin-3, size-margin-3)
        painter.drawLine(size-margin-3, margin+3, margin+3, size-margin-3)
    elif shape == 'check':
        # Checkmark
        cx = size // 2
        cy = size // 2
        painter.drawLine(margin+3, cy, cx-2, size-margin-3)
        painter.drawLine(cx-2, size-margin-3, size-margin-3, margin+3)
    elif shape == 'warn':
        # Warning triangle
        cx = size // 2
        cy = size // 2
        points = [
            (cx, margin+2),
            (margin+2, size-margin-2),
            (size-margin-2, size-margin-2)
        ]
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
        polygon = QPolygon([QPoint(x, y) for x, y in points])
        painter.setBrush(QColor("#f59e0b"))
        painter.drawPolygon(polygon)
        painter.setPen(QColor("#000"))
        painter.drawText(QRect(margin, cy-2, size-2*margin, 8), Qt.AlignmentFlag.AlignCenter, "!")
    elif shape == 'info':
        # Info circle
        cx = size // 2
        cy = size // 2
        painter.drawEllipse(margin+2, margin+2, size-2*margin-4, size-2*margin-4)
        painter.setPen(QColor("#000"))
        painter.drawText(QRect(cx-2, margin+4, 4, size-2*margin-8), Qt.AlignmentFlag.AlignCenter, "i")
    elif shape == 'plus':
        cx = size // 2
        cy = size // 2
        painter.drawLine(cx, margin+3, cx, size-margin-3)
        painter.drawLine(margin+3, cy, size-margin-3, cy)
    elif shape == 'trash':
        # Trash can
        painter.drawRect(margin+4, margin+4, size-2*margin-8, size-2*margin-6)
        painter.drawLine(margin+6, margin+4, margin+8, margin+2)
        painter.drawLine(size-margin-6, margin+4, size-margin-8, margin+2)
        painter.drawLine(margin+4, margin+4, size-margin-4, margin+4)
    elif shape == 'copy':
        # Two overlapping rectangles
        painter.drawRect(margin+4, margin+2, size-2*margin-6, size-2*margin-4)
        painter.drawRect(margin+2, margin+4, size-2*margin-6, size-2*margin-4)
    elif shape == 'search':
        # Magnifying glass
        painter.drawEllipse(margin+2, margin+2, 8, 8)
        painter.drawLine(margin+8, margin+8, size-margin-2, size-margin-2)
    elif shape == 'doc':
        # Document
        painter.drawRect(margin+3, margin, size-2*margin-6, size-2*margin)
        painter.drawLine(margin+6, margin+6, size-margin-6, margin+6)
        painter.drawLine(margin+6, margin+10, size-margin-6, margin+10)
        painter.drawLine(margin+6, margin+14, size-margin-6, margin+14)
    elif shape == 'csv':
        # Document with CSV
        painter.drawRect(margin+3, margin, size-2*margin-6, size-2*margin)
        font = QFont("Arial", 5, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(margin, margin+6, size-2*margin, 10), Qt.AlignmentFlag.AlignCenter, "CSV")
    elif shape == 'excel':
        # Document with grid
        painter.drawRect(margin+3, margin, size-2*margin-6, size-2*margin)
        for i in range(3):
            painter.drawLine(margin+5, margin+8+i*4, size-margin-5, margin+8+i*4)
        for i in range(3):
            painter.drawLine(margin+5+i*4, margin+8, margin+5+i*4, size-margin-3)
    else:
        # Default circle
        painter.drawEllipse(margin, margin, size-2*margin, size-2*margin)
    
    painter.end()
    return QIcon(pixmap)


class Icons:
    """Icon constants for BioStat toolbar."""
    
    # Colors
    PRIMARY = "#4f6ef7"
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    SECONDARY = "#6b7280"
    
    # Icon methods - return QIcon
    @staticmethod
    def OPEN(): return create_shape_icon('folder', color=Icons.PRIMARY)
    @staticmethod
    def SAVE(): return create_shape_icon('disk', color=Icons.PRIMARY)
    @staticmethod
    def EXPORT(): return create_shape_icon('arrow_up', color=Icons.PRIMARY)
    @staticmethod
    def CSV(): return create_shape_icon('csv', color=Icons.PRIMARY)
    @staticmethod
    def EXCEL(): return create_shape_icon('excel', color=Icons.SUCCESS)
    @staticmethod
    def RUN(): return create_shape_icon('play', color=Icons.SUCCESS)
    @staticmethod
    def CHART(): return create_shape_icon('chart', color=Icons.PRIMARY)
    @staticmethod
    def STATS(): return create_shape_icon('chart', color=Icons.PRIMARY)
    @staticmethod
    def CLEAR(): return create_shape_icon('x', color=Icons.DANGER)
    @staticmethod
    def CHECK(): return create_shape_icon('check', color=Icons.SUCCESS)
    @staticmethod
    def WARN(): return create_shape_icon('warn', color=Icons.WARNING)
    @staticmethod
    def INFO(): return create_shape_icon('info', color=Icons.PRIMARY)
    @staticmethod
    def LAB(): return create_shape_icon('doc', color=Icons.PRIMARY)
    @staticmethod
    def GEAR(): return create_colored_icon('⚙', color=Icons.SECONDARY)
    @staticmethod
    def DOC(): return create_shape_icon('doc', color=Icons.PRIMARY)
    @staticmethod
    def SEARCH(): return create_shape_icon('search', color=Icons.PRIMARY)
    @staticmethod
    def QUESTION(): return create_colored_icon('?', color=Icons.PRIMARY)
    @staticmethod
    def ADD(): return create_shape_icon('plus', color=Icons.SUCCESS)
    @staticmethod
    def TRASH(): return create_shape_icon('trash', color=Icons.DANGER)
    @staticmethod
    def DOWNLOAD(): return create_shape_icon('arrow_down', color=Icons.PRIMARY)
    @staticmethod
    def UPLOAD(): return create_shape_icon('arrow_up', color=Icons.PRIMARY)
    @staticmethod
    def COPY(): return create_shape_icon('copy', color=Icons.PRIMARY)
    @staticmethod
    def HELP(): return create_shape_icon('info', color=Icons.PRIMARY)
    @staticmethod
    def DOWN(): return create_shape_icon('arrow_down', color=Icons.PRIMARY)
    @staticmethod
    def UP(): return create_shape_icon('arrow_up', color=Icons.PRIMARY)
    @staticmethod
    def LEFT(): return create_shape_icon('arrow_left', color=Icons.PRIMARY)
    @staticmethod
    def RIGHT(): return create_shape_icon('arrow_right', color=Icons.PRIMARY)

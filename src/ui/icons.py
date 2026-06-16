"""Icons for BioStat using qtawesome (FontAwesome 5 / Material Design)."""
import qtawesome as qta
from PyQt6.QtGui import QIcon


class Icons:
    """Icon constants for BioStat toolbar and UI elements.

    Uses qtawesome to provide professional vector icons from
    FontAwesome 5 (fa5s/fa5b) and Material Design (mdi6).
    """

    # Theme colors — Clean Clinical
    PRIMARY = "#2b579a"
    SUCCESS = "#107c41"
    WARNING = "#bf8700"
    DANGER = "#c23040"
    SECONDARY = "#4a5568"

    # ── File operations ──────────────────────────────────
    @staticmethod
    def OPEN():
        return qta.icon("fa5s.folder-open", color=Icons.PRIMARY)

    @staticmethod
    def SAVE():
        return qta.icon("fa5s.save", color=Icons.PRIMARY)

    @staticmethod
    def EXPORT():
        return qta.icon("fa5s.file-export", color=Icons.PRIMARY)

    @staticmethod
    def CSV():
        return qta.icon("fa5s.file-csv", color=Icons.PRIMARY)

    @staticmethod
    def EXCEL():
        return qta.icon("fa5s.file-excel", color=Icons.SUCCESS)

    # ── Actions ──────────────────────────────────────────
    @staticmethod
    def RUN():
        return qta.icon("fa5s.play-circle", color=Icons.SUCCESS)

    @staticmethod
    def CLEAR():
        return qta.icon("fa5s.times-circle", color=Icons.DANGER)

    @staticmethod
    def CHECK():
        return qta.icon("fa5s.check-circle", color=Icons.SUCCESS)

    # ── Charts & Statistics ──────────────────────────────
    @staticmethod
    def CHART():
        return qta.icon("fa5s.chart-bar", color=Icons.PRIMARY)

    @staticmethod
    def STATS():
        return qta.icon("fa5s.chart-line", color=Icons.PRIMARY)

    # ── Notifications ────────────────────────────────────
    @staticmethod
    def WARN():
        return qta.icon(
            "fa5s.exclamation-triangle", color=Icons.WARNING
        )

    @staticmethod
    def INFO():
        return qta.icon("fa5s.info-circle", color=Icons.PRIMARY)

    # ── Lab & Documents ──────────────────────────────────
    @staticmethod
    def LAB():
        return qta.icon("fa5s.flask", color=Icons.PRIMARY)

    @staticmethod
    def DOC():
        return qta.icon("fa5s.file-alt", color=Icons.PRIMARY)

    @staticmethod
    def GEAR():
        return qta.icon("fa5s.cog", color=Icons.SECONDARY)

    # ── Search & Navigation ──────────────────────────────
    @staticmethod
    def SEARCH():
        return qta.icon("fa5s.search", color=Icons.PRIMARY)

    @staticmethod
    def QUESTION():
        return qta.icon(
            "fa5s.question-circle", color=Icons.PRIMARY
        )

    @staticmethod
    def HELP():
        return qta.icon("fa5s.life-ring", color=Icons.PRIMARY)

    # ── Editing ──────────────────────────────────────────
    @staticmethod
    def ADD():
        return qta.icon("fa5s.plus-circle", color=Icons.SUCCESS)

    @staticmethod
    def TRASH():
        return qta.icon("fa5s.trash-alt", color=Icons.DANGER)

    @staticmethod
    def COPY():
        return qta.icon("fa5s.copy", color=Icons.PRIMARY)

    # ── Arrows ───────────────────────────────────────────
    @staticmethod
    def DOWNLOAD():
        return qta.icon("fa5s.download", color=Icons.PRIMARY)

    @staticmethod
    def UPLOAD():
        return qta.icon("fa5s.upload", color=Icons.PRIMARY)

    @staticmethod
    def DOWN():
        return qta.icon("fa5s.arrow-down", color=Icons.PRIMARY)

    @staticmethod
    def UP():
        return qta.icon("fa5s.arrow-up", color=Icons.PRIMARY)

    @staticmethod
    def LEFT():
        return qta.icon("fa5s.arrow-left", color=Icons.PRIMARY)

    @staticmethod
    def RIGHT():
        return qta.icon("fa5s.arrow-right", color=Icons.PRIMARY)

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtCore import Qt, QByteArray, QSize
from PyQt5.QtGui import QColor, QFont, QPalette


# ====== آیکون‌های SVG جاسازی‌شده ======
home_svg = """
<svg width="24" height="24" fill="#888" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 9.75L12 3l9 6.75V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V9.75Z"/>
</svg>
"""

settings_svg = """
<svg width="24" height="24" fill="#888" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8.14-2.25a6.2 6.2 0 0 0 0-1.5l2.01-1.57a.38.38 0 0 0 .09-.49l-1.9-3.3a.38.38 0 0 0-.48-.16l-2.37.95a6.28 6.28 0 0 0-1.3-.75l-.36-2.5a.38.38 0 0 0-.38-.32h-3.8a.38.38 0 0 0-.38.32l-.36 2.5a6.28 6.28 0 0 0-1.3.75l-2.37-.95a.38.38 0 0 0-.48.16l-1.9 3.3a.38.38 0 0 0 .09.49l2.01 1.57a6.2 6.2 0 0 0 0 1.5l-2.01 1.57a.38.38 0 0 0-.09.49l1.9 3.3c.1.18.3.25.48.16l2.37-.95c.4.3.84.55 1.3.75l.36 2.5c.04.19.2.32.38.32h3.8c.19 0 .35-.13.38-.32l.36-2.5a6.28 6.28 0 0 0 1.3-.75l2.37.95c.18.09.38.02.48-.16l1.9-3.3a.38.38 0 0 0-.09-.49l-2.01-1.57Z"/>
</svg>
"""


def make_svg_widget(svg_data, size=QSize(40, 40)):
    widget = QSvgWidget()
    widget.load(QByteArray(svg_data.encode()))
    widget.setFixedSize(size)
    return widget


# ====== بخش سایدبار مدرن ======
class Sidebar(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(80)
        self.setStyleSheet("""
            QFrame {
                background-color: #161623;
                border-right: 1px solid #29293a;
            }
            QSvgWidget:hover {
                background-color: #29293a;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(20, 30, 20, 0)
        layout.setSpacing(20)

        self.icons = [
            make_svg_widget(home_svg),
            make_svg_widget(settings_svg),
        ]
        for icon in self.icons:
            layout.addWidget(icon)

        layout.addStretch()
        self.setLayout(layout)


# ====== کارت محتوا ======
class Card(QFrame):
    def __init__(self, title, content):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 16px;
            }
            QLabel {
                color: #ccddee;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_title.setStyleSheet("color: #8ceeff;")

        lbl_content = QLabel(content)
        lbl_content.setWordWrap(True)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_content)
        self.setLayout(layout)


# ====== پنل اصلی ======
class MainPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #12121a;")
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        layout.addWidget(Card(
            "Dashboard", "Welcome to your custom interface.\nThis is a test UI in PyQt5 with SVGs."))

        layout.addWidget(Card(
            "Next Feature", "Animation, dynamic icons, interactive elements, and more!"))

        self.setLayout(layout)


# ====== هدر بالایی ======
class Header(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(55)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2f0f5e, stop:1 #004f6e
                );
                border-bottom: 1px solid #333;
            }
        """)
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("🔮 Arcane Deluxe UI")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        layout.addWidget(title)
        layout.addStretch()
        self.setLayout(layout)


# ====== پنجره اصلی ======
class ArcaneWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arcane UI Pro")
        self.setGeometry(100, 100, 960, 600)
        self.setStyleSheet("background-color: #12121a;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(Header())

        main_body = QHBoxLayout()
        main_body.setContentsMargins(0, 0, 0, 0)
        main_body.addWidget(Sidebar())
        main_body.addWidget(MainPanel())

        layout.addLayout(main_body)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Dark theme
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#12121a"))
    app.setPalette(palette)

    win = ArcaneWindow()
    win.show()
    sys.exit(app.exec_())

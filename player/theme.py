"""Cyberpunk chrome drawn locally; no animation or effects over the video."""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget, QFrame


class CyberBackground(QWidget):
    def paintEvent(self, event):
        painter=QPainter(self)
        gradient=QLinearGradient(0,0,self.width(),self.height())
        gradient.setColorAt(0,QColor('#070813'))
        gradient.setColorAt(.55,QColor('#0c1022'))
        gradient.setColorAt(1,QColor('#15091e'))
        painter.fillRect(self.rect(),gradient)
        painter.setPen(QColor(40,220,255,10))
        for x in range(0,self.width(),32):painter.drawLine(x,0,x,self.height())
        for y in range(0,self.height(),32):painter.drawLine(0,y,self.width(),y)
        painter.setPen(QPen(QColor('#38f5fa'),2))
        painter.drawLine(18,2,min(260,self.width()-18),2)
        painter.setPen(QPen(QColor('#ff37aa'),2))
        painter.drawLine(max(18,self.width()-260),2,self.width()-18,2)


class CyberPanel(QFrame):
    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w,h=self.width()-1,self.height()-1
        c=12
        shape=QPolygonF([QPointF(c,1),QPointF(w,1),QPointF(w,h-c),QPointF(w-c,h),
                         QPointF(1,h),QPointF(1,c)])
        gradient=QLinearGradient(0,0,0,h)
        gradient.setColorAt(0,QColor('#101627'))
        gradient.setColorAt(1,QColor('#090d19'))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor('#254c64'),1))
        painter.drawPolygon(shape)
        painter.setPen(QPen(QColor('#3af2f5'),2))
        painter.drawLine(c+3,1,min(c+95,w-3),1)
        painter.setPen(QPen(QColor('#f435a5'),2))
        painter.drawLine(max(3,w-95),h,w-c,h)


STYLE = '''
QMainWindow, QDialog { background: #080b16; color: #e7f5ff; }
QWidget { color: #e7f5ff; font-family: "Bahnschrift", "Segoe UI", "DejaVu Sans"; font-size: 13px; }
QMenuBar, QMenu { background: #101324; color: #b6d5ee; border-bottom: 1px solid #2a3556; }
QMenu::item { padding: 7px 20px; }
QMenu::item:selected { color: #40f5f8; background: #173246; }
QFrame#panel { background: transparent; border: none; }
QPushButton { background: #111b2c; border: 1px solid #345676; border-radius: 3px; padding: 8px 12px; color: #ccedff; }
QPushButton:hover { background: #153b4d; color: #55ffff; border-color: #37e8f4; }
QPushButton:pressed { background: #20546c; }
QPushButton:checked { background: #351735; color: #ff7cc7; border-color: #f436a8; }
QPushButton:disabled { color: #5b687b; background: #101622; border-color: #27364b; }
QPushButton#primary { background: #e6ff43; color: #101510; border-color: #e6ff43; font-weight: bold; }
QPushButton#primary:hover { background: #f2ff94; border-color: #fbffc7; }
QLineEdit, QComboBox, QSpinBox { background: #080e1e; border: 1px solid #33466c; border-radius: 3px; padding: 6px; selection-background-color: #216f82; }
QLineEdit:focus, QComboBox:focus { border-color: #38eaf5; }
QComboBox QAbstractItemView { background: #111b30; color: #c9f5ff; selection-background-color: #254765; }
QListWidget { background: #090f1e; border: none; outline: none; }
QListWidget::item { padding: 11px 8px; border-bottom: 1px solid #1c2942; color: #aec5dc; }
QListWidget::item:hover { background: #142b3c; color: #59faff; }
QListWidget::item:selected { background: #183c52; border-left: 3px solid #38f5fa; color: #e2fcff; }
QSplitter::handle { background: #151b30; width: 5px; }
QSplitter::handle:hover { background: #275b72; }
QSlider::groove:horizontal { height: 5px; background: #27334d; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #38e8f2; border-radius: 2px; }
QSlider::handle:horizontal { width: 12px; margin: -5px 0; background: #e6ff43; border: 1px solid #f5ffad; border-radius: 2px; }
QStatusBar { background: #080b16; color: #7796b7; border-top: 1px solid #28304c; }
QToolTip { background: #121b2f; color: #75faff; border: 1px solid #3ee4ec; padding: 5px; }
QScrollBar:vertical { background: #0b1221; width: 8px; }
QScrollBar::handle:vertical { background: #2e526a; min-height: 24px; border-radius: 3px; }
'''

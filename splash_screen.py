"""
Syntrak 启动界面（Splash Screen）
- Logo 淡入 + 缩放动画
- 版本信息显示
- 底部进度条动画
- 约2秒后自动关闭，进入主界面
"""
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QPoint, pyqtProperty
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QBrush


class SplashScreen(QWidget):
    """启动界面"""
    finished = pyqtSignal()  # 启动界面结束信号

    def __init__(self, version: str = "v1.0"):
        super().__init__()
        self.version = version
        self._opacity = 0.0
        self._logo_scale = 0.85

        # 无边框 + 窗口置顶
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        # 不使用透明背景，避免某些平台下窗口不显示

        # 窗口大小
        self.setFixedSize(680, 420)
        self.setStyleSheet("background-color: #0f1432;")
        self._center_on_screen()

        # Logo
        logo_path = os.path.join(os.path.dirname(__file__), "pics", "welcome.png")
        self.logo_pixmap = QPixmap(logo_path)

        # 动画定时器
        self._fade_in_duration = 600   # 淡入 600ms
        self._hold_duration = 1000     # 保持 1000ms
        self._fade_out_duration = 400  # 淡出 400ms
        self._total_duration = self._fade_in_duration + self._hold_duration + self._fade_out_duration

        # 进度条
        self.progress = 0

        # 启动动画
        self._start_animation()

    def _center_on_screen(self):
        """窗口居中"""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = screen_geometry.x() + (screen_geometry.width() - self.width()) // 2
            y = screen_geometry.y() + (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _start_animation(self):
        """启动动画序列"""
        # 阶段1：淡入 + 缩放（0-600ms）
        self._fade_in_anim = QPropertyAnimation(self, b"opacity")
        self._fade_in_anim.setDuration(self._fade_in_duration)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._scale_anim = QPropertyAnimation(self, b"logo_scale")
        self._scale_anim.setDuration(self._fade_in_duration)
        self._scale_anim.setStartValue(0.85)
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutBack)

        # 进度条动画（整个过程）
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._update_progress)
        self._progress_timer.start(16)  # ~60fps

        # 总定时器：2秒后开始淡出
        QTimer.singleShot(self._fade_in_duration + self._hold_duration, self._start_fade_out)

        self._fade_in_anim.start()
        self._scale_anim.start()

    def _update_progress(self):
        """更新进度条"""
        if self.progress < 100:
            self.progress += 100 / (self._total_duration / 16)
            if self.progress > 100:
                self.progress = 100
            self.update()

    def _start_fade_out(self):
        """开始淡出动画"""
        self._fade_out_anim = QPropertyAnimation(self, b"opacity")
        self._fade_out_anim.setDuration(self._fade_out_duration)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out_anim.finished.connect(self._on_animation_finished)
        self._fade_out_anim.start()

    def _on_animation_finished(self):
        """动画结束，发射信号"""
        self._progress_timer.stop()
        self.finished.emit()
        self.close()

    # ===== 动画属性 =====
    def get_opacity(self):
        return self._opacity

    def set_opacity(self, value):
        self._opacity = value
        self.update()

    def get_logo_scale(self):
        return self._logo_scale

    def set_logo_scale(self, value):
        self._logo_scale = value
        self.update()

    opacity = pyqtProperty(float, get_opacity, set_opacity)
    logo_scale = pyqtProperty(float, get_logo_scale, set_logo_scale)

    # ===== 绘制 =====
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 整体透明度
        painter.setOpacity(self._opacity)

        # 背景：深色圆角矩形
        rect = self.rect().adjusted(10, 10, -10, -10)
        gradient = QLinearGradient(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        gradient.setColorAt(0.0, QColor(15, 20, 50))
        gradient.setColorAt(0.5, QColor(20, 30, 70))
        gradient.setColorAt(1.0, QColor(10, 15, 40))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 20, 20)

        # 边框光晕
        painter.setPen(QColor(100, 150, 255, 80))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 20, 20)

        # Logo（居中，带缩放）
        if not self.logo_pixmap.isNull():
            logo_width = 480
            logo_height = int(logo_width * self.logo_pixmap.height() / self.logo_pixmap.width())
            scaled_width = int(logo_width * self._logo_scale)
            scaled_height = int(logo_height * self._logo_scale)

            logo_x = (self.width() - scaled_width) // 2
            logo_y = 100 + (logo_height - scaled_height) // 2

            # Logo 阴影
            painter.setOpacity(self._opacity * 0.3)
            shadow_pix = self.logo_pixmap.scaled(
                scaled_width, scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(logo_x + 3, logo_y + 5, shadow_pix)

            # Logo 本体
            painter.setOpacity(self._opacity)
            painter.drawPixmap(logo_x, logo_y, scaled_width, scaled_height, self.logo_pixmap)

        # 版本信息
        painter.setOpacity(self._opacity)
        font = QFont("Segoe UI", 11)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(180, 200, 255))
        version_text = f"Syntrak MotionCap Viewer  {self.version}"
        painter.drawText(self.rect().adjusted(0, 0, 0, -60), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, version_text)

        # 底部进度条背景
        bar_x = 140
        bar_y = self.height() - 45
        bar_width = self.width() - 280
        bar_height = 6

        # 背景
        painter.setOpacity(self._opacity * 0.5)
        painter.setBrush(QColor(60, 70, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, 3, 3)

        # 进度（蓝紫渐变）
        if self.progress > 0:
            progress_width = int(bar_width * self.progress / 100)
            prog_gradient = QLinearGradient(bar_x, bar_y, bar_x + progress_width, bar_y)
            prog_gradient.setColorAt(0.0, QColor(100, 120, 255))
            prog_gradient.setColorAt(0.5, QColor(150, 100, 255))
            prog_gradient.setColorAt(1.0, QColor(100, 200, 255))
            painter.setOpacity(self._opacity)
            painter.setBrush(QBrush(prog_gradient))
            painter.drawRoundedRect(bar_x, bar_y, progress_width, bar_height, 3, 3)

        # Loading 文字
        painter.setOpacity(self._opacity * 0.7)
        font_small = QFont("Segoe UI", 9)
        painter.setFont(font_small)
        painter.setPen(QColor(140, 160, 200))
        painter.drawText(self.rect().adjusted(0, 0, 0, -15), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, "Loading...")

        painter.end()

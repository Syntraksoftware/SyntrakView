from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime

class LogEmitter(QObject):
    sig_log = pyqtSignal(str)

class Logger:
    def __init__(self):
        self.emitter = LogEmitter()

    def info(self, msg):
        text = f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] {msg}"
        self.emitter.sig_log.emit(text)

    def warn(self, msg):
        text = f"[{datetime.now().strftime('%H:%M:%S')}] [WARN] {msg}"
        self.emitter.sig_log.emit(text)

    def error(self, msg):
        text = f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {msg}"
        self.emitter.sig_log.emit(text)

global_logger = Logger()

# 观察模式(默认 False)：关闭热路径调试 print 与 angle_log.txt，动画不被日志拖慢。
# UI "Debug log" 勾选框切换；运行时随时可开关。
DEBUG_LOG = False

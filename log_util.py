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

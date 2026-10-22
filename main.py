import sys
import asyncio
from PyQt6.QtWidgets import QApplication
import qasync

# 还原最初原始文件名和类名，不要乱改名
from ble_manager import BleManager
from ui_main import MainWindow
from splash_screen import SplashScreen
from log_util import global_logger

def main():
    app = QApplication(sys.argv)
    # 创建qasync循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    ble_mgr = BleManager()
    win = MainWindow(ble_mgr)

    # 信号绑定
    global_logger.emitter.sig_log.connect(win.append_log)

    # 创建启动界面
    splash = SplashScreen(version="v1.1")

    # 启动界面结束后显示主界面
    def on_splash_finished():
        win.show()
        win.raise_()
        win.activateWindow()

    splash.finished.connect(on_splash_finished)
    splash.show()
    splash.raise_()
    splash.activateWindow()

    # 修复：不用 loop.quit，改用 loop.stop()
    def on_window_closed():
        loop.stop()
    win.destroyed.connect(on_window_closed)

    try:
        loop.run_forever()
    finally:
        loop.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Return to Close...")

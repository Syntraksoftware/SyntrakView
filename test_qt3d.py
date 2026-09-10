"""快速测试Qt3D人偶组件（不连接BLE，用模拟角度数据）"""
import sys
import math
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import QTimer
from skeleton_qt3d_view import Qt3DSkeletonWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt3D Skeleton Test")
        self.resize(600, 700)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.skeleton = Qt3DSkeletonWidget()
        layout.addWidget(self.skeleton)

        btn = QPushButton("Animate Left Arm")
        btn.clicked.connect(self.toggle_animate)
        layout.addWidget(btn)

        self.setCentralWidget(central)
        self.animating = False
        self.anim_time = 0
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate)
        self.anim_timer.start(33)

    def toggle_animate(self):
        self.animating = not self.animating

    def animate(self):
        if not self.animating:
            return
        self.anim_time += 0.05
        # 模拟左臂运动
        shoulder_z = 30 + 30 * math.sin(self.anim_time)
        elbow_z = 60 + 40 * math.sin(self.anim_time * 1.5)
        angles = {
            1: [0, 0, 0],
            10: [0, 0, shoulder_z],
            12: [0, 0, elbow_z],
        }
        self.skeleton.update_angles(angles)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = TestWindow()
    w.show()
    sys.exit(app.exec())

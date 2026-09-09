'''
2D侧视人偶显示组件，用13关节相对转角实时驱动
像滑雪的人，侧视图，左右肢体错开显示
'''
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont


class Skeleton2DWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 500)
        # 13关节相对转角: {sensor_id: [Y, X, Z]度}
        self._angles = {i: [0.0, 0.0, 0.0] for i in range(1, 14)}
        self._scale = 1.8  # 1cm = 1.8像素
        self._connected = False

        # 骨骼定义: (关节名, 传感器ID, 父关节索引, 长度cm, 相对父的初始角度度, 颜色, 左右偏移像素)
        # 角度: 0=向右(前), 90=向下, -90=向上, 180=向左(后)
        # 索引顺序:
        #  0=Hips(根)
        #  1=Hip_L, 2=Thigh_L, 3=Calf_L, 4=Foot_L
        #  5=Hip_R, 6=Thigh_R, 7=Calf_R, 8=Foot_R
        #  9=Spine(Shoulder_L位置), 10=UpperArm_L, 11=ForeArm_L, 12=Hand_L
        #  13=Shoulder_R, 14=UpperArm_R, 15=ForeArm_R, 16=Hand_R
        #  17=Head
        self._bones = [
            # name,      imu, parent, len,  init_angle, color,      side_off
            ("Hips",        1,  -1,  0,    0,   "#2c3e50", 0),    # 0 根
            ("Hip_L",       2,  0,   8.8,  90,  "#e74c3c", -5),   # 1 左髋向下
            ("Thigh_L",     4,  1,   45.6, 0,   "#e74c3c", 0),    # 2 左大腿
            ("Calf_L",      6,  2,   46.7, 0,   "#e74c3c", 0),    # 3 左小腿
            ("Foot_L",      0,  3,   18,   -80, "#e74c3c", 0),    # 4 左脚(前下)
            ("Hip_R",       3,  0,   8.8,  90,  "#3498db", 5),    # 5 右髋
            ("Thigh_R",     5,  5,   45.6, 0,   "#3498db", 0),    # 6 右大腿
            ("Calf_R",      7,  6,   46.7, 0,   "#3498db", 0),    # 7 右小腿
            ("Foot_R",      0,  7,   18,   -80, "#3498db", 0),    # 8 右脚
            ("Spine",       8,  0,   48.7, -90, "#27ae60", -5),   # 9 脊柱向上(左肩高度)
            ("UpperArm_L",  10, 9,   15.6, 80,  "#27ae60", 0),    # 10 左上臂(前下)
            ("ForeArm_L",   12, 10,  25.9, 0,   "#27ae60", 0),    # 11 左前臂
            ("Hand_L",      0,  11,  20,   0,   "#27ae60", 0),    # 12 左手
            ("Shoulder_R",  9,  9,   0,    0,   "#f39c12", 10),   # 13 右肩(从脊柱偏移)
            ("UpperArm_R",  11, 13,  15.6, 80,  "#f39c12", 0),    # 14 右上臂
            ("ForeArm_R",   13, 14,  25.9, 0,   "#f39c12", 0),    # 15 右前臂
            ("Hand_R",      0,  15,  20,   0,   "#f39c12", 0),    # 16 右手
            ("Head",        0,  9,   22,   -90, "#2c3e50", 0),    # 17 头(从脊柱向上)
        ]

    def update_angles(self, angles: dict):
        """接收13关节相对转角: {sensor_id: [Y,X,Z]度}"""
        self._angles.update(angles)
        self._connected = True
        self.update()

    def set_connected(self, connected: bool):
        self._connected = connected
        self.update()

    def _compute_positions(self):
        """计算所有关节的2D位置和绝对角度"""
        n = len(self._bones)
        pos = [(0.0, 0.0)] * n
        abs_angle = [0.0] * n

        # 根节点位置
        cx = self.width() / 2
        cy = self.height() * 0.32
        pos[0] = (cx, cy)
        abs_angle[0] = 0.0

        for i in range(1, n):
            name, imu_id, parent, length, init_angle, color, side_off = self._bones[i]

            # 绝对角度 = 父绝对角度 + 初始角度偏移 + 本关节相对转角Z
            angle = abs_angle[parent] + init_angle
            if imu_id > 0 and imu_id in self._angles:
                angle += self._angles[imu_id][2]  # Z rotation
            abs_angle[i] = angle

            # 计算位置
            px, py = pos[parent]
            rad = math.radians(angle)
            dx = length * self._scale * math.cos(rad)
            dy = length * self._scale * math.sin(rad)
            pos[i] = (px + dx + side_off, py + dy)

        return pos

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor("#f5f7fa"))

        # 地面线
        ground_y = self.height() - 30
        pen = QPen(QColor("#bdc3c7"), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(20, ground_y, self.width() - 20, ground_y)

        if not self._connected:
            painter.setPen(QColor("#95a5a6"))
            painter.setFont(QFont("Arial", 14))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "Connect to device to see\nreal-time skeleton")
            return

        pos = self._compute_positions()

        # 画骨骼连线
        for i in range(1, len(self._bones)):
            name, imu_id, parent, length, init_angle, color, side_off = self._bones[i]
            if length <= 0:
                continue  # 跳过纯偏移节点(如Shoulder_R)
            x1, y1 = pos[parent]
            x2, y2 = pos[i]

            width = 6 if "Thigh" in name or "Calf" in name else 4
            if "UpperArm" in name or "ForeArm" in name:
                width = 5
            if "Spine" in name:
                width = 7
            if "Foot" in name or "Hand" in name:
                width = 3

            pen = QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 画关节点和特殊部位
        for i, bone in enumerate(self._bones):
            name, imu_id, parent, length, init_angle, color, side_off = bone
            x, y = pos[i]

            if imu_id > 0:
                # 有传感器的关节
                r = 8
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawEllipse(QPointF(x, y), r, r)
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Arial", 7, QFont.Weight.Bold))
                painter.drawText(QRectF(x - 10, y - 7, 20, 14),
                               Qt.AlignmentFlag.AlignCenter, str(imu_id))
            elif name == "Head":
                r = 15
                painter.setBrush(QBrush(QColor("#f5cba7")))
                painter.setPen(QPen(QColor("#2c3e50"), 2))
                painter.drawEllipse(QPointF(x, y), r, r)
            elif "Foot" in name:
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor("#2c3e50"), 1))
                painter.drawRoundedRect(QRectF(x - 14, y - 5, 28, 10), 3, 3)

        # 滑雪板
        foot_l = pos[4]
        foot_r = pos[8]
        fx = (foot_l[0] + foot_r[0]) / 2
        fy = max(foot_l[1], foot_r[1]) + 10
        pen = QPen(QColor("#2c3e50"), 3)
        painter.setPen(pen)
        painter.drawLine(QPointF(fx - 70, fy), QPointF(fx + 70, fy))

        # 标题
        painter.setPen(QColor("#2c3e50"))
        painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        painter.drawText(10, 22, "Real-time Skeleton (Side View)")

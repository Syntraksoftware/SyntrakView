"""
sensor_viewer_dialog.py
Sensor attitude viewer dialog.
Left: human figure with sensor nodes (clickable)
Right: 3D attitude visualization (matplotlib)
Bottom: status info
All UI text in English.
"""
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QMouseEvent

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from sensor_data_parser import SensorDataParser, SENSOR_NAMES


# Sensor positions on human figure (relative coords 0-1, x=left->right, y=top->bottom)
# Based on IMU location diagram (front view)
SENSOR_POSITIONS = {
    8:  (0.30, 0.20),  # Left Shoulder (joint)
    9:  (0.70, 0.20),  # Right Shoulder (joint)
    10: (0.23, 0.25),  # Left Upper Arm (mid-bone, between shoulder and elbow)
    11: (0.77, 0.25),  # Right Upper Arm (mid-bone)
    12: (0.18, 0.38),  # Left Forearm (mid-bone, between elbow and wrist)
    13: (0.82, 0.38),  # Right Forearm (mid-bone)
    1:  (0.50, 0.40),  # Waist
    2:  (0.37, 0.50),  # Left Hip (pelvis joint)
    3:  (0.63, 0.50),  # Right Hip (pelvis joint)
    4:  (0.41, 0.57),  # Left Thigh (mid-bone, between hip and knee)
    5:  (0.59, 0.57),  # Right Thigh (mid-bone)
    6:  (0.41, 0.75),  # Left Shin (mid-bone, between knee and ankle)
    7:  (0.59, 0.75),  # Right Shin (mid-bone)
}

# English sensor names
SENSOR_NAMES_EN = {
    1: "Waist",
    2: "L Hip",
    3: "R Hip",
    4: "L Thigh",
    5: "R Thigh",
    6: "L Shin",
    7: "R Shin",
    8: "L Shoulder",
    9: "R Shoulder",
    10: "L Upper Arm",
    11: "R Upper Arm",
    12: "L Forearm",
    13: "R Forearm",
}


def quaternion_to_rotation_matrix(qw, qx, qy, qz):
    """Convert quaternion (w,x,y,z) to 3x3 rotation matrix"""
    n = np.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
    if n < 1e-8:
        return np.eye(3)
    qw, qx, qy, qz = qw/n, qx/n, qy/n, qz/n
    return np.array([
        [1 - 2*(qy*qy + qz*qz), 2*(qx*qy - qw*qz),     2*(qx*qz + qw*qy)],
        [2*(qx*qy + qw*qz),     1 - 2*(qx*qx + qz*qz), 2*(qy*qz - qw*qx)],
        [2*(qx*qz - qw*qy),     2*(qy*qz + qw*qx),     1 - 2*(qx*qx + qy*qy)],
    ])


class HumanFigureWidget(QWidget):
    """Custom widget that draws a human figure with clickable sensor nodes."""

    sensor_selected = pyqtSignal(int)  # emits sensor_id

    # Colors
    COLOR_STATIONARY = QColor(46, 204, 113)   # green - online & stationary
    COLOR_MOVING = QColor(231, 76, 60)         # red - online & moving
    COLOR_OFFLINE = QColor(127, 140, 141)      # gray - offline
    COLOR_SELECTED = QColor(241, 196, 15)       # yellow ring for selected
    COLOR_BODY = QColor(52, 73, 94)             # dark blue-gray body outline
    COLOR_BG = QColor(26, 26, 46)               # dark background

    def __init__(self, parser: SensorDataParser, parent=None):
        super().__init__(parent)
        self.parser = parser
        self.selected_id = 1
        self.setMinimumSize(220, 500)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._node_radius = 12

    def set_selected(self, sensor_id: int):
        self.selected_id = sensor_id
        self.update()

    def _get_node_pos(self, sensor_id: int) -> QPointF:
        """Get pixel position for a sensor node."""
        rel = SENSOR_POSITIONS.get(sensor_id, (0.5, 0.5))
        x = int(rel[0] * self.width())
        y = int(rel[1] * self.height())
        return QPointF(x, y)

    def _hit_test(self, pos: QPointF) -> int:
        """Find sensor node at given position. Returns sensor_id or -1."""
        for sid in SENSOR_POSITIONS:
            node_pos = self._get_node_pos(sid)
            dx = pos.x() - node_pos.x()
            dy = pos.y() - node_pos.y()
            if (dx*dx + dy*dy) <= (self._node_radius + 4) ** 2:
                return sid
        return -1

    def mousePressEvent(self, event: QMouseEvent):
        sid = self._hit_test(event.position())
        if sid > 0:
            self.selected_id = sid
            self.sensor_selected.emit(sid)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), self.COLOR_BG)

        w = self.width()
        h = self.height()

        # ===== Draw human figure (stylized front view) =====
        # Body color - slightly lighter for better visibility
        body_color = QColor(80, 110, 150)
        joint_color = QColor(120, 160, 200)

        # Key body points (relative coords)
        head_c = QPointF(0.50 * w, 0.09 * h)
        head_r = 0.055 * h
        neck_t = QPointF(0.50 * w, 0.145 * h)
        neck_b = QPointF(0.50 * w, 0.165 * h)
        shoulder_l = QPointF(0.28 * w, 0.18 * h)
        shoulder_r = QPointF(0.72 * w, 0.18 * h)
        elbow_l = QPointF(0.20 * w, 0.31 * h)
        elbow_r = QPointF(0.80 * w, 0.31 * h)
        wrist_l = QPointF(0.16 * w, 0.44 * h)
        wrist_r = QPointF(0.84 * w, 0.44 * h)
        waist_l = QPointF(0.37 * w, 0.40 * h)
        waist_r = QPointF(0.63 * w, 0.40 * h)
        hip_l = QPointF(0.41 * w, 0.49 * h)
        hip_r = QPointF(0.59 * w, 0.49 * h)
        knee_l = QPointF(0.41 * w, 0.65 * h)
        knee_r = QPointF(0.59 * w, 0.65 * h)
        ankle_l = QPointF(0.41 * w, 0.84 * h)
        ankle_r = QPointF(0.59 * w, 0.84 * h)
        foot_l = QPointF(0.37 * w, 0.89 * h)
        foot_r = QPointF(0.63 * w, 0.89 * h)

        # Draw limbs with thick rounded lines
        limb_pen = QPen(body_color, 8)
        limb_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        limb_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(limb_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Arms
        painter.drawLine(shoulder_l, elbow_l)
        painter.drawLine(elbow_l, wrist_l)
        painter.drawLine(shoulder_r, elbow_r)
        painter.drawLine(elbow_r, wrist_r)

        # Legs
        painter.drawLine(hip_l, knee_l)
        painter.drawLine(knee_l, ankle_l)
        painter.drawLine(hip_r, knee_r)
        painter.drawLine(knee_r, ankle_r)

        # Feet (short horizontal lines)
        painter.drawLine(ankle_l, foot_l)
        painter.drawLine(ankle_r, foot_r)

        # Torso - filled trapezoid (shoulders to waist)
        torso_pen = QPen(body_color, 2)
        painter.setPen(torso_pen)
        painter.setBrush(QBrush(QColor(60, 85, 120, 180)))
        torso_points = [shoulder_l, shoulder_r, waist_r, waist_l]
        painter.drawPolygon(*[p.toPoint() for p in torso_points])

        # Pelvis - inverted trapezoid (waist to hips), wider at bottom
        pelvis_top_l = QPointF(0.39 * w, 0.41 * h)
        pelvis_top_r = QPointF(0.61 * w, 0.41 * h)
        pelvis_bot_l = QPointF(0.36 * w, 0.50 * h)
        pelvis_bot_r = QPointF(0.64 * w, 0.50 * h)
        pelvis_pen = QPen(body_color, 2)
        painter.setPen(pelvis_pen)
        painter.setBrush(QBrush(QColor(55, 78, 110, 200)))
        pelvis_points = [pelvis_top_l, pelvis_top_r, pelvis_bot_r, pelvis_bot_l]
        painter.drawPolygon(*[p.toPoint() for p in pelvis_points])

        # Neck
        neck_pen = QPen(body_color, 6)
        neck_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(neck_pen)
        painter.drawLine(neck_t, neck_b)

        # Head - filled circle with outline
        painter.setPen(QPen(body_color, 2))
        painter.setBrush(QBrush(QColor(70, 100, 140, 200)))
        painter.drawEllipse(head_c, head_r, head_r)

        # Joint circles (shoulders, elbows, wrists, hips, knees, ankles)
        joint_r = 5
        painter.setPen(QPen(joint_color, 1.5))
        painter.setBrush(QBrush(joint_color))
        for jp in [shoulder_l, shoulder_r, elbow_l, elbow_r, wrist_l, wrist_r,
                   hip_l, hip_r, knee_l, knee_r, ankle_l, ankle_r]:
            painter.drawEllipse(jp, joint_r, joint_r)

        # Hands (small circles at wrists)
        hand_r = 7
        painter.setPen(QPen(QColor(150, 180, 210), 1.5))
        painter.setBrush(QBrush(QColor(150, 180, 210, 200)))
        painter.drawEllipse(wrist_l, hand_r, hand_r)
        painter.drawEllipse(wrist_r, hand_r, hand_r)

        # Draw sensor nodes
        for sid in SENSOR_POSITIONS:
            pos = self._get_node_pos(sid)
            sensor = self.parser.get_sensor(sid)

            # Determine color
            if sensor and sensor.valid and sensor.is_fresh:
                if sensor.is_stationary:
                    color = self.COLOR_STATIONARY
                else:
                    color = self.COLOR_MOVING
            else:
                color = self.COLOR_OFFLINE

            # Selected ring
            if sid == self.selected_id:
                ring_pen = QPen(self.COLOR_SELECTED, 3)
                painter.setPen(ring_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(pos, self._node_radius + 4, self._node_radius + 4)

            # Node circle
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(pos, self._node_radius, self._node_radius)

            # Sensor ID text
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 8, QFont.Weight.Bold)
            painter.setFont(font)
            text_rect = painter.boundingRect(0, 0, 30, 20, Qt.AlignmentFlag.AlignCenter, str(sid))
            text_rect.moveCenter(pos.toPoint())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(sid))

        # Legend
        legend_y = h - 60
        painter.setPen(QColor(236, 240, 241))
        legend_font = QFont("Arial", 8)
        painter.setFont(legend_font)

        items = [
            (self.COLOR_STATIONARY, "Online / Stationary"),
            (self.COLOR_MOVING, "Online / Moving"),
            (self.COLOR_OFFLINE, "Offline"),
        ]
        for i, (color, label) in enumerate(items):
            ly = legend_y + i * 18
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawEllipse(QPointF(15, ly), 6, 6)
            painter.setPen(QColor(236, 240, 241))
            painter.drawText(28, ly + 4, label)

        painter.end()


class MplCanvas(FigureCanvasQTAgg):
    """matplotlib 3D canvas embedded in PyQt6"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#1a1a2e')
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Cube vertices
        self.cube_verts = np.array([
            [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5],
            [0.5,  0.5, -0.5], [-0.5,  0.5, -0.5],
            [-0.5, -0.5,  0.5], [0.5, -0.5,  0.5],
            [0.5,  0.5,  0.5], [-0.5,  0.5,  0.5],
        ])
        self.cube_faces = [
            [self.cube_verts[0], self.cube_verts[1], self.cube_verts[2], self.cube_verts[3]],
            [self.cube_verts[4], self.cube_verts[5], self.cube_verts[6], self.cube_verts[7]],
            [self.cube_verts[0], self.cube_verts[1], self.cube_verts[5], self.cube_verts[4]],
            [self.cube_verts[2], self.cube_verts[3], self.cube_verts[7], self.cube_verts[6]],
            [self.cube_verts[0], self.cube_verts[3], self.cube_verts[7], self.cube_verts[4]],
            [self.cube_verts[1], self.cube_verts[2], self.cube_verts[6], self.cube_verts[5]],
        ]
        self.face_colors = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#1abc9c']
        self._setup_axes()
        self.ax.view_init(elev=20, azim=45)  # 初始视角，用户可自由旋转

    def _setup_axes(self):
        self.ax.set_xlim(-1.5, 1.5)
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_zlim(-1.5, 1.5)
        self.ax.set_xlabel('X', color='#ecf0f1', fontsize=9)
        self.ax.set_ylabel('Y', color='#ecf0f1', fontsize=9)
        self.ax.set_zlabel('Z', color='#ecf0f1', fontsize=9)
        self.ax.tick_params(colors='#7f8c8d', labelsize=7)
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.xaxis.pane.set_edgecolor('#34495e')
        self.ax.yaxis.pane.set_edgecolor('#34495e')
        self.ax.zaxis.pane.set_edgecolor('#34495e')
        self.ax.grid(True, color='#34495e', alpha=0.3)

    def update_pose(self, qw, qx, qy, qz):
        self.ax.clear()
        self._setup_axes()
        R = quaternion_to_rotation_matrix(qw, qx, qy, qz)
        rotated_faces = []
        for face in self.cube_faces:
            rotated_face = [R @ v for v in face]
            rotated_faces.append(rotated_face)
        poly = Poly3DCollection(rotated_faces, alpha=0.7, edgecolor='#ecf0f1', linewidth=0.5)
        poly.set_facecolor(self.face_colors)
        self.ax.add_collection3d(poly)
        # Direction arrow (X axis)
        arrow_start = R @ np.array([0, 0, 0])
        arrow_end = R @ np.array([1.0, 0, 0])
        self.ax.plot3D([arrow_start[0], arrow_end[0]],
                        [arrow_start[1], arrow_end[1]],
                        [arrow_start[2], arrow_end[2]],
                        color='#e74c3c', linewidth=3)
        # World axes reference
        axis_len = 1.2
        self.ax.plot3D([0, axis_len], [0, 0], [0, 0], color='#e74c3c', linewidth=1, alpha=0.5)
        self.ax.plot3D([0, 0], [0, axis_len], [0, 0], color='#2ecc71', linewidth=1, alpha=0.5)
        self.ax.plot3D([0, 0], [0, 0], [0, axis_len], color='#3498db', linewidth=1, alpha=0.5)
        self.fig.tight_layout()
        self.draw_idle()


class SensorViewerDialog(QDialog):
    """Sensor attitude viewer dialog - English UI"""

    def __init__(self, parser: SensorDataParser, parent=None):
        super().__init__(parent)
        self.parser = parser
        self.current_sensor_id = 1
        self.setWindowTitle("Sensor Attitude Viewer")
        self.resize(950, 680)
        self.setStyleSheet("QWidget { background-color: #1a1a2e; color: #ecf0f1; }")
        self._init_ui()
        # Refresh timer (20Hz for matplotlib software rendering)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_view)
        self.refresh_timer.start(50)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # ===== Left: Human figure with sensor nodes =====
        left_panel = QVBoxLayout()
        title_label = QLabel("Sensor Map")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #e94560;")
        left_panel.addWidget(title_label)

        self.human_figure = HumanFigureWidget(self.parser, self)
        self.human_figure.sensor_selected.connect(self._on_sensor_selected)
        left_panel.addWidget(self.human_figure)

        self.online_label = QLabel("Online: 0/13")
        self.online_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.online_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(self.online_label)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setFixedWidth(240)
        main_layout.addWidget(left_widget)

        # ===== Right: 3D view + status =====
        right_panel = QVBoxLayout()

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #e94560;")
        right_panel.addWidget(self.title_label)

        self.canvas = MplCanvas(self)
        right_panel.addWidget(self.canvas, stretch=1)

        # Status group
        status_group = QGroupBox("Status")
        status_group.setStyleSheet("""
            QGroupBox { color: #ecf0f1; border: 1px solid #0f3460; border-radius: 4px; margin-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; }
        """)
        status_layout = QHBoxLayout()

        self.stationary_label = QLabel("● Moving")
        self.stationary_label.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: bold;")
        status_layout.addWidget(self.stationary_label)

        self.cal_label = QLabel("Cal: Not Calibrated")
        self.cal_label.setStyleSheet("color: #f39c12; font-size: 14px;")
        status_layout.addWidget(self.cal_label)

        self.fresh_label = QLabel("Data: --")
        self.fresh_label.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        status_layout.addWidget(self.fresh_label)

        self.quat_label = QLabel("q: --")
        self.quat_label.setStyleSheet("color: #3498db; font-size: 12px; font-family: monospace;")
        status_layout.addWidget(self.quat_label)

        status_layout.addStretch()
        status_group.setLayout(status_layout)
        right_panel.addWidget(status_group)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        main_layout.addWidget(right_widget, stretch=1)

        # Set default selection after all widgets are created
        self._on_sensor_selected(1)

    def _on_sensor_selected(self, sensor_id: int):
        self.current_sensor_id = sensor_id
        name = SENSOR_NAMES_EN.get(sensor_id, f"ID{sensor_id}")
        self.title_label.setText(f"Sensor {sensor_id}: {name}")
        self.human_figure.set_selected(sensor_id)

    def _refresh_view(self):
        sensor = self.parser.get_sensor(self.current_sensor_id)
        if sensor is None or not sensor.valid:
            self.fresh_label.setText("Data: No Data")
            self.quat_label.setText("q: --")
            return

        # Update 3D cube
        self.canvas.update_pose(sensor.qw, sensor.qx, sensor.qy, sensor.qz)

        # Update status labels
        if sensor.is_stationary:
            self.stationary_label.setText("● Stationary")
            self.stationary_label.setStyleSheet("color: #27ae60; font-size: 14px; font-weight: bold;")
        else:
            self.stationary_label.setText("● Moving")
            self.stationary_label.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: bold;")

        if sensor.is_cal_valid:
            self.cal_label.setText("Cal: Calibrated")
            self.cal_label.setStyleSheet("color: #27ae60; font-size: 14px;")
        else:
            self.cal_label.setText("Cal: Not Calibrated")
            self.cal_label.setStyleSheet("color: #f39c12; font-size: 14px;")

        if sensor.is_fresh:
            self.fresh_label.setText("Data: Live")
            self.fresh_label.setStyleSheet("color: #27ae60; font-size: 14px;")
        else:
            self.fresh_label.setText("Data: Timeout")
            self.fresh_label.setStyleSheet("color: #e74c3c; font-size: 14px;")

        self.quat_label.setText(
            f"q: [{sensor.qw:+.3f}, {sensor.qx:+.3f}, {sensor.qy:+.3f}, {sensor.qz:+.3f}]"
        )

        # Update online count
        active = self.parser.get_active_count()
        self.online_label.setText(f"Online: {active}/13")

        # Trigger human figure repaint (to update node colors)
        self.human_figure.update()

    def closeEvent(self, event):
        self.refresh_timer.stop()
        super().closeEvent(event)

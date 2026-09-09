'''
3D人偶显示组件，用13关节相对转角实时驱动
matplotlib 3D渲染，增量更新避免卡顿
'''
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D


def euler_yxz_to_matrix(y_deg, x_deg, z_deg):
    """YXZ欧拉角(度)转3x3旋转矩阵"""
    y, x, z = np.radians([y_deg, x_deg, z_deg])
    Ry = np.array([[np.cos(y),0,np.sin(y)],[0,1,0],[-np.sin(y),0,np.cos(y)]])
    Rx = np.array([[1,0,0],[0,np.cos(x),-np.sin(x)],[0,np.sin(x),np.cos(x)]])
    Rz = np.array([[np.cos(z),-np.sin(z),0],[np.sin(z),np.cos(z),0],[0,0,1]])
    return Ry @ Rx @ Rz


class Skeleton3DWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 500)
        self._angles = {i: [0.0,0.0,0.0] for i in range(1,14)}
        self._connected = False
        self._scale = 0.01
        self._debug_count = 0

        # 骨骼: (name, imu_id, parent, offset_cm[x,y,z], color, linewidth)
        self._bones = [
            ("Hips",        1,  -1, [0,0,0],            "#2c3e50", 0),
            ("Hip_L",       2,  0,  [-10.5,-8.8,0],     "#e74c3c", 5),
            ("Thigh_L",     4,  1,  [0,-45.6,0],        "#e74c3c", 5),
            ("Calf_L",      6,  2,  [0,-46.7,0],        "#e74c3c", 5),
            ("Foot_L",      0,  3,  [0,-8,14.5],        "#e74c3c", 3),
            ("Hip_R",       3,  0,  [10.5,-8.8,0],      "#3498db", 5),
            ("Thigh_R",     5,  5,  [0,-45.6,0],        "#3498db", 5),
            ("Calf_R",      7,  6,  [0,-46.7,0],        "#3498db", 5),
            ("Foot_R",      0,  7,  [0,-8,14.5],        "#3498db", 3),
            ("Spine",       8,  0,  [0,48.7,0],         "#27ae60", 6),
            ("UpperArm_L",  10, 9,  [-15,-5,5],         "#27ae60", 4),
            ("ForeArm_L",   12, 10, [0,-25.9,0],        "#27ae60", 4),
            ("Hand_L",      0,  11, [0,-20,0],          "#27ae60", 2.5),
            ("UpperArm_R",  11, 9,  [15,-5,5],          "#f39c12", 4),
            ("ForeArm_R",   13, 13, [0,-25.9,0],        "#f39c12", 4),
            ("Hand_R",      0,  14, [0,-20,0],          "#f39c12", 2.5),
            ("Head",        0,  9,  [0,22,0],           "#f5cba7", 0),
        ]

        self._bone_lines = []   # 骨骼线条对象
        self._joint_points = [] # 关节点对象
        self._head_point = None
        self._board_line = None
        self._text_overlay = None

        self._setup_ui()
        self._init_scene_objects()

        # 节流重绘：收到数据只更新角度，QTimer 15Hz触发重绘
        self._redraw_timer = QTimer(self)
        self._redraw_timer.timeout.connect(self._do_redraw)
        self._redraw_timer.start(66)  # ~15Hz

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.figure = Figure(figsize=(5,6), facecolor='#f5f7fa')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.canvas)
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#f5f7fa')

    def _init_scene_objects(self):
        """初始化场景：坐标轴、地面、创建所有线条对象（初始位置在原点）"""
        self.ax.set_xlim(-0.8, 0.8)
        self.ax.set_ylim(-0.2, 1.8)
        self.ax.set_zlim(-0.8, 0.8)
        self.ax.set_xlabel('X', fontsize=8, color='#7f8c8d')
        self.ax.set_ylabel('Y', fontsize=8, color='#7f8c8d')
        self.ax.set_zlabel('Z', fontsize=8, color='#7f8c8d')
        self.ax.tick_params(labelsize=7, colors='#95a5a6')
        self.ax.view_init(elev=15, azim=-60)
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title('Real-time Skeleton', fontsize=11, color='#2c3e50', pad=10)

        # 未连接提示文字
        self._text_overlay = self.ax.text2D(0.5, 0.5,
            'Connect to device\nto see real-time skeleton',
            transform=self.ax.transAxes, ha='center', va='center',
            fontsize=14, color='#95a5a6')

        # 创建骨骼线条（初始在原点）
        self._bone_lines = []
        for i in range(1, len(self._bones)):
            name, imu, parent, off, color, lw = self._bones[i]
            if lw <= 0:
                self._bone_lines.append(None)
                continue
            line, = self.ax.plot([0,0],[0,0],[0,0], color=color, linewidth=lw,
                                solid_capstyle='round')
            self._bone_lines.append(line)

        # 创建关节点
        self._joint_points = []
        for i, bone in enumerate(self._bones):
            name, imu, parent, off, color, lw = bone
            if imu > 0:
                pt, = self.ax.plot([0],[0],[0], 'o', color=color, markersize=10,
                                  markeredgecolor='white', markeredgewidth=1.5)
                self._joint_points.append((i, pt))
            else:
                self._joint_points.append(None)

        # 头部
        self._head_point, = self.ax.plot([0],[0],[0], 'o', color='#f5cba7',
                                         markersize=22, markeredgecolor='#2c3e50',
                                         markeredgewidth=1)
        # 滑雪板
        self._board_line, = self.ax.plot([0,0],[0,0],[0,0], color='#2c3e50', linewidth=4)

    def update_angles(self, angles: dict):
        """收到BLE数据：只更新角度，不立即重绘（由QTimer节流）"""
        self._angles.update(angles)
        self._connected = True
        self._debug_count += 1
        if self._debug_count <= 3 or self._debug_count % 100 == 0:
            a10 = angles.get(10, [0,0,0])
            a12 = angles.get(12, [0,0,0])
            print(f"[UpdateAngles] #{self._debug_count} s10={a10[0]:.1f},{a10[1]:.1f},{a10[2]:.1f} s12={a12[0]:.1f},{a12[1]:.1f},{a12[2]:.1f}")

    def set_connected(self, connected: bool):
        self._connected = connected
        if not connected:
            self._debug_count = 0

    def _compute_positions(self):
        n = len(self._bones)
        pos = [np.zeros(3) for _ in range(n)]
        rot = [np.eye(3) for _ in range(n)]
        pos[0] = np.array([0, 0.9, 0])
        # 根节点Hips的旋转用传感器1的绝对姿态
        if 1 in self._angles:
            rot[0] = euler_yxz_to_matrix(*self._angles[1])
        for i in range(1, n):
            name, imu, parent, off_cm, color, lw = self._bones[i]
            offset = np.array(off_cm) * self._scale
            if imu > 0 and imu in self._angles:
                R_rel = euler_yxz_to_matrix(*self._angles[imu])
            else:
                R_rel = np.eye(3)
            rot[i] = rot[parent] @ R_rel
            pos[i] = pos[parent] + rot[parent] @ offset
        return pos

    def _do_redraw(self):
        """QTimer触发的节流重绘：clear+全量重绘，确保渲染生效"""
        # 保存用户视角，clear后恢复
        elev = self.ax.elev
        azim = self.ax.azim
        self.ax.clear()
        self._setup_axes()
        self.ax.view_init(elev=elev, azim=azim)

        if not self._connected:
            self.ax.text2D(0.5, 0.5, 'Connect to device\nto see real-time skeleton',
                          transform=self.ax.transAxes, ha='center', va='center',
                          fontsize=14, color='#95a5a6')
            self.canvas.draw_idle()
            return

        pos = self._compute_positions()

        # 调试：每20帧打印一次前臂位置和角度
        if not hasattr(self, '_redraw_debug'):
            self._redraw_debug = 0
        self._redraw_debug += 1
        if self._redraw_debug % 20 == 0:
            p11 = pos[11]
            a12 = self._angles.get(12, [0,0,0])
            a10 = self._angles.get(10, [0,0,0])
            print(f"[Redraw] #{self._redraw_debug} pos=({p11[0]:.3f},{p11[1]:.3f},{p11[2]:.3f}) s10={a10[0]:.1f},{a10[1]:.1f},{a10[2]:.1f} s12={a12[0]:.1f},{a12[1]:.1f},{a12[2]:.1f}")

        # 画骨骼连线
        for i in range(1, len(self._bones)):
            name, imu, parent, off, color, lw = self._bones[i]
            if lw <= 0:
                continue
            p1, p2 = pos[parent], pos[i]
            self.ax.plot([p1[0],p2[0]], [p1[1],p2[1]], [p1[2],p2[2]],
                        color=color, linewidth=lw, solid_capstyle='round')

        # 画关节点
        for i, bone in enumerate(self._bones):
            name, imu, parent, off, color, lw = bone
            p = pos[i]
            if imu > 0:
                self.ax.scatter(p[0], p[1], p[2], color=color, s=100,
                              edgecolors='white', linewidths=1.5, zorder=5)
                self.ax.text(p[0], p[1], p[2]+0.03, str(imu),
                           fontsize=7, ha='center', color='white', fontweight='bold')
            elif name == 'Head':
                self.ax.scatter(p[0], p[1], p[2], color='#f5cba7', s=400,
                              edgecolors='#2c3e50', linewidths=1, zorder=4)

        # 滑雪板
        foot_l = pos[4]
        foot_r = pos[8]
        cx = (foot_l[0]+foot_r[0])/2
        cy = min(foot_l[1], foot_r[1]) - 0.02
        cz = (foot_l[2]+foot_r[2])/2
        self.ax.plot([cx-0.25, cx+0.25], [cy, cy], [cz, cz],
                    color='#2c3e50', linewidth=4)

        self.canvas.draw_idle()

    def _setup_axes(self):
        """配置坐标轴（每次clear后调用）"""
        self.ax.set_xlim(-0.8, 0.8)
        self.ax.set_ylim(-0.2, 1.8)
        self.ax.set_zlim(-0.8, 0.8)
        self.ax.set_xlabel('X', fontsize=8, color='#7f8c8d')
        self.ax.set_ylabel('Y', fontsize=8, color='#7f8c8d')
        self.ax.set_zlabel('Z', fontsize=8, color='#7f8c8d')
        self.ax.tick_params(labelsize=7, colors='#95a5a6')
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title('Real-time Skeleton', fontsize=11, color='#2c3e50', pad=10)

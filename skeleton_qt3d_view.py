"""
Skeleton3DView - Qt3D + STL 3D人偶组件
用BLE相对转角实时驱动人偶姿态，支持鼠标旋转视角
"""
import os
import math
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal
from PyQt6.QtGui import QVector3D, QQuaternion, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6 import Qt3DCore, Qt3DRender, Qt3DExtras

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')


def euler_to_quaternion(yaw_deg, pitch_deg, roll_deg):
    """YXZ欧拉角(度)转四元数"""
    y, x, z = math.radians(yaw_deg), math.radians(pitch_deg), math.radians(roll_deg)
    cy, sy = math.cos(y / 2), math.sin(y / 2)
    cx, sx = math.cos(x / 2), math.sin(x / 2)
    cz, sz = math.cos(z / 2), math.sin(z / 2)
    # YXZ: R = Ry * Rx * Rz
    w = cy * cx * cz + sy * sx * sz
    qx = cy * sx * cz + sy * cx * sz
    qy = sy * cx * cz - cy * sx * sz
    qz = cy * cx * sz - sy * sx * cz
    return QQuaternion(w, qx, qy, qz)


# 骨骼定义：(名称, 父索引, 偏移(x,y,z), STL文件, 传感器ID或None, 模型偏移)
# 偏移是关节点相对于父关节的位置；模型偏移是STL中心相对于关节点的位置
BONES = [
    ("Hips",        -1, (0, 0.9, 0),      "hips.stl",      1,  (0, 0, 0)),
    ("Spine",        0, (0, 0.15, 0),     "spine.stl",     None, (0, 0.06, 0)),
    ("Head",         1, (0, 0.20, 0),     "head.stl",      None, (0, 0.06, 0)),
    ("UpperArm_L",   1, (-0.11, 0.10, 0), "upper_arm.stl", 10,  (0, -0.11, 0)),
    ("ForeArm_L",    3, (0, -0.22, 0),    "forearm.stl",   12,  (0, -0.10, 0)),
    ("Hand_L",       4, (0, -0.20, 0),    "hand.stl",      None, (0, -0.03, 0)),
    ("UpperArm_R",   1, (0.11, 0.10, 0),  "upper_arm.stl", 11,  (0, -0.11, 0)),
    ("ForeArm_R",    6, (0, -0.22, 0),    "forearm.stl",   13,  (0, -0.10, 0)),
    ("Hand_R",       7, (0, -0.20, 0),    "hand.stl",      None, (0, -0.03, 0)),
    ("Thigh_L",      0, (-0.06, -0.04, 0),"thigh.stl",     4,  (0, -0.16, 0)),
    ("Shin_L",       9, (0, -0.32, 0),    "shin.stl",      6,  (0, -0.15, 0)),
    ("Foot_L",      10, (0, -0.30, 0),    "foot.stl",      8,  (0, -0.015, 0.04)),
    ("Thigh_R",      0, (0.06, -0.04, 0), "thigh.stl",     5,  (0, -0.16, 0)),
    ("Shin_R",      12, (0, -0.32, 0),    "shin.stl",      7,  (0, -0.15, 0)),
    ("Foot_R",      13, (0, -0.30, 0),    "foot.stl",      9,  (0, -0.015, 0.04)),
]


class BoneEntity:
    """单个骨骼：关节实体(位置+旋转) + 模型子实体(网格偏移)"""
    def __init__(self, view, name, parent_idx, offset, stl_file, sensor_id, model_offset, color):
        self.name = name
        self.parent_idx = parent_idx
        self.offset = QVector3D(*offset)
        self.model_offset = QVector3D(*model_offset)
        self.sensor_id = sensor_id

        # 关节实体：负责位置和旋转（绕关节点旋转）
        self.entity = Qt3DCore.QEntity(view.root_entity)
        self.joint_transform = Qt3DCore.QTransform()
        self.joint_transform.setTranslation(self.offset)
        self.entity.addComponent(self.joint_transform)

        # 模型实体：作为关节实体的子节点，负责网格偏移
        self.mesh_entity = Qt3DCore.QEntity(self.entity)
        mesh_transform = Qt3DCore.QTransform()
        mesh_transform.setTranslation(self.model_offset)
        self.mesh_entity.addComponent(mesh_transform)

        # 网格
        mesh = Qt3DRender.QMesh()
        mesh.setSource(QUrl.fromLocalFile(os.path.join(MODELS_DIR, stl_file)))
        self.mesh_entity.addComponent(mesh)

        # 材质
        mat = Qt3DExtras.QPhongMaterial()
        mat.setDiffuse(QColor(*color))
        mat.setAmbient(QColor(color[0] // 3, color[1] // 3, color[2] // 3))
        mat.setShininess(80)
        self.mesh_entity.addComponent(mat)


class Qt3DSkeletonWidget(QWidget):
    """Qt3D人偶Widget，嵌入主界面右侧"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angles = {}
        self._connected = False
        self._debug_count = 0

        # 创建Qt3D窗口
        self.view = Qt3DExtras.Qt3DWindow()
        self.view.defaultFrameGraph().setClearColor(QColor(30, 30, 40))

        # 容器
        self.container = QWidget.createWindowContainer(self.view)
        self.container.setMinimumSize(300, 400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.container)

        # 根实体
        self.root_entity = Qt3DCore.QEntity()

        # 相机
        self.camera = self.view.camera()
        self.camera.lens().setPerspectiveProjection(45, 1.0, 0.1, 100)
        self.camera.setPosition(QVector3D(0, 1.2, 2.5))
        self.camera.setViewCenter(QVector3D(0, 0.9, 0))
        self.camera.setUpVector(QVector3D(0, 1, 0))

        # 相机控制器（鼠标旋转/缩放）
        self.cam_controller = Qt3DExtras.QOrbitCameraController(self.root_entity)
        self.cam_controller.setCamera(self.camera)
        self.cam_controller.setLinearSpeed(2.0)
        self.cam_controller.setLookSpeed(180)

        # 光照
        self._setup_lights()

        # 地面（参考平面）
        self._create_ground()

        # 创建骨骼
        self.bones = []
        self._create_bones()

        # 设置父子关系
        for i, bone in enumerate(self.bones):
            if bone.parent_idx >= 0:
                bone.entity.setParent(self.bones[bone.parent_idx].entity)

        # 滑雪板和雪杖（装饰）
        self._create_ski_gear()

        # 设置根实体
        self.view.setRootEntity(self.root_entity)

        # 重绘定时器（Qt3D自动渲染，不需要手动重绘，但需要更新变换）
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_poses)
        self._update_timer.start(33)  # ~30Hz更新姿态

    def _setup_lights(self):
        """设置光源"""
        # 点光源（上方）
        point_light = Qt3DRender.QPointLight()
        point_light.setColor(QColor(255, 255, 255))
        point_light.setIntensity(0.6)
        point_transform = Qt3DCore.QTransform()
        point_transform.setTranslation(QVector3D(0, 3, 2))
        point_entity = Qt3DCore.QEntity(self.root_entity)
        point_entity.addComponent(point_light)
        point_entity.addComponent(point_transform)

        # 主方向光
        dir_light = Qt3DRender.QDirectionalLight()
        dir_light.setColor(QColor(255, 240, 220))
        dir_light.setIntensity(0.7)
        dir_light.setWorldDirection(QVector3D(-0.5, -1, -0.5))
        dir_entity = Qt3DCore.QEntity(self.root_entity)
        dir_entity.addComponent(dir_light)

    def _create_ground(self):
        """创建地面参考平面"""
        ground_entity = Qt3DCore.QEntity(self.root_entity)
        ground_mesh = Qt3DCore.QEntity()  # 用平面网格
        # 用一个大的扁平长方体当地面
        plane = Qt3DExtras.QCuboidMesh()
        plane.setXExtent(3.0)
        plane.setYExtent(0.01)
        plane.setZExtent(3.0)
        ground_entity.addComponent(plane)
        ground_mat = Qt3DExtras.QPhongMaterial()
        ground_mat.setDiffuse(QColor(60, 60, 70))
        ground_entity.addComponent(ground_mat)
        ground_transform = Qt3DCore.QTransform()
        ground_transform.setTranslation(QVector3D(0, 0, 0))
        ground_entity.addComponent(ground_transform)

    def _create_bones(self):
        """创建所有骨骼实体"""
        # 颜色：左侧蓝色系，右侧红色系，中间灰色
        left_color = (80, 140, 255)
        right_color = (255, 100, 80)
        center_color = (200, 200, 200)

        for name, parent_idx, offset, stl_file, sensor_id, model_offset in BONES:
            if '_L' in name:
                color = left_color
            elif '_R' in name:
                color = right_color
            else:
                color = center_color
            bone = BoneEntity(self, name, parent_idx, offset, stl_file, sensor_id, model_offset, color)
            self.bones.append(bone)

    def _create_ski_gear(self):
        """创建滑雪板和雪杖（装饰，固定在脚上和手上）"""
        # 滑雪板（左右脚各一个，作为Foot的子实体）
        for foot_idx in [11, 14]:
            ski_entity = Qt3DCore.QEntity(self.bones[foot_idx].entity)
            ski_mesh = Qt3DRender.QMesh()
            ski_mesh.setSource(QUrl.fromLocalFile(os.path.join(MODELS_DIR, 'ski.stl')))
            ski_entity.addComponent(ski_mesh)
            ski_mat = Qt3DExtras.QPhongMaterial()
            ski_mat.setDiffuse(QColor(255, 255, 255))
            ski_entity.addComponent(ski_mat)
            ski_transform = Qt3DCore.QTransform()
            ski_transform.setTranslation(QVector3D(0, -0.03, 0.1))
            ski_entity.addComponent(ski_transform)

        # 雪杖（左右手各一个）
        for hand_idx, side in [(5, -1), (8, 1)]:
            pole_entity = Qt3DCore.QEntity(self.bones[hand_idx].entity)
            pole_mesh = Qt3DRender.QMesh()
            pole_mesh.setSource(QUrl.fromLocalFile(os.path.join(MODELS_DIR, 'pole.stl')))
            pole_entity.addComponent(pole_mesh)
            pole_mat = Qt3DExtras.QPhongMaterial()
            pole_mat.setDiffuse(QColor(180, 180, 180))
            pole_entity.addComponent(pole_mat)
            pole_transform = Qt3DCore.QTransform()
            pole_transform.setTranslation(QVector3D(side * 0.02, -0.30, 0))
            pole_entity.addComponent(pole_transform)

    def update_angles(self, angles: dict):
        """收到BLE角度数据，保存供定时器更新"""
        self._angles.update(angles)
        self._connected = True

    def set_connected(self, connected: bool):
        self._connected = connected

    def _update_poses(self):
        """根据当前角度更新所有骨骼的旋转"""
        # 计算每个骨骼的世界旋转（父旋转 * 相对旋转）
        world_rot = [QQuaternion()] * len(self.bones)

        for i, bone in enumerate(self.bones):
            # 相对旋转
            if bone.sensor_id and bone.sensor_id in self._angles:
                y, x, z = self._angles[bone.sensor_id]
                rel_rot = euler_to_quaternion(y, x, z)
            else:
                rel_rot = QQuaternion()  # 单位四元数

            # 世界旋转 = 父世界旋转 * 相对旋转
            if bone.parent_idx >= 0:
                world_rot[i] = world_rot[bone.parent_idx] * rel_rot
            else:
                world_rot[i] = rel_rot

            # 设置关节变换：位置=偏移，旋转=相对旋转（绕关节点）
            bone.joint_transform.setTranslation(bone.offset)
            bone.joint_transform.setRotation(rel_rot)

        # 调试
        self._debug_count += 1
        if self._debug_count % 100 == 0:
            s12 = self._angles.get(12, [0, 0, 0])
            print(f"[Qt3D] #{self._debug_count} s12={s12[0]:.1f},{s12[1]:.1f},{s12[2]:.1f}")

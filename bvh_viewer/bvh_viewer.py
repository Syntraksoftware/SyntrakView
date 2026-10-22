"""
独立BVH查看器 - 从0开始，直接用BVH原始骨骼结构显示3D动作
用于验证BVH解析和世界旋转计算是否正确，与Blender对比
"""
import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QFileDialog,
                             QSpinBox)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.Qt3DCore import QEntity, QTransform
from PyQt6.Qt3DExtras import Qt3DWindow, QPhongMaterial, QCylinderMesh, QSphereMesh
from PyQt6.QtGui import QVector3D, QQuaternion, QColor


class BVHJoint:
    """BVH关节"""
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.offset = QVector3D(0, 0, 0)
        self.channels = []  # 通道列表，如 ['Xposition', 'Yposition', 'Zposition', 'Zrotation', 'Xrotation', 'Yrotation']
        self.children = []
        self.channel_start = 0  # 在帧数据中的起始索引


class BVHLoader:
    """BVH文件加载器"""
    def __init__(self):
        self.root_joint = None
        self.joints = []  # 按遍历顺序的关节列表
        self.num_channels = 0
        self.num_frames = 0
        self.frame_time = 0.016667
        self.frame_data = None  # numpy array (num_frames, num_channels)
        self.current_frame = 0

    def load(self, filepath):
        """加载BVH文件"""
        # 重置所有状态
        self.root_joint = None
        self.joints = []
        self.num_channels = 0
        self.num_frames = 0
        self.frame_time = 0.016667
        self.frame_data = None
        self.current_frame = 0
        self.scale = 0.01  # BVH单位通常是厘米，转换为米

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # 解析HIERARCHY部分
        i = 0
        parent_stack = []
        in_end_site = False
        channel_offset = 0

        while i < len(lines):
            line = lines[i].strip()
            parts = line.split()

            if line.startswith('HIERARCHY'):
                i += 1
                continue
            elif line.startswith('ROOT') or line.startswith('JOINT'):
                name = parts[1]
                if parent_stack:
                    joint = BVHJoint(name, parent_stack[-1])
                    parent_stack[-1].children.append(joint)
                else:
                    joint = BVHJoint(name, None)
                    self.root_joint = joint
                joint.channel_start = channel_offset
                self.joints.append(joint)
                parent_stack.append(joint)
                i += 1
                continue
            elif line.startswith('End Site'):
                in_end_site = True
                i += 1
                continue
            elif line.startswith('OFFSET'):
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                if parent_stack and not in_end_site:
                    # offset先保存原始值，使用时再缩放
                    parent_stack[-1].offset_raw = QVector3D(x, y, z)
                    parent_stack[-1].offset = QVector3D(x, y, z)
                i += 1
                continue
            elif line.startswith('CHANNELS'):
                num_ch = int(parts[1])
                channels = parts[2:2+num_ch]
                if parent_stack:
                    parent_stack[-1].channels = channels
                    channel_offset += num_ch
                i += 1
                continue
            elif line == '}':
                if in_end_site:
                    in_end_site = False
                elif parent_stack:
                    parent_stack.pop()
                i += 1
                continue
            elif line.startswith('MOTION'):
                break
            i += 1

        self.num_channels = channel_offset

        # 解析MOTION部分
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('Frames:'):
                self.num_frames = int(line.split(':')[1].strip())
            elif line.startswith('Frame Time:'):
                self.frame_time = float(line.split(':')[1].strip())
            elif line and line[0].isdigit() or (line and line[0] == '-'):
                # 帧数据开始
                break
            i += 1

        # 读取帧数据
        frame_lines = []
        while i < len(lines):
            line = lines[i].strip()
            if line:
                frame_lines.append(line)
            i += 1

        if frame_lines:
            self.frame_data = np.zeros((len(frame_lines), self.num_channels))
            for idx, fl in enumerate(frame_lines):
                values = [float(v) for v in fl.split()]
                self.frame_data[idx] = values[:self.num_channels]

        print(f"[BVH] 加载完成: {filepath}")
        print(f"  关节数: {len(self.joints)}")
        print(f"  通道数: {self.num_channels}")
        print(f"  帧数: {self.num_frames}")
        print(f"  帧间隔: {self.frame_time}s ({1/self.frame_time:.1f}fps)")
        print(f"  关节列表: {[j.name for j in self.joints]}")
        return True

    def get_joint_rotation(self, joint, frame_idx):
        """获取指定关节在指定帧的旋转四元数（相对父关节）"""
        if frame_idx >= self.num_frames:
            return QQuaternion()

        frame = self.frame_data[frame_idx]
        rot_channels = [(c, joint.channel_start + i) for i, c in enumerate(joint.channels) if 'rotation' in c]

        # 按通道顺序构建四元数
        q = QQuaternion(1, 0, 0, 0)  # 单位四元数
        for ch_name, ch_idx in rot_channels:
            angle = frame[ch_idx]
            if ch_name == 'Xrotation':
                axis = QVector3D(1, 0, 0)
            elif ch_name == 'Yrotation':
                axis = QVector3D(0, 1, 0)
            elif ch_name == 'Zrotation':
                axis = QVector3D(0, 0, 1)
            else:
                continue
            q = q * QQuaternion.fromAxisAndAngle(axis, angle)

        return q

    def get_joint_position(self, joint, frame_idx):
        """获取指定关节在指定帧的位置偏移（相对父关节，已缩放为米）"""
        if frame_idx >= self.num_frames:
            return joint.offset * self.scale

        frame = self.frame_data[frame_idx]
        pos = QVector3D(joint.offset * self.scale)

        for i, ch in enumerate(joint.channels):
            ch_idx = joint.channel_start + i
            if ch == 'Xposition':
                pos.setX(frame[ch_idx] * self.scale)
            elif ch == 'Yposition':
                pos.setY(frame[ch_idx] * self.scale)
            elif ch == 'Zposition':
                pos.setZ(frame[ch_idx] * self.scale)

        return pos

    def compute_world_transforms(self, frame_idx):
        """计算指定帧所有关节的世界位置和旋转（迭代版，避免栈溢出）"""
        world_pos = {}
        world_rot = {}

        if not self.root_joint:
            return world_pos, world_rot

        # 用显式栈迭代遍历
        stack = [(self.root_joint, QVector3D(0, 0, 0), QQuaternion(1, 0, 0, 0))]
        while stack:
            joint, parent_pos, parent_rot = stack.pop()
            rel_pos = self.get_joint_position(joint, frame_idx)
            rel_rot = self.get_joint_rotation(joint, frame_idx)

            w_rot = parent_rot * rel_rot
            w_pos = parent_pos + parent_rot.rotatedVector(rel_pos)

            world_pos[joint.name] = w_pos
            world_rot[joint.name] = w_rot

            # 子关节入栈（顺序不影响结果）
            for child in joint.children:
                stack.append((child, w_pos, w_rot))

        return world_pos, world_rot


class SkeletonEntity:
    """3D骨骼实体"""
    def __init__(self, root_entity, joints):
        self.root_entity = root_entity
        self.joints = joints
        self.joint_entities = {}  # name -> (sphere_entity, transform)
        self.bone_entities = []   # [(cylinder_entity, transform, parent_name, child_name)]

        # 创建关节球体
        for joint in joints:
            entity = QEntity(root_entity)
            mesh = QSphereMesh()
            mesh.setRadius(0.03)
            material = QPhongMaterial()
            if 'Left' in joint.name or 'left' in joint.name or '_L' in joint.name:
                material.setDiffuse(QColor(100, 200, 100))  # 左侧绿色
            elif 'Right' in joint.name or 'right' in joint.name or '_R' in joint.name:
                material.setDiffuse(QColor(200, 100, 200))  # 右侧紫色
            else:
                material.setDiffuse(QColor(200, 200, 200))  # 中间灰色
            entity.addComponent(mesh)
            entity.addComponent(material)
            transform = QTransform()
            entity.addComponent(transform)
            self.joint_entities[joint.name] = (entity, transform)

        # 创建骨骼圆柱体
        for joint in joints:
            for child in joint.children:
                entity = QEntity(root_entity)
                mesh = QCylinderMesh()
                mesh.setRadius(0.015)
                mesh.setLength(0.1)  # 默认长度
                material = QPhongMaterial()
                material.setDiffuse(QColor(180, 180, 180))
                entity.addComponent(mesh)
                entity.addComponent(material)
                transform = QTransform()
                entity.addComponent(transform)
                self.bone_entities.append((entity, transform, mesh, joint.name, child.name))

    def update(self, world_pos, world_rot):
        """更新骨骼位置"""
        # 更新关节位置
        for name, (entity, transform) in self.joint_entities.items():
            if name in world_pos:
                transform.setTranslation(world_pos[name])

        # 更新骨骼位置和方向
        for entity, transform, mesh, parent_name, child_name in self.bone_entities:
            if parent_name in world_pos and child_name in world_pos:
                p1 = world_pos[parent_name]
                p2 = world_pos[child_name]
                mid = (p1 + p2) * 0.5
                direction = p2 - p1
                length = direction.length()

                if length > 0.001:
                    # 圆柱体默认沿Y轴，需要旋转到direction方向
                    default_dir = QVector3D(0, 1, 0)
                    q = QQuaternion.rotationTo(default_dir, direction.normalized())
                    transform.setRotation(q)
                    transform.setTranslation(mid)
                    # 设置圆柱体高度
                    mesh.setLength(length)


class BVHViewer(QMainWindow):
    """BVH查看器主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BVH Viewer - 独立验证程序")
        self.resize(1200, 800)

        self.loader = BVHLoader()
        self.skeleton = None
        self.playing = False
        self.play_speed = 1.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timer)

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 3D视图
        self.view = Qt3DWindow()
        self.view.defaultFrameGraph().setClearColor(QColor(30, 30, 40))
        container = QWidget.createWindowContainer(self.view)
        container.setMinimumSize(800, 600)
        layout.addWidget(container)

        # 根实体
        self.root_entity = QEntity()
        self.view.setRootEntity(self.root_entity)

        # 相机
        camera = self.view.camera()
        camera.lens().setPerspectiveProjection(45, 16/9, 0.1, 1000)
        camera.setPosition(QVector3D(0, 1.5, 3))
        camera.setViewCenter(QVector3D(0, 1, 0))

        # 灯光
        light_entity = QEntity(self.root_entity)
        from PyQt6.Qt3DRender import QPointLight
        light = QPointLight()
        light.setIntensity(1.0)
        light_entity.addComponent(light)
        light_transform = QTransform()
        light_transform.setTranslation(QVector3D(5, 10, 5))
        light_entity.addComponent(light_transform)

        # 控制栏
        ctrl_layout = QHBoxLayout()

        self.open_btn = QPushButton("Open BVH")
        self.open_btn.clicked.connect(self.on_open)
        ctrl_layout.addWidget(self.open_btn)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.on_play_pause)
        ctrl_layout.addWidget(self.play_btn)

        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 400)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix("%")
        self.speed_spin.valueChanged.connect(self.on_speed_change)
        ctrl_layout.addWidget(QLabel("Speed:"))
        ctrl_layout.addWidget(self.speed_spin)

        self.frame_label = QLabel("Frame: 0/0")
        ctrl_layout.addWidget(self.frame_label)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # 进度条
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        layout.addWidget(self.slider)

        self._slider_pressed = False

    def on_open(self):
        """打开BVH文件"""
        filepath, _ = QFileDialog.getOpenFileName(self, "Open BVH", "", "BVH Files (*.bvh)")
        if filepath:
            self.loader.load(filepath)
            self.slider.setRange(0, self.loader.num_frames - 1)
            self.frame_label.setText(f"Frame: 0/{self.loader.num_frames - 1}")

            # 创建骨骼
            if self.skeleton:
                # 清除旧骨骼
                for name, (entity, _) in self.skeleton.joint_entities.items():
                    entity.setParent(QEntity())  # 设置为空父实体，确保从场景中移除
                    entity.setEnabled(False)
                for entity, _, _, _, _ in self.skeleton.bone_entities:
                    entity.setParent(QEntity())
                    entity.setEnabled(False)

            self.skeleton = SkeletonEntity(self.root_entity, self.loader.joints)
            self.update_frame(0)

            # 自动调整相机位置
            self.adjust_camera()

    def on_play_pause(self):
        """播放/暂停"""
        if self.loader.frame_data is None:
            return
        self.playing = not self.playing
        if self.playing:
            self.play_btn.setText("Pause")
            self.timer.start(16)  # ~60fps
        else:
            self.play_btn.setText("Play")
            self.timer.stop()

    def on_speed_change(self, value):
        """速度改变"""
        self.play_speed = value / 100.0

    def on_timer(self):
        """定时器回调"""
        if self._slider_pressed:
            return
        next_frame = self.loader.current_frame + self.play_speed
        if next_frame >= self.loader.num_frames:
            next_frame = 0  # 循环
        self.loader.current_frame = int(next_frame)
        self.update_frame(self.loader.current_frame)

    def on_slider_moved(self, value):
        """进度条拖动"""
        self.update_frame(value)

    def on_slider_pressed(self):
        self._slider_pressed = True

    def on_slider_released(self):
        self._slider_pressed = False
        self.loader.current_frame = self.slider.value()

    def adjust_camera(self):
        """根据骨骼位置范围自动调整相机"""
        if self.loader.frame_data is None:
            return
        world_pos, _ = self.loader.compute_world_transforms(0)
        if not world_pos:
            return

        # 计算所有关节位置的范围
        all_pos = list(world_pos.values())
        min_x = min(p.x() for p in all_pos)
        max_x = max(p.x() for p in all_pos)
        min_y = min(p.y() for p in all_pos)
        max_y = max(p.y() for p in all_pos)
        min_z = min(p.z() for p in all_pos)
        max_z = max(p.z() for p in all_pos)

        center = QVector3D((min_x+max_x)/2, (min_y+max_y)/2, (min_z+max_z)/2)
        size = max(max_x-min_x, max_y-min_y, max_z-min_z)
        distance = size * 2.5 + 1.0

        camera = self.view.camera()
        camera.setPosition(QVector3D(center.x(), center.y() + size*0.3, center.z() + distance))
        camera.setViewCenter(center)
        print(f"[Camera] 骨骼范围: x[{min_x:.2f},{max_x:.2f}] y[{min_y:.2f},{max_y:.2f}] z[{min_z:.2f},{max_z:.2f}]")
        print(f"[Camera] 中心: {center.x():.2f}, {center.y():.2f}, {center.z():.2f}, 距离: {distance:.2f}")

    def update_frame(self, frame_idx):
        """更新指定帧"""
        if self.loader.frame_data is None or self.skeleton is None:
            return
        if frame_idx >= self.loader.num_frames:
            frame_idx = self.loader.num_frames - 1

        world_pos, world_rot = self.loader.compute_world_transforms(frame_idx)
        self.skeleton.update(world_pos, world_rot)

        self.slider.blockSignals(True)
        self.slider.setValue(frame_idx)
        self.slider.blockSignals(False)
        self.frame_label.setText(f"Frame: {frame_idx}/{self.loader.num_frames - 1}")


def main():
    app = QApplication(sys.argv)
    viewer = BVHViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

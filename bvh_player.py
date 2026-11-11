"""
BVH文件解析和播放器
支持解析BVH文件的关节层级和运动数据，提供逐帧播放接口
"""
import numpy as np
from PyQt6.QtGui import QQuaternion, QVector3D


class BVHJoint:
    """BVH关节节点"""
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = []
        self.offset = QVector3D(0, 0, 0)
        self.channels = []  # 例如 ['Xposition', 'Yposition', 'Zposition', 'Zrotation', 'Xrotation', 'Yrotation']
        self.channel_start_idx = -1  # 在帧数据中的起始索引


class BVHPlayer:
    """BVH文件解析和播放器"""

    # BVH关节名 -> 我们骨骼系统的传感器ID映射
    # 我们的传感器ID: 1=Waist, 2=Hip_Left, 3=Hip_Right, 4=Thigh_Left, 5=Thigh_Right,
    # 6=Calf_Left, 7=Calf_Right, 8=Shoulder_Left, 9=Shoulder_Right,
    # 10=UpperArm_Left, 11=UpperArm_Right, 12=ForeArm_Left, 13=ForeArm_Right
    BONE_TO_SENSOR = {
        # ===== 我们自己的BVH格式（Syntrak录制的文件）=====
        # 我们的BVH面朝+Z，Left=用户左手=屏幕右，需交换到右侧传感器
        'Hips': 1,             # 根节点，映射到传感器1（Waist）
        'Hip_Left': 3,
        'Thigh_Left': 5,
        'Calf_Left': 7,
        'Hip_Right': 2,
        'Thigh_Right': 4,
        'Calf_Right': 6,
        'Shoulder_Left': 9,
        'UpperArm_Left': 11,
        'ForeArm_Left': 13,
        'Shoulder_Right': 8,
        'UpperArm_Right': 10,
        'ForeArm_Right': 12,
        # ===== 通用BVH格式（Mixamo等）=====
        'Pelvis': None,
        'Spine': None,
        'Spine1': None,
        'Spine2': None,
        'Spine3': None,
        'Neck': None,
        'Head': None,
        'LeftShoulder': 8,
        'LeftArm': 10,
        'LeftForeArm': 12,
        'LeftHand': None,
        'RightShoulder': 9,
        'RightArm': 11,
        'RightForeArm': 13,
        'RightHand': None,
        'LeftUpLeg': 4,
        'LeftLeg': 6,
        'LeftFoot': None,
        'LeftToeBase': None,
        'RightUpLeg': 5,
        'RightLeg': 7,
        'RightFoot': None,
        'RightToeBase': None,
        'LeftHip': 2,
        'RightHip': 3,
        'HipLeft': 2,
        'HipRight': 3,
    }

    @classmethod
    def fuzzy_match_sensor(cls, joint_name):
        """
        模糊匹配关节名到传感器ID。
        支持多种命名约定：Syntrak格式、Mixamo格式、Virdyn格式等。
        返回传感器ID (1-13) 或 None（根节点/无传感器关节）
        """
        name = joint_name.lower().strip()

        # 根节点和无传感器关节
        if name in ('hips', 'pelvis', 'root', 'spine', 'spine1', 'spine2', 'spine3',
                     'neck', 'head', 'hand', 'foot', 'toe'):
            return None
        if any(x in name for x in ('finger', 'thumb', 'toe')):
            return None
        if name == 'hips' or name.endswith('hips'):
            return None

        # 判断左右
        is_left = ('left' in name) or name.startswith('l_') or '_l_' in name or name.endswith('_l')
        is_right = ('right' in name) or name.startswith('r_') or '_r_' in name or name.endswith('_r')

        # 按优先级匹配部位（从具体到一般）
        # 大腿
        if any(x in name for x in ('upperleg', 'thigh', 'upleg')):
            return 4 if is_left else (5 if is_right else None)
        # 小腿
        if any(x in name for x in ('lowerleg', 'calf')):
            return 6 if is_left else (7 if is_right else None)
        # 肩部
        if 'shoulder' in name:
            return 8 if is_left else (9 if is_right else None)
        # 上臂
        if 'upperarm' in name or ('arm' in name and 'fore' not in name and 'lower' not in name):
            return 10 if is_left else (11 if is_right else None)
        # 前臂
        if any(x in name for x in ('forearm', 'lowerarm')):
            return 12 if is_left else (13 if is_right else None)
        # 髋部（注意：不要匹配到"hips"）
        if 'hip' in name and 'hips' not in name:
            return 2 if is_left else (3 if is_right else None)
        # 一般的leg（如果不是upperleg/lowerleg）
        if 'leg' in name and 'upper' not in name and 'lower' not in name:
            return 6 if is_left else (7 if is_right else None)

        return None  # 未匹配

    def __init__(self):
        self.root_joint = None
        self.joints = {}  # name -> BVHJoint
        self.num_frames = 0
        self.frame_time = 0.033333  # 默认30fps
        self.frame_data = None  # numpy array (num_frames, num_channels)
        self.file_path = None
        self.file_size = 0
        self.num_channels = 0

        # 播放状态
        self.current_frame = 0
        self.playing = False
        self.speed = 1.0
        self.loop = True
        self.retarget = False  # 是否使用世界空间重定向
        self._accumulated_time = 0.0

    def load(self, file_path):
        """加载并解析BVH文件"""
        # 重置所有数据，避免上一个文件的残留
        self.root_joint = None
        self.joints = {}
        self.num_frames = 0
        self.frame_time = 0.033333
        self.frame_data = None
        self.num_channels = 0
        self.current_frame = 0
        self.playing = False
        self._accumulated_time = 0.0

        self.file_path = file_path
        import os
        self.file_size = os.path.getsize(file_path)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # 解析HIERARCHY
        idx = 0
        channel_idx = 0
        parent_stack = []
        in_end_site = False  # 是否在End Site块内

        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith('MOTION'):
                break
            if line.startswith('ROOT') or line.startswith('JOINT'):
                name = line.split()[1]
                if parent_stack:
                    joint = BVHJoint(name, parent_stack[-1])
                    parent_stack[-1].children.append(joint)
                else:
                    joint = BVHJoint(name, None)
                    self.root_joint = joint
                joint.channel_start_idx = channel_idx
                self.joints[name] = joint
                parent_stack.append(joint)
            elif line.startswith('End Site'):
                # End Site没有通道，标记进入End Site块
                in_end_site = True
            elif line.startswith('OFFSET'):
                parts = line.split()
                if parent_stack:
                    parent_stack[-1].offset = QVector3D(
                        float(parts[1]), float(parts[2]), float(parts[3])
                    )
            elif line.startswith('CHANNELS'):
                parts = line.split()
                num_ch = int(parts[1])
                ch_names = parts[2:2+num_ch]
                if parent_stack:
                    parent_stack[-1].channels = ch_names
                    channel_idx += num_ch
            elif line == '}':
                if in_end_site:
                    in_end_site = False  # End Site块结束，不弹栈
                elif parent_stack:
                    parent_stack.pop()
            idx += 1

        self.num_channels = channel_idx

        # 解析MOTION
        idx += 1  # 跳过MOTION行
        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith('Frames:'):
                self.num_frames = int(line.split(':')[1].strip())
            elif line.startswith('Frame Time:'):
                self.frame_time = float(line.split(':')[1].strip())
            elif line:
                # 第一帧数据行，开始解析所有帧
                frame_lines = lines[idx:]
                self.frame_data = np.zeros((self.num_frames, self.num_channels))
                for f_idx, fl in enumerate(frame_lines):
                    if f_idx >= self.num_frames:
                        break
                    values = [float(x) for x in fl.strip().split()]
                    self.frame_data[f_idx] = values[:self.num_channels]
                break
            idx += 1

        print(f"[BVH] 加载完成: {file_path}")
        print(f"  文件大小: {self.file_size} bytes")
        print(f"  关节数: {len(self.joints)}")
        print(f"  通道数: {self.num_channels}")
        print(f"  帧数: {self.num_frames}")
        print(f"  帧间隔: {self.frame_time:.6f}s ({1/self.frame_time:.1f}fps)")
        print(f"  总时长: {self.num_frames * self.frame_time:.2f}s")

        return True

    def get_frame_angles(self, frame_idx):
        """获取指定帧的角度数据，返回 {sensor_id: (y, x, z)} 字典"""
        if self.frame_data is None or frame_idx >= self.num_frames:
            return {}

        angles = {}
        frame = self.frame_data[frame_idx]

        for joint_name, joint in self.joints.items():
            # 优先精确匹配，失败时用模糊匹配
            sensor_id = self.BONE_TO_SENSOR.get(joint_name)
            if sensor_id is None and joint_name not in self.BONE_TO_SENSOR:
                sensor_id = self.fuzzy_match_sensor(joint_name)
            if sensor_id is None:
                continue

            # 从通道中提取旋转
            rot_x = rot_y = rot_z = 0.0
            for ch_offset, ch_name in enumerate(joint.channels):
                idx = joint.channel_start_idx + ch_offset
                if idx >= len(frame):
                    continue
                val = frame[idx]
                if ch_name == 'Xrotation':
                    rot_x = val
                elif ch_name == 'Yrotation':
                    rot_y = val
                elif ch_name == 'Zrotation':
                    rot_z = val

            # 我们自己的BVH文件channels声明为 Yrotation Xrotation Zrotation（YXZ顺序），
            # 数据直接写入 (ey, ex, ez)，与实时BLE发送的格式完全一致，无需转换。
            # _convert_bvh_rotation 的提取公式是ZYX顺序，用于YXZ数据会导致旋转顺序错误。
            angles[sensor_id] = (rot_y, rot_x, rot_z)

        # 处理需要平均的关节（Pelvis用左右髋平均，Spine用左右肩平均）
        # 这些在_update_poses中已经处理了，这里只需要提供单个传感器的数据

        return angles

    def _get_joint_relative_rotation(self, joint, frame):
        """获取单个关节的相对旋转四元数"""
        rot_x = rot_y = rot_z = 0.0
        for ch_offset, ch_name in enumerate(joint.channels):
            idx = joint.channel_start_idx + ch_offset
            if idx >= len(frame):
                continue
            val = frame[idx]
            if ch_name == 'Xrotation':
                rot_x = val
            elif ch_name == 'Yrotation':
                rot_y = val
            elif ch_name == 'Zrotation':
                rot_z = val
        # 按BVH通道顺序构建四元数
        rot_channels = [c for c in joint.channels if 'rotation' in c]
        qx = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), rot_x)
        qy = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), rot_y)
        qz = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), rot_z)
        q = QQuaternion()
        for ch in rot_channels:
            if ch == 'Xrotation':
                q = q * qx
            elif ch == 'Yrotation':
                q = q * qy
            elif ch == 'Zrotation':
                q = q * qz
        return q

    def compute_world_rotations(self, frame_idx):
        """计算指定帧所有关节的世界空间旋转（从根节点累乘，迭代实现避免栈溢出），返回 {joint_name: QQuaternion}"""
        if self.frame_data is None or frame_idx >= self.num_frames:
            return {}
        frame = self.frame_data[frame_idx]
        world_rots = {}

        if self.root_joint:
            # 迭代遍历：栈中存储(joint, parent_world_rot)
            stack = [(self.root_joint, QQuaternion(1, 0, 0, 0))]
            while stack:
                joint, parent_wrot = stack.pop()
                rel_rot = self._get_joint_relative_rotation(joint, frame)
                world_rot = parent_wrot * rel_rot
                world_rots[joint.name] = world_rot
                # 子节点逆序压栈，保证遍历顺序和递归一致
                for child in reversed(joint.children):
                    stack.append((child, world_rot))
        return world_rots

    def get_frame_angles_retargeted(self, frame_idx):
        """
        世界空间重定向：计算BVH关键关节的世界旋转，按我们的骨骼层级反推相对旋转。
        返回 {sensor_id: (y, x, z)}
        """
        world_rots = self.compute_world_rotations(frame_idx)
        if not world_rots:
            return {}

        # 坐标系相似变换：绕Y轴180度，把BVH坐标系（面朝-Z）转换到我们的坐标系（面朝+Z）
        # 公式：Q' = R_180 * Q * R_180^-1，对应四元数变换 (w, x, y, z) -> (w, -x, y, -z)
        # 关键：Q为单位四元数时Q'仍为单位四元数，不会改变初始朝向（第0帧仍朝前）
        # 只转换动作的坐标系表示，使动作方向从"朝后基准"变为"朝前基准"
        world_rots = {name: QQuaternion(q.scalar(), -q.x(), q.y(), -q.z()) for name, q in world_rots.items()}

        def find_world_rot(keywords):
            for name, wrot in world_rots.items():
                nl = name.lower()
                for kw in keywords:
                    if kw.lower() in nl:
                        return wrot
            return None

        def q2euler(q):
            e = q.toEulerAngles()
            return (e.y(), e.x(), e.z())

        # 根节点
        hips_wrot = None
        for n in ('Hips', 'Pelvis', 'Root'):
            if n in world_rots:
                hips_wrot = world_rots[n]
                break
        if hips_wrot is None:
            hips_wrot = QQuaternion()

        # 各关键关节的世界旋转（不交换左右，我们的Left对应BVH的Left）
        hip_l = find_world_rot(['hip_left', 'lefthip', 'l_hip']) or hips_wrot
        hip_r = find_world_rot(['hip_right', 'righthip', 'r_hip']) or hips_wrot
        thigh_l = find_world_rot(['thigh_left', 'leftthigh', 'left_upleg', 'leftupperleg', 'l_thigh'])
        thigh_r = find_world_rot(['thigh_right', 'rightthigh', 'right_upleg', 'rightupperleg', 'r_thigh'])
        shin_l = find_world_rot(['calf_left', 'leftcalf', 'leftleg', 'leftlowerleg', 'l_calf'])
        shin_r = find_world_rot(['calf_right', 'rightcalf', 'rightleg', 'rightlowerleg', 'r_calf'])
        shoulder_l = find_world_rot(['shoulder_left', 'leftshoulder', 'l_shoulder']) or hips_wrot
        shoulder_r = find_world_rot(['shoulder_right', 'rightshoulder', 'r_shoulder']) or hips_wrot
        upperarm_l = find_world_rot(['upperarm_left', 'leftupperarm', 'leftarm', 'l_upperarm', 'l_arm'])
        upperarm_r = find_world_rot(['upperarm_right', 'rightupperarm', 'rightarm', 'r_upperarm', 'r_arm'])
        forearm_l = find_world_rot(['forearm_left', 'leftforearm', 'leftlowerarm', 'l_forearm'])
        forearm_r = find_world_rot(['forearm_right', 'rightforearm', 'rightlowerarm', 'r_forearm'])

        # 中间节点：Pelvis用Hips（Virdyn没有独立髋关节），Spine用最上面的脊椎关节
        pelvis_wrot = hips_wrot
        # 优先用Spine2（中间脊椎），Spine3旋转角度最大可能导致上半身过于前倾
        spine_wrot = (find_world_rot(['spine2', 'spine_2']) or
                      find_world_rot(['spine3', 'spine_3']) or
                      find_world_rot(['spine1', 'spine_1']) or
                      find_world_rot(['spine']) or
                      shoulder_l)

        result = {}

        # 第103帧详细调试：打印世界旋转四元数
        if frame_idx == 103:
            print(f"=== Frame {frame_idx} World Rotations ===")
            for name in ['Hips', 'Spine', 'Spine1', 'Spine2', 'Spine3',
                          'LeftShoulder', 'LeftUpperArm', 'LeftLowerArm',
                          'RightShoulder', 'RightUpperArm', 'RightLowerArm',
                          'LeftUpperLeg', 'LeftLowerLeg',
                          'RightUpperLeg', 'RightLowerLeg']:
                if name in world_rots:
                    q = world_rots[name]
                    e = q.toEulerAngles()
                    print(f"  {name}: q=({q.scalar():.3f},{q.x():.3f},{q.y():.3f},{q.z():.3f}) euler=({e.x():.1f},{e.y():.1f},{e.z():.1f})")
            print(f"  pelvis_wrot used: {pelvis_wrot is not None}")
            print(f"  spine_wrot used: {spine_wrot is not None}")
            print("=== End ===")

        # 详细调试：打印查找结果
        if not hasattr(self, '_retarget_debug_count'):
            self._retarget_debug_count = 0
        self._retarget_debug_count += 1
        if self._retarget_debug_count <= 3:
            print(f"[Retarget Detail] frame={frame_idx}")
            print(f"  world_rots keys: {sorted(world_rots.keys())[:15]}...")
            print(f"  hips_wrot is None: {hips_wrot is None}")
            print(f"  hip_l is None: {hip_l is None}")
            print(f"  thigh_l is None: {thigh_l is None}")
            print(f"  shin_l is None: {shin_l is None}")
            print(f"  shoulder_l is None: {shoulder_l is None}")
            print(f"  upperarm_l is None: {upperarm_l is None}")
            print(f"  forearm_l is None: {forearm_l is None}")
            # 测试find_world_rot
            test = find_world_rot(['leftupperleg'])
            print(f"  find_world_rot(['leftupperleg']) is None: {test is None}")

        # ========== 正确的重定向逻辑 ==========
        # 我们的骨骼结构：
        #   Hips(根,固定) ─┬─ Pelvis(传感器2/3) ─┬─ Thigh_L(4) ─ Shin_L(6) ─ Foot_L
        #                   │                       └─ Thigh_R(5) ─ Shin_R(7) ─ Foot_R
        #                   └─ Spine(传感器8/9) ─┬─ UpperArm_L(10) ─ ForeArm_L(12)
        #                                           └─ UpperArm_R(11) ─ ForeArm_R(13)
        #
        # BVH对应：
        #   Pelvis ← Hips, Spine ← Spine3
        #   UpperArm ← UpperArm, ForeArm ← LowerArm
        #   Thigh ← UpperLeg, Shin ← LowerLeg
        #
        # 重定向原则：让我们的每个节点的世界旋转 = BVH对应关节的世界旋转
        # 相对旋转 = 父节点世界旋转.inverted() * 目标世界旋转

        # Pelvis（传感器2/3）：父节点Hips固定，所以相对旋转 = 世界旋转 = BVH的Hips世界旋转
        result[2] = q2euler(hips_wrot)
        result[3] = q2euler(hips_wrot)

        # Spine（传感器8/9）：父节点Hips固定，所以相对旋转 = 世界旋转 = BVH的Spine3世界旋转
        result[8] = q2euler(spine_wrot)
        result[9] = q2euler(spine_wrot)

        # UpperArm的T-Pose旋转：我们的骨骼初始向下，T-Pose时向两侧
        # BVH的UpperArm初始就是向两侧，所以需要乘以T-Pose旋转来匹配初始方向
        tpose_arm_l = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), -90)
        tpose_arm_r = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), 90)

        # UpperArm_L（传感器10）：完整相对旋转 = BVH相对旋转 * T-Pose旋转
        # 注意：乘法顺序是 bvh_rel * tpose，因为tpose是骨骼自身的初始方向修正
        if upperarm_l is not None: result[10] = q2euler(spine_wrot.inverted() * upperarm_l * tpose_arm_l)
        if upperarm_r is not None: result[11] = q2euler(spine_wrot.inverted() * upperarm_r * tpose_arm_r)

        # ForeArm（传感器12/13）：我们的ForeArm初始方向向下(Y负)，BVH的ForeArm初始方向向两侧(X方向)
        # 需要我们的ForeArm世界旋转 = BVH的ForeArm世界旋转 * T-Pose，才能让指向一致
        # 推导：ForeArm相对旋转 = T-Pose.inverted() * BVH的UpperArm世界旋转.inverted() * BVH的ForeArm世界旋转 * T-Pose
        if forearm_l is not None and upperarm_l is not None: result[12] = q2euler(tpose_arm_l.inverted() * upperarm_l.inverted() * forearm_l * tpose_arm_l)
        if forearm_r is not None and upperarm_r is not None: result[13] = q2euler(tpose_arm_r.inverted() * upperarm_r.inverted() * forearm_r * tpose_arm_r)

        # Thigh（传感器4/5）：父节点Pelvis，相对旋转 = Pelvis世界旋转.inverted() * Thigh世界旋转
        if thigh_l is not None: result[4] = q2euler(hips_wrot.inverted() * thigh_l)
        if thigh_r is not None: result[5] = q2euler(hips_wrot.inverted() * thigh_r)

        # Shin（传感器6/7）：父节点Thigh，相对旋转 = Thigh世界旋转.inverted() * Shin世界旋转
        if shin_l is not None and thigh_l is not None: result[6] = q2euler(thigh_l.inverted() * shin_l)
        if shin_r is not None and thigh_r is not None: result[7] = q2euler(thigh_r.inverted() * shin_r)

        # 注意：不需要任何坐标系转换！独立BVH查看器已验证直接用原始数据与Blender一致

        # 调试输出
        if not hasattr(self, '_retarget_debug_count'):
            self._retarget_debug_count = 0
        self._retarget_debug_count += 1
        if self._retarget_debug_count % 60 == 0:
            print(f'[Retarget Debug] frame={frame_idx}, keys={sorted(result.keys())}, sample={list(result.items())[:3]}')
        return result

    def _convert_bvh_rotation(self, rot_x, rot_y, rot_z, channels):
        """将BVH旋转转换为我们的(y, x, z)格式"""
        # 确定BVH的旋转顺序
        rot_channels = [c for c in channels if 'rotation' in c]
        order = ''.join([c[0] for c in rot_channels])  # 例如 'ZXY'

        # BVH旋转角度（度）
        rx, ry, rz = np.radians(rot_x), np.radians(rot_y), np.radians(rot_z)

        # 按BVH顺序构建四元数
        qx = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), np.degrees(rx))
        qy = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), np.degrees(ry))
        qz = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), np.degrees(rz))

        # 按顺序相乘
        q = QQuaternion()
        for ch in rot_channels:
            if ch == 'Xrotation':
                q = q * qx
            elif ch == 'Yrotation':
                q = q * qy
            elif ch == 'Zrotation':
                q = q * qz

        # 转换为欧拉角（YXZ顺序，即y, x, z）
        # 使用四元数转欧拉角
        euler = self._quaternion_to_euler_yxz(q)
        return euler

    def _quaternion_to_euler_yxz(self, q):
        """四元数转YXZ欧拉角（返回角度，y, x, z）"""
        # 四元数分量
        w, x, y, z = q.scalar(), q.x(), q.y(), q.z()

        # YXZ顺序的欧拉角提取
        # 参考: https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll_x = np.arctan2(sinr_cosp, cosr_cosp)

        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch_y = np.sign(sinp) * np.pi / 2
        else:
            pitch_y = np.arcsin(sinp)

        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw_z = np.arctan2(siny_cosp, cosy_cosp)

        # 转换为角度，返回(y, x, z)
        return (np.degrees(pitch_y), np.degrees(roll_x), np.degrees(yaw_z))

    def update(self, delta_time):
        """更新播放进度，返回当前帧的角度数据"""
        if not self.playing or self.frame_data is None:
            return None

        self._accumulated_time += delta_time * self.speed
        frame_duration = self.frame_time

        while self._accumulated_time >= frame_duration:
            self._accumulated_time -= frame_duration
            self.current_frame += 1
            if self.current_frame >= self.num_frames:
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = self.num_frames - 1
                    self.playing = False

        if self.retarget:
            return self.get_frame_angles_retargeted(self.current_frame)
        return self.get_frame_angles(self.current_frame)

    def set_retarget(self, enabled):
        self.retarget = enabled

    def play(self):
        self.playing = True

    def pause(self):
        self.playing = False

    def stop(self):
        self.playing = False
        self.current_frame = 0
        self._accumulated_time = 0

    def seek(self, frame_idx):
        self.current_frame = max(0, min(frame_idx, self.num_frames - 1))
        self._accumulated_time = 0

    def set_speed(self, speed):
        self.speed = max(0.1, min(speed, 10.0))

    def set_loop(self, loop):
        self.loop = loop

    def get_progress(self):
        """返回播放进度 0.0 - 1.0"""
        if self.num_frames == 0:
            return 0.0
        return self.current_frame / (self.num_frames - 1)

    def get_current_time(self):
        """返回当前播放时间（秒）"""
        return self.current_frame * self.frame_time

    def get_total_time(self):
        """返回总时长（秒）"""
        return self.num_frames * self.frame_time

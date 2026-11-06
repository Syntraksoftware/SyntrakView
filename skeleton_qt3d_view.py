"""
Skeleton3DView - Qt3D + STL 3D人偶组件
用BLE相对转角实时驱动人偶姿态，支持鼠标旋转视角
支持多套人偶切换（从 models/<名称>/ 子目录加载STL）
"""
import os
import math
import numpy as np
from stl import mesh as stl_mesh
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal
from PyQt6.QtGui import QVector3D, QQuaternion, QColor, QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6 import Qt3DCore, Qt3DRender, Qt3DExtras
from PyQt6.Qt3DRender import (QCullFace, QRenderStateSet, QRenderSurfaceSelector,
                                QViewport, QCameraSelector, QClearBuffers)
from PyQt6.QtCore import QRectF
from PyQt6.Qt3DRender import QCullFace

def _open_shared_angle_log(path, mode="w"):
    """以 Windows 共享模式(FILE_SHARE_READ|WRITE)打开 angle_log.txt，
    使外部程序(记事本/分析脚本)在上位机运行时也能读取，不被独占锁住。
    Python 内置 open() 在 Windows 虽已默认允许共享读，此处显式声明共享，
    确保任何第三方读取(含外部脚本)都不会因句柄独占而失败。"""
    import ctypes
    from ctypes import wintypes
    ctypes.windll.kernel32.CreateFileW.restype = wintypes.HANDLE
    ctypes.windll.kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_ALWAYS = 4
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    h = ctypes.windll.kernel32.CreateFileW(
        path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, None)
    if h is None or h == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    import msvcrt
    import os as _os
    fd = msvcrt.open_osfhandle(h, _os.O_WRONLY)
    fh = _os.fdopen(fd, mode, encoding="utf-8", buffering=1)
    if "a" in mode:
        fh.seek(0, _os.SEEK_END)
    return fh


BASE_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
VIEW_ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pics', 'view_icons')
DEFAULT_AVATAR = 'skier_pro'

# ===== 上位机构建版本标识：每次代码修改务必更新（格式 HOSTYYYYMMDD_HHMM），
# 打印在所有 log（angle_log.txt / console）行首，用于与固件 FW_BUILD_TAG、BLE frame_cnt 对齐，
# 避免"log 与代码版本不对应"。
# 本次=手臂方向修正: BLE实时手臂(Shoulder/UpperArm/ForeArm)pitch(x)+roll(z)取负, 修正手往上显示往下+拧转反; 仅非virdyn路径
HOST_BUILD_TAG = "HOST20261106_2210"

# 各个人偶的配色方案：骨骼名 -> (R,G,B)
AVATAR_COLORS = {
    'skier_pro': {
        'Head':        (220, 180, 150),  # 脸肤色（头盔护目镜同体）
        'Neck':        (220, 180, 150),
        'Spine':       (35, 55, 110),    # 深蓝滑雪服
        'Hips':        (35, 55, 110),
        'UpperArm_L':  (35, 55, 110),
        'UpperArm_R':  (35, 55, 110),
        'ForeArm_L':   (35, 55, 110),
        'ForeArm_R':   (35, 55, 110),
        'Hand_L':      (220, 80, 40),    # 亮橙红手套
        'Hand_R':      (220, 80, 40),
        'Thigh_L':     (30, 40, 75),     # 深靛蓝滑雪裤
        'Thigh_R':     (30, 40, 75),
        'Shin_L':      (30, 40, 75),
        'Shin_R':      (30, 40, 75),
        'Foot_L':      (45, 45, 50),     # 深灰滑雪靴
        'Foot_R':      (45, 45, 50),
    },
    'robot': {
        'Head':        (180, 180, 190),  # 金属灰头
        'Neck':        (150, 150, 160),
        'Spine':       (100, 110, 130),  # 金属蓝灰胸甲
        'Hips':        (90, 100, 120),
        'UpperArm_L':  (110, 120, 140),
        'UpperArm_R':  (110, 120, 140),
        'ForeArm_L':   (100, 110, 130),
        'ForeArm_R':   (100, 110, 130),
        'Hand_L':      (80, 90, 110),
        'Hand_R':      (80, 90, 110),
        'Thigh_L':     (95, 105, 125),
        'Thigh_R':     (95, 105, 125),
        'Shin_L':      (85, 95, 115),
        'Shin_R':      (85, 95, 115),
        'Foot_L':      (70, 80, 100),
        'Foot_R':      (70, 80, 100),
    },
    'stickman': {
        'Head':        (200, 200, 200),
        'Neck':        (180, 180, 180),
        'Spine':       (160, 160, 160),
        'Hips':        (150, 150, 150),
        'UpperArm_L':  (170, 170, 170),
        'UpperArm_R':  (170, 170, 170),
        'ForeArm_L':   (165, 165, 165),
        'ForeArm_R':   (165, 165, 165),
        'Hand_L':      (190, 190, 190),
        'Hand_R':      (190, 190, 190),
        'Thigh_L':     (155, 155, 155),
        'Thigh_R':     (155, 155, 155),
        'Shin_L':      (150, 150, 150),
        'Shin_R':      (150, 150, 150),
        'Foot_L':      (140, 140, 140),
        'Foot_R':      (140, 140, 140),
    },
    # 成年男性：红色滑雪服，黑色裤子
    'male_skier': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (180, 40, 40),
        'Hips':        (180, 40, 40),
        'UpperArm_L':  (180, 40, 40),
        'UpperArm_R':  (180, 40, 40),
        'ForeArm_L':   (180, 40, 40),
        'ForeArm_R':   (180, 40, 40),
        'Hand_L':      (50, 50, 55),
        'Hand_R':      (50, 50, 55),
        'Thigh_L':     (40, 40, 45),
        'Thigh_R':     (40, 40, 45),
        'Shin_L':      (40, 40, 45),
        'Shin_R':      (40, 40, 45),
        'Foot_L':      (45, 45, 50),
        'Foot_R':      (45, 45, 50),
    },
    # 成年女性：紫色滑雪服，深紫裤子，马尾
    'female_skier': {
        'Head':        (230, 190, 160),
        'Neck':        (230, 190, 160),
        'Spine':       (140, 60, 140),
        'Hips':        (140, 60, 140),
        'UpperArm_L':  (140, 60, 140),
        'UpperArm_R':  (140, 60, 140),
        'ForeArm_L':   (140, 60, 140),
        'ForeArm_R':   (140, 60, 140),
        'Hand_L':      (200, 100, 150),
        'Hand_R':      (200, 100, 150),
        'Thigh_L':     (100, 40, 100),
        'Thigh_R':     (100, 40, 100),
        'Shin_L':      (100, 40, 100),
        'Shin_R':      (100, 40, 100),
        'Foot_L':      (60, 30, 60),
        'Foot_R':      (60, 30, 60),
    },
    # 老年人：深绿滑雪服，棕色裤子，略驼背
    'elder_skier': {
        'Head':        (210, 185, 160),
        'Neck':        (210, 185, 160),
        'Spine':       (50, 90, 60),
        'Hips':        (50, 90, 60),
        'UpperArm_L':  (50, 90, 60),
        'UpperArm_R':  (50, 90, 60),
        'ForeArm_L':   (50, 90, 60),
        'ForeArm_R':   (50, 90, 60),
        'Hand_L':      (120, 80, 50),
        'Hand_R':      (120, 80, 50),
        'Thigh_L':     (90, 65, 45),
        'Thigh_R':     (90, 65, 45),
        'Shin_L':      (90, 65, 45),
        'Shin_R':      (90, 65, 45),
        'Foot_L':      (70, 50, 35),
        'Foot_R':      (70, 50, 35),
    },
    # 少年：亮黄滑雪服，蓝色裤子，大头
    'kid_skier': {
        'Head':        (235, 200, 170),
        'Neck':        (235, 200, 170),
        'Spine':       (240, 200, 40),
        'Hips':        (240, 200, 40),
        'UpperArm_L':  (240, 200, 40),
        'UpperArm_R':  (240, 200, 40),
        'ForeArm_L':   (240, 200, 40),
        'ForeArm_R':   (240, 200, 40),
        'Hand_L':      (60, 120, 200),
        'Hand_R':      (60, 120, 200),
        'Thigh_L':     (50, 100, 180),
        'Thigh_R':     (50, 100, 180),
        'Shin_L':      (50, 100, 180),
        'Shin_R':      (50, 100, 180),
        'Foot_L':      (40, 40, 50),
        'Foot_R':      (40, 40, 50),
    },
    # 胖滑雪者：橙色滑雪服，棕色裤子
    'fat_skier': {
        'Head':        (225, 185, 155),
        'Neck':        (225, 185, 155),
        'Spine':       (220, 120, 40),
        'Hips':        (220, 120, 40),
        'UpperArm_L':  (220, 120, 40),
        'UpperArm_R':  (220, 120, 40),
        'ForeArm_L':   (220, 120, 40),
        'ForeArm_R':   (220, 120, 40),
        'Hand_L':      (80, 60, 40),
        'Hand_R':      (80, 60, 40),
        'Thigh_L':     (100, 70, 40),
        'Thigh_R':     (100, 70, 40),
        'Shin_L':      (100, 70, 40),
        'Shin_R':      (100, 70, 40),
        'Foot_L':      (60, 40, 30),
        'Foot_R':      (60, 40, 30),
    },
    # 高个子：青色滑雪服，深灰裤子
    'tall_skier': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (40, 160, 160),
        'Hips':        (40, 160, 160),
        'UpperArm_L':  (40, 160, 160),
        'UpperArm_R':  (40, 160, 160),
        'ForeArm_L':   (40, 160, 160),
        'ForeArm_R':   (40, 160, 160),
        'Hand_L':      (50, 50, 60),
        'Hand_R':      (50, 50, 60),
        'Thigh_L':     (60, 60, 70),
        'Thigh_R':     (60, 60, 70),
        'Shin_L':      (60, 60, 70),
        'Shin_R':      (60, 60, 70),
        'Foot_L':      (40, 40, 50),
        'Foot_R':      (40, 40, 50),
    },
    # 肌肉男：黑色滑雪服，红色装饰
    'muscle_skier': {
        'Head':        (225, 185, 155),
        'Neck':        (225, 185, 155),
        'Spine':       (40, 40, 45),
        'Hips':        (40, 40, 45),
        'UpperArm_L':  (40, 40, 45),
        'UpperArm_R':  (40, 40, 45),
        'ForeArm_L':   (40, 40, 45),
        'ForeArm_R':   (40, 40, 45),
        'Hand_L':      (180, 40, 40),
        'Hand_R':      (180, 40, 40),
        'Thigh_L':     (50, 50, 55),
        'Thigh_R':     (50, 50, 55),
        'Shin_L':      (50, 50, 55),
        'Shin_R':      (50, 50, 55),
        'Foot_L':      (30, 30, 35),
        'Foot_R':      (30, 30, 35),
    },
    # 瘦高：浅灰滑雪服，深蓝裤子
    'slim_skier': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (180, 180, 190),
        'Hips':        (180, 180, 190),
        'UpperArm_L':  (180, 180, 190),
        'UpperArm_R':  (180, 180, 190),
        'ForeArm_L':   (180, 180, 190),
        'ForeArm_R':   (180, 180, 190),
        'Hand_L':      (60, 60, 70),
        'Hand_R':      (60, 60, 70),
        'Thigh_L':     (40, 60, 120),
        'Thigh_R':     (40, 60, 120),
        'Shin_L':      (40, 60, 120),
        'Shin_R':      (40, 60, 120),
        'Foot_L':      (35, 35, 45),
        'Foot_R':      (35, 35, 45),
    },
    # 动漫男孩：蓝色滑雪服，白色裤子，大头
    'anime_boy': {
        'Head':        (240, 205, 175),
        'Neck':        (240, 205, 175),
        'Spine':       (60, 120, 220),
        'Hips':        (60, 120, 220),
        'UpperArm_L':  (60, 120, 220),
        'UpperArm_R':  (60, 120, 220),
        'ForeArm_L':   (60, 120, 220),
        'ForeArm_R':   (60, 120, 220),
        'Hand_L':      (230, 230, 240),
        'Hand_R':      (230, 230, 240),
        'Thigh_L':     (230, 230, 240),
        'Thigh_R':     (230, 230, 240),
        'Shin_L':      (230, 230, 240),
        'Shin_R':      (230, 230, 240),
        'Foot_L':      (50, 50, 60),
        'Foot_R':      (50, 50, 60),
    },
    # 动漫女孩：粉色滑雪服，紫色裙子，大头双马尾
    'anime_girl': {
        'Head':        (245, 210, 180),
        'Neck':        (245, 210, 180),
        'Spine':       (240, 130, 170),
        'Hips':        (240, 130, 170),
        'UpperArm_L':  (240, 130, 170),
        'UpperArm_R':  (240, 130, 170),
        'ForeArm_L':   (240, 130, 170),
        'ForeArm_R':   (240, 130, 170),
        'Hand_L':      (250, 200, 220),
        'Hand_R':      (250, 200, 220),
        'Thigh_L':     (160, 100, 180),
        'Thigh_R':     (160, 100, 180),
        'Shin_L':      (160, 100, 180),
        'Shin_R':      (160, 100, 180),
        'Foot_L':      (80, 50, 90),
        'Foot_R':      (80, 50, 90),
    },
    # 白雪公主：蓝色上衣，黄色裙子，红色蝴蝶结，黑色头发
    'snow_white': {
        'Head':        (240, 205, 175),
        'Neck':        (240, 205, 175),
        'Spine':       (50, 100, 200),
        'Hips':        (240, 210, 60),
        'UpperArm_L':  (50, 100, 200),
        'UpperArm_R':  (50, 100, 200),
        'ForeArm_L':   (50, 100, 200),
        'ForeArm_R':   (50, 100, 200),
        'Hand_L':      (240, 205, 175),
        'Hand_R':      (240, 205, 175),
        'Thigh_L':     (240, 210, 60),
        'Thigh_R':     (240, 210, 60),
        'Shin_L':      (240, 210, 60),
        'Shin_R':      (240, 210, 60),
        'Foot_L':      (40, 30, 30),
        'Foot_R':      (40, 30, 30),
    },
    # 唐老鸭：蓝色水手服，白色身体，黄色嘴脚
    'donald_duck': {
        'Head':        (250, 250, 250),
        'Neck':        (250, 250, 250),
        'Spine':       (50, 100, 200),
        'Hips':        (50, 100, 200),
        'UpperArm_L':  (50, 100, 200),
        'UpperArm_R':  (50, 100, 200),
        'ForeArm_L':   (50, 100, 200),
        'ForeArm_R':   (50, 100, 200),
        'Hand_L':      (250, 250, 250),
        'Hand_R':      (250, 250, 250),
        'Thigh_L':     (50, 100, 200),
        'Thigh_R':     (50, 100, 200),
        'Shin_L':      (250, 220, 50),
        'Shin_R':      (250, 220, 50),
        'Foot_L':      (250, 220, 50),
        'Foot_R':      (250, 220, 50),
    },
    # 巴斯光年：白色太空服，绿色紫色装饰
    'buzz_lightyear': {
        'Head':        (220, 220, 230),
        'Neck':        (200, 200, 210),
        'Spine':       (230, 230, 240),
        'Hips':        (180, 180, 200),
        'UpperArm_L':  (100, 200, 100),
        'UpperArm_R':  (180, 100, 200),
        'ForeArm_L':   (230, 230, 240),
        'ForeArm_R':   (230, 230, 240),
        'Hand_L':      (200, 200, 210),
        'Hand_R':      (200, 200, 210),
        'Thigh_L':     (180, 180, 200),
        'Thigh_R':     (180, 180, 200),
        'Shin_L':      (100, 200, 100),
        'Shin_R':      (180, 100, 200),
        'Foot_L':      (150, 150, 170),
        'Foot_R':      (150, 150, 170),
    },
    # 米老鼠：黑色身体，红色短裤，黄色鞋子，白色手套
    'mickey_mouse': {
        'Head':        (40, 40, 40),
        'Neck':        (40, 40, 40),
        'Spine':       (40, 40, 40),
        'Hips':        (200, 40, 40),
        'UpperArm_L':  (40, 40, 40),
        'UpperArm_R':  (40, 40, 40),
        'ForeArm_L':   (40, 40, 40),
        'ForeArm_R':   (40, 40, 40),
        'Hand_L':      (240, 240, 240),
        'Hand_R':      (240, 240, 240),
        'Thigh_L':     (40, 40, 40),
        'Thigh_R':     (40, 40, 40),
        'Shin_L':      (40, 40, 40),
        'Shin_R':      (40, 40, 40),
        'Foot_L':      (240, 210, 50),
        'Foot_R':      (240, 210, 50),
    },
    # 大力水手：蓝白水手服，烟斗，强壮前臂
    'popeye': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (60, 100, 180),
        'Hips':        (60, 100, 180),
        'UpperArm_L':  (240, 240, 240),
        'UpperArm_R':  (240, 240, 240),
        'ForeArm_L':   (220, 180, 150),
        'ForeArm_R':   (220, 180, 150),
        'Hand_L':      (220, 180, 150),
        'Hand_R':      (220, 180, 150),
        'Thigh_L':     (60, 100, 180),
        'Thigh_R':     (60, 100, 180),
        'Shin_L':      (60, 100, 180),
        'Shin_R':      (60, 100, 180),
        'Foot_L':      (50, 50, 60),
        'Foot_R':      (50, 50, 60),
    },
    # 国王：红色长袍，金色皇冠，权杖
    'king': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (180, 40, 40),
        'Hips':        (180, 40, 40),
        'UpperArm_L':  (180, 40, 40),
        'UpperArm_R':  (180, 40, 40),
        'ForeArm_L':   (180, 40, 40),
        'ForeArm_R':   (180, 40, 40),
        'Hand_L':      (220, 180, 150),
        'Hand_R':      (220, 180, 150),
        'Thigh_L':     (180, 40, 40),
        'Thigh_R':     (180, 40, 40),
        'Shin_L':      (180, 40, 40),
        'Shin_R':      (180, 40, 40),
        'Foot_L':      (80, 50, 30),
        'Foot_R':      (80, 50, 30),
    },
    # 哈利波特：黑色长袍，红色围巾，圆框眼镜，魔杖
    'harry_potter': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (40, 40, 50),
        'Hips':        (40, 40, 50),
        'UpperArm_L':  (40, 40, 50),
        'UpperArm_R':  (40, 40, 50),
        'ForeArm_L':   (40, 40, 50),
        'ForeArm_R':   (40, 40, 50),
        'Hand_L':      (220, 180, 150),
        'Hand_R':      (220, 180, 150),
        'Thigh_L':     (40, 40, 50),
        'Thigh_R':     (40, 40, 50),
        'Shin_L':      (40, 40, 50),
        'Shin_R':      (40, 40, 50),
        'Foot_L':      (30, 30, 35),
        'Foot_R':      (30, 30, 35),
    },
    # 钢铁侠：红金配色
    'iron_man': {
        'Head':        (200, 50, 50),
        'Neck':        (200, 50, 50),
        'Spine':       (200, 50, 50),
        'Hips':        (200, 50, 50),
        'UpperArm_L':  (200, 50, 50),
        'UpperArm_R':  (200, 50, 50),
        'ForeArm_L':   (220, 180, 50),
        'ForeArm_R':   (220, 180, 50),
        'Hand_L':      (200, 50, 50),
        'Hand_R':      (200, 50, 50),
        'Thigh_L':     (200, 50, 50),
        'Thigh_R':     (200, 50, 50),
        'Shin_L':      (220, 180, 50),
        'Shin_R':      (220, 180, 50),
        'Foot_L':      (200, 50, 50),
        'Foot_R':      (200, 50, 50),
    },
    # 绿巨人：绿色皮肤，紫色裤子
    'hulk': {
        'Head':        (60, 160, 60),
        'Neck':        (60, 160, 60),
        'Spine':       (60, 160, 60),
        'Hips':        (100, 60, 140),
        'UpperArm_L':  (60, 160, 60),
        'UpperArm_R':  (60, 160, 60),
        'ForeArm_L':   (60, 160, 60),
        'ForeArm_R':   (60, 160, 60),
        'Hand_L':      (60, 160, 60),
        'Hand_R':      (60, 160, 60),
        'Thigh_L':     (100, 60, 140),
        'Thigh_R':     (100, 60, 140),
        'Shin_L':      (60, 160, 60),
        'Shin_R':      (60, 160, 60),
        'Foot_L':      (60, 160, 60),
        'Foot_R':      (60, 160, 60),
    },
    # 奇异博士：蓝色法袍，红色披风
    'doctor_strange': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (50, 60, 140),
        'Hips':        (50, 60, 140),
        'UpperArm_L':  (50, 60, 140),
        'UpperArm_R':  (50, 60, 140),
        'ForeArm_L':   (50, 60, 140),
        'ForeArm_R':   (50, 60, 140),
        'Hand_L':      (220, 180, 150),
        'Hand_R':      (220, 180, 150),
        'Thigh_L':     (50, 60, 140),
        'Thigh_R':     (50, 60, 140),
        'Shin_L':      (50, 60, 140),
        'Shin_R':      (50, 60, 140),
        'Foot_L':      (180, 40, 40),
        'Foot_R':      (180, 40, 40),
    },
    # 美国队长：蓝白红
    'captain_america': {
        'Head':        (50, 60, 140),
        'Neck':        (220, 180, 150),
        'Spine':       (50, 60, 140),
        'Hips':        (50, 60, 140),
        'UpperArm_L':  (50, 60, 140),
        'UpperArm_R':  (50, 60, 140),
        'ForeArm_L':   (200, 50, 50),
        'ForeArm_R':   (200, 50, 50),
        'Hand_L':      (220, 220, 220),
        'Hand_R':      (220, 220, 220),
        'Thigh_L':     (50, 60, 140),
        'Thigh_R':     (50, 60, 140),
        'Shin_L':      (50, 60, 140),
        'Shin_R':      (50, 60, 140),
        'Foot_L':      (200, 50, 50),
        'Foot_R':      (200, 50, 50),
    },
    # 超人：蓝色紧身衣，红色披风靴子
    'superman': {
        'Head':        (220, 180, 150),
        'Neck':        (220, 180, 150),
        'Spine':       (50, 70, 160),
        'Hips':        (50, 70, 160),
        'UpperArm_L':  (50, 70, 160),
        'UpperArm_R':  (50, 70, 160),
        'ForeArm_L':   (50, 70, 160),
        'ForeArm_R':   (50, 70, 160),
        'Hand_L':      (200, 50, 50),
        'Hand_R':      (200, 50, 50),
        'Thigh_L':     (50, 70, 160),
        'Thigh_R':     (50, 70, 160),
        'Shin_L':      (50, 70, 160),
        'Shin_R':      (50, 70, 160),
        'Foot_L':      (200, 50, 50),
        'Foot_R':      (200, 50, 50),
    },
    # 蜘蛛侠：红蓝配色
    'spiderman': {
        'Head':        (200, 50, 50),
        'Neck':        (200, 50, 50),
        'Spine':       (50, 70, 160),
        'Hips':        (50, 70, 160),
        'UpperArm_L':  (200, 50, 50),
        'UpperArm_R':  (200, 50, 50),
        'ForeArm_L':   (50, 70, 160),
        'ForeArm_R':   (50, 70, 160),
        'Hand_L':      (200, 50, 50),
        'Hand_R':      (200, 50, 50),
        'Thigh_L':     (50, 70, 160),
        'Thigh_R':     (50, 70, 160),
        'Shin_L':      (200, 50, 50),
        'Shin_R':      (200, 50, 50),
        'Foot_L':      (200, 50, 50),
        'Foot_R':      (200, 50, 50),
    },
    # 闪电侠：红色，黄色装饰
    'flash': {
        'Head':        (200, 50, 50),
        'Neck':        (200, 50, 50),
        'Spine':       (200, 50, 50),
        'Hips':        (200, 50, 50),
        'UpperArm_L':  (200, 50, 50),
        'UpperArm_R':  (200, 50, 50),
        'ForeArm_L':   (240, 200, 50),
        'ForeArm_R':   (240, 200, 50),
        'Hand_L':      (200, 50, 50),
        'Hand_R':      (200, 50, 50),
        'Thigh_L':     (200, 50, 50),
        'Thigh_R':     (200, 50, 50),
        'Shin_L':      (240, 200, 50),
        'Shin_R':      (240, 200, 50),
        'Foot_L':      (240, 200, 50),
        'Foot_R':      (240, 200, 50),
    },
    # 毒液：黑色共生体
    'venom': {
        'Head':        (20, 20, 25),
        'Neck':        (20, 20, 25),
        'Spine':       (20, 20, 25),
        'Hips':        (20, 20, 25),
        'UpperArm_L':  (20, 20, 25),
        'UpperArm_R':  (20, 20, 25),
        'ForeArm_L':   (20, 20, 25),
        'ForeArm_R':   (20, 20, 25),
        'Hand_L':      (20, 20, 25),
        'Hand_R':      (20, 20, 25),
        'Thigh_L':     (20, 20, 25),
        'Thigh_R':     (20, 20, 25),
        'Shin_L':      (20, 20, 25),
        'Shin_R':      (20, 20, 25),
        'Foot_L':      (20, 20, 25),
        'Foot_R':      (20, 20, 25),
    },
    'nutcracker_skier': {
        'Head':        (190, 175, 150),  # 米色针织帽
        'Neck':        (220, 180, 150),  # 肤色
        'Spine':       (40, 70, 160),    # 蓝色上衣
        'Hips':        (40, 70, 160),
        'UpperArm_L':  (40, 70, 160),    # 蓝色袖子
        'UpperArm_R':  (40, 70, 160),
        'ForeArm_L':   (40, 70, 160),
        'ForeArm_R':   (40, 70, 160),
        'Hand_L':      (240, 240, 240),   # 白色手套
        'Hand_R':      (240, 240, 240),
        'Thigh_L':     (180, 40, 40),     # 红色裤子
        'Thigh_R':     (180, 40, 40),
        'Shin_L':      (180, 40, 40),
        'Shin_R':      (180, 40, 40),
        'Foot_L':      (40, 70, 160),     # 蓝色靴子
        'Foot_R':      (40, 70, 160),
    },
}

# 滑雪板和雪杖颜色（按人偶）
AVATAR_GEAR_COLORS = {
    'skier_pro':   {'ski': (200, 50, 50), 'pole': (220, 220, 220)},
    'robot':       {'ski': (60, 60, 80), 'pole': (180, 180, 200)},
    'stickman':    {'ski': (120, 120, 120), 'pole': (100, 100, 100)},
    'male_skier':  {'ski': (40, 80, 200), 'pole': (220, 220, 220)},
    'female_skier':{'ski': (220, 100, 180), 'pole': (230, 200, 230)},
    'elder_skier': {'ski': (220, 140, 40), 'pole': (180, 160, 120)},
    'kid_skier':   {'ski': (50, 180, 80), 'pole': (200, 200, 80)},
    'nutcracker_skier': {'ski': (160, 120, 70), 'pole': (140, 100, 60)},
    'fat_skier':   {'ski': (220, 140, 40), 'pole': (180, 140, 80)},
    'tall_skier':  {'ski': (40, 180, 180), 'pole': (200, 220, 220)},
    'muscle_skier': {'ski': (180, 40, 40), 'pole': (200, 200, 200)},
    'slim_skier':  {'ski': (100, 120, 180), 'pole': (200, 200, 210)},
    'anime_boy':   {'ski': (60, 120, 220), 'pole': (230, 230, 240)},
    'anime_girl':  {'ski': (240, 130, 170), 'pole': (250, 200, 220)},
    'snow_white':  {'ski': (240, 210, 60), 'pole': (200, 40, 40)},
    'donald_duck': {'ski': (250, 220, 50), 'pole': (50, 100, 200)},
    'buzz_lightyear': {'ski': (100, 200, 100), 'pole': (180, 100, 200)},
    'mickey_mouse': {'ski': (240, 210, 50), 'pole': (200, 40, 40)},
    'popeye':      {'ski': (240, 240, 240), 'pole': (60, 100, 180)},
    'king':        {'ski': (240, 200, 50), 'pole': (240, 200, 50)},
    'harry_potter': {'ski': (120, 40, 40), 'pole': (150, 100, 50)},
    'iron_man':      {'ski': (220, 180, 50), 'pole': (200, 50, 50)},
    'hulk':          {'ski': (100, 60, 140), 'pole': (60, 160, 60)},
    'doctor_strange': {'ski': (180, 40, 40), 'pole': (240, 200, 50)},
    'captain_america': {'ski': (200, 50, 50), 'pole': (50, 60, 140)},
    'superman':      {'ski': (200, 50, 50), 'pole': (50, 70, 160)},
    'spiderman':     {'ski': (50, 70, 160), 'pole': (200, 50, 50)},
    'flash':         {'ski': (240, 200, 50), 'pole': (200, 50, 50)},
    'venom':         {'ski': (200, 200, 200), 'pole': (20, 20, 25)},
}


def euler_to_quaternion(yaw_deg, pitch_deg, roll_deg):
    """YXZ欧拉角(度)转四元数"""
    y, x, z = math.radians(yaw_deg), math.radians(pitch_deg), math.radians(roll_deg)
    cy, sy = math.cos(y / 2), math.sin(y / 2)
    cx, sx = math.cos(x / 2), math.sin(x / 2)
    cz, sz = math.cos(z / 2), math.sin(z / 2)
    w = cy * cx * cz + sy * sx * sz
    qx = cy * sx * cz + sy * cx * sz
    qy = sy * cx * cz - cy * sx * sz
    qz = cy * cx * sz - sy * sx * cz
    return QQuaternion(w, qx, qy, qz)


def quaternion_to_euler_yxz(q):
    """四元数转YXZ欧拉角(度)，与euler_to_quaternion互为逆运算"""
    w, x, y, z = q.scalar(), q.x(), q.y(), q.z()
    # 从四元数提取旋转矩阵
    m00 = 1 - 2*(y*y + z*z)
    m01 = 2*(x*y - w*z)
    m02 = 2*(x*z + w*y)
    m10 = 2*(x*y + w*z)
    m11 = 1 - 2*(x*x + z*z)
    m12 = 2*(y*z - w*x)
    m20 = 2*(x*z - w*y)
    m21 = 2*(y*z + w*x)
    m22 = 1 - 2*(x*x + y*y)
    # YXZ顺序：R = Ry * Rx * Rz
    # m12 = -sin(x) → pitch = -asin(m12)
    sin_x = -m12
    sin_x = max(-1, min(1, sin_x))
    pitch = math.degrees(math.asin(sin_x))
    # m02 = sin(y)*cos(x), m22 = cos(y)*cos(x) → yaw = atan2(m02, m22)
    yaw = math.degrees(math.atan2(m02, m22))
    # m10 = cos(x)*sin(z), m11 = cos(x)*cos(z) → roll = atan2(m10, m11)
    roll = math.degrees(math.atan2(m10, m11))
    return yaw, pitch, roll


def _wrap_to_180_diff(a, b):
    """把 b 对齐到距离 a 最近的 ±180° 范围内"""
    diff = (b - a + 180) % 360 - 180
    return a + diff


def average_euler(a, b):
    """逐轴平均两组欧拉角，先对齐到同一 unwrap 帧再平均"""
    return tuple((_wrap_to_180_diff(a[i], b[i]) + a[i]) * 0.5 for i in range(3))


# 骨骼定义：(名称, 父索引, 偏移(x,y,z), STL文件, 传感器ID或None, 模型偏移)
BONES = [
    ("Hips",        -1, (0, 0.83, 0),       None,             None, (0, 0, 0)),          # 0 根节点（固定，无网格）
    ("Pelvis",       0, (0, 0, 0),           "hips.stl",      None, (0, 0, 0)),          # 1 骨盆（S2+S3平均，hips.stl挂这里）
    ("Spine",        0, (0, 0.05, 0),        "spine.stl",     None, (0, 0.14, 0)),       # 2 上半身（实时恒Q，virdyn用S8+S9平均；与Pelvis平级）
    ("Neck",         2, (0, 0.28, 0),        "neck.stl",      None, (0, 0.03, 0)),       # 3
    ("Head",         3, (0, 0.06, 0),        "head.stl",      None, (0, 0.05, 0)),       # 4
    ("Shoulder_L",   2, (-0.13, 0.28, 0),    None,             8,    (0, 0, 0)),         # 5 左肩（S8，实时读；virdyn恒Q，纯旋转支点）
    ("UpperArm_L",   2, (-0.13, 0.28, 0),    "upper_arm.stl", 10,   (0, -0.12, 0)),      # 6 直接挂Spine，与Shoulder_L平级（S8下滑导致肩部角度不可靠）
    ("ForeArm_L",    6, (0, -0.24, 0),       "forearm.stl",   12,   (0, -0.11, 0)),      # 7
    ("Hand_L",       7, (0, -0.22, 0),       "hand.stl",      None, (0, -0.028, 0)),     # 8
    ("Shoulder_R",   2, (0.13, 0.28, 0),     None,             9,    (0, 0, 0)),         # 9 右肩（S9，实时读；virdyn恒Q，纯旋转支点）
    ("UpperArm_R",   2, (0.13, 0.28, 0),     "upper_arm.stl", 11,   (0, -0.12, 0)),      # 10 直接挂Spine，与Shoulder_R平级
    ("ForeArm_R",   10, (0, -0.24, 0),       "forearm.stl",   13,   (0, -0.11, 0)),      # 11
    ("Hand_R",      11, (0, -0.22, 0),       "hand.stl",      None, (0, -0.028, 0)),     # 12
    ("Thigh_L",      1, (-0.06, -0.05, 0),   "thigh.stl",     4,    (0, -0.18, 0)),      # 13
    ("Shin_L",      13, (0, -0.36, 0),       "shin.stl",      6,    (0, -0.17, 0)),      # 14
    ("Foot_L",      14, (0, -0.34, 0),       "foot.stl",      None, (0, -0.025, 0.04)),  # 15
    ("Thigh_R",      1, (0.06, -0.05, 0),    "thigh.stl",     5,    (0, -0.18, 0)),      # 16
    ("Shin_R",      16, (0, -0.36, 0),       "shin.stl",      7,    (0, -0.17, 0)),      # 17
    ("Foot_R",      17, (0, -0.34, 0),       "foot.stl",      None, (0, -0.025, 0.04)),  # 18
]


def get_available_avatars():
    """扫描models目录，返回可用的人偶名称列表"""
    avatars = []
    if os.path.isdir(BASE_MODELS_DIR):
        for name in sorted(os.listdir(BASE_MODELS_DIR)):
            subdir = os.path.join(BASE_MODELS_DIR, name)
            if os.path.isdir(subdir) and os.path.isfile(os.path.join(subdir, 'head.stl')):
                avatars.append(name)
    if not avatars:
        avatars = [DEFAULT_AVATAR]
    return avatars




def _make_material(color, shininess=80):
    """创建禁用背面剔除的Phong材质（解决模型看起来"空"的问题）"""
    mat = Qt3DExtras.QPhongMaterial()
    mat.setDiffuse(QColor(*color))
    mat.setAmbient(QColor(color[0] // 3, color[1] // 3, color[2] // 3))
    mat.setShininess(shininess)
    # 禁用背面剔除：给effect的每个render pass添加NoCulling状态
    effect = mat.effect()
    try:
        passes = effect.renderPasses()
        for rp in passes:
            cull = QCullFace()
            cull.setMode(QCullFace.CullingMode.NoCulling)
            rp.addRenderState(cull)
    except Exception:
        pass  # API不可用时静默降级
    return mat


def _get_stl_y_bounds(stl_path):
    """读取STL文件，返回Y轴的(min, max, half_length)"""
    try:
        stl_data = stl_mesh.Mesh.from_file(stl_path)
        ys = stl_data.vectors[:, :, 1].flatten()
        y_min, y_max = ys.min(), ys.max()
        return y_min, y_max, (y_max - y_min) / 2
    except Exception:
        return -0.1, 0.1, 0.1  # 默认值


class BoneEntity:
    """单个骨骼：关节实体(位置+旋转) + 模型子实体(网格偏移)
    模型偏移自动适配STL长度，让模型顶部对齐关节，确保不断开"""
    def __init__(self, view, name, parent_idx, offset, stl_file, sensor_id, model_offset, color, models_dir):
        self.name = name
        self.parent_idx = parent_idx
        self.offset = QVector3D(*offset)
        self.sensor_id = sensor_id

        # 自动计算模型偏移：根据部位类型选择对齐方式
        self.has_mesh = stl_file is not None
        if self.has_mesh:
            stl_path = os.path.join(models_dir, stl_file)
            y_min, y_max, half_len = _get_stl_y_bounds(stl_path)

            # 向上延伸的部位（Spine, Neck）：模型底部对齐关节，向上延伸
            # 向下延伸的部位（四肢）：模型顶部对齐关节，向下延伸
            # Head：模型中心对齐关节
            UPWARD_PARTS = {'Spine', 'Neck'}
            DOWNWARD_PARTS = {'UpperArm_L', 'UpperArm_R', 'ForeArm_L', 'ForeArm_R',
                              'Hand_L', 'Hand_R', 'Thigh_L', 'Thigh_R',
                              'Shin_L', 'Shin_R', 'Foot_L', 'Foot_R'}

            if name in UPWARD_PARTS:
                # 模型底部对齐关节：model_offset Y = half_len，模型底部在0处，顶部在full_len处
                auto_y = half_len
            elif name in DOWNWARD_PARTS:
                # 模型顶部对齐关节：model_offset Y = -half_len，模型顶部在0处，底部在-full_len处
                auto_y = -half_len
            else:
                # Head等：使用原始的model_offset
                auto_y = model_offset[1]

            # 保留原始的X和Z偏移
            self.model_offset = QVector3D(model_offset[0], auto_y, model_offset[2])
        else:
            # 无网格的纯变换节点（如Pelvis），使用原始model_offset
            self.model_offset = QVector3D(*model_offset)

        # 关节实体：负责位置和旋转（绕关节点旋转）
        self.entity = Qt3DCore.QEntity(view.root_entity)
        self.joint_transform = Qt3DCore.QTransform()
        self.joint_transform.setTranslation(self.offset)
        self.entity.addComponent(self.joint_transform)

        # 模型实体：作为关节实体的子节点，负责网格偏移（仅当有网格时）
        if self.has_mesh:
            self.mesh_entity = Qt3DCore.QEntity(self.entity)
            self.mesh_transform = Qt3DCore.QTransform()
            self.mesh_transform.setTranslation(self.model_offset)
            # 右手镜像：与左手对称（绕Y轴180°翻转拇指方向）
            if self.name == 'Hand_R':
                self.mesh_transform.setRotation(
                    QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), 180))
            self.mesh_entity.addComponent(self.mesh_transform)

            # 网格（从指定人偶目录加载）
            mesh = Qt3DRender.QMesh()
            mesh.setSource(QUrl.fromLocalFile(stl_path))
            self.mesh_entity.addComponent(mesh)

            # 保存模型Y轴长度（用于动态调整子骨骼位置）
            self.model_y_length = y_max - y_min

            # 材质（禁用背面剔除，确保封闭实心）
            mat = _make_material(color)
            self.mesh_entity.addComponent(mat)
        else:
            # 无网格的纯变换节点，model_y_length设为0
            self.model_y_length = 0.0


class Qt3DSkeletonWidget(QWidget):
    """Qt3D人偶Widget，嵌入主界面右侧，支持多套人偶切换"""

    avatar_changed = pyqtSignal(str)  # 人偶切换信号

    def __init__(self, parent=None, avatar_name=None):
        super().__init__(parent)
        self._angles = {}
        self._last_frame_cnt = 0  # 固件采集帧号(60Hz)，来自BLE角度包frame_cnt
        self._prev_rel_rot = None  # per-bone quaternion continuity (gimbal lock sign)
        self._connected = False
        self._debug_count = 0
        self._avatar_name = avatar_name or DEFAULT_AVATAR
        self._gear_entities = []  # 滑雪板和雪杖实体，切换人偶时需要重建
        self._pole_transforms = []  # 雪杖transform引用（保持竖直向下）
        self._pole_hand_indices = []  # 雪杖对应的手部骨骼索引
        self._ski_transforms = []   # 滑雪板transform引用（BVH重定向时转180度）

        # 创建Qt3D窗口
        self.view = Qt3DExtras.Qt3DWindow()
        self.view.defaultFrameGraph().setClearColor(QColor(30, 30, 40))

        # 容器
        self.container = QWidget.createWindowContainer(self.view)
        self.container.setMinimumSize(300, 400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        # 3D视图控制栏
        self._create_camera_controls(layout)
        layout.addWidget(self.container, 1)

        # 根实体
        self.root_entity = Qt3DCore.QEntity()

        # 相机
        self.camera = self.view.camera()
        self.camera.lens().setPerspectiveProjection(45, 1.0, 0.1, 100)
        self.camera.setPosition(QVector3D(0, 1.2, 2.5))
        self.camera.setViewCenter(QVector3D(0, 0.98, 0))
        self.camera.setUpVector(QVector3D(0, 1, 0))

        # 相机控制器（鼠标旋转/缩放）
        self.cam_controller = Qt3DExtras.QOrbitCameraController(self.root_entity)
        self.cam_controller.setCamera(self.camera)
        self.cam_controller.setLinearSpeed(2.0)
        self.cam_controller.setLookSpeed(180)

        # 设置frame graph（全局禁用背面剔除，确保模型封闭实心）
        # self._setup_framegraph()  # 暂时禁用，会导致3D视图卡住

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

        # 重绘定时器
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_poses)
        self._update_timer.start(33)  # ~30Hz更新姿态

        # BVH播放器
        from bvh_player import BVHPlayer
        self._bvh_player = BVHPlayer()
        self._bvh_mode = False
        self._bvh_retarget = False  # 默认直接映射（我们自己的文件），第三方文件可开启重定向
        self._last_update_time = 0

        # Log播放器（新增）
        self._log_frames = []  # 解析后的log帧数据
        self._log_playing = False  # 是否正在播放log
        self._log_frame_idx = 0  # 当前播放到第几帧
        self._log_timer = QTimer(self)  # 播放定时器
        self._log_timer.timeout.connect(self._play_log_frame)

    def _setup_framegraph(self):
        """在现有frame graph中添加QRenderStateSet，全局禁用背面剔除"""
        from PyQt6.Qt3DRender import QRenderStateSet as _RSSet, QCullFace as _CF
        
        def add_cull_state(node):
            """递归遍历frame graph，在第一个叶子节点前添加QRenderStateSet"""
            children = node.children()
            if not children:
                # 叶子节点，添加QRenderStateSet作为子节点
                state_set = _RSSet(node)
                cull = _CF()
                cull.setMode(_CF.CullingMode.NoCulling)
                state_set.addRenderState(cull)
                return True
            for child in children:
                if add_cull_state(child):
                    return True
            return False
        
        fg = self.view.activeFrameGraph()
        if fg:
            add_cull_state(fg)

    def _setup_lights(self):
        """设置光源"""
        point_light = Qt3DRender.QPointLight()
        point_light.setColor(QColor(255, 255, 255))
        point_light.setIntensity(0.6)
        point_transform = Qt3DCore.QTransform()
        point_transform.setTranslation(QVector3D(0, 3, 2))
        point_entity = Qt3DCore.QEntity(self.root_entity)
        point_entity.addComponent(point_light)
        point_entity.addComponent(point_transform)

        dir_light = Qt3DRender.QDirectionalLight()
        dir_light.setColor(QColor(255, 240, 220))
        dir_light.setIntensity(0.7)
        dir_light.setWorldDirection(QVector3D(-0.5, -1, -0.5))
        dir_entity = Qt3DCore.QEntity(self.root_entity)
        dir_entity.addComponent(dir_light)

    def _create_ground(self):
        """创建地面参考平面"""
        ground_entity = Qt3DCore.QEntity(self.root_entity)
        plane = Qt3DExtras.QCuboidMesh()
        plane.setXExtent(3.0)
        plane.setYExtent(0.01)
        plane.setZExtent(3.0)
        ground_entity.addComponent(plane)
        ground_mat = _make_material((60, 60, 70), shininess=20)
        ground_entity.addComponent(ground_mat)
        ground_transform = Qt3DCore.QTransform()
        ground_transform.setTranslation(QVector3D(0, 0, 0))
        ground_entity.addComponent(ground_transform)

    def _get_models_dir(self):
        """获取当前人偶的STL目录"""
        d = os.path.join(BASE_MODELS_DIR, self._avatar_name)
        if os.path.isdir(d):
            return d
        return os.path.join(BASE_MODELS_DIR, DEFAULT_AVATAR)

    def _get_color_map(self):
        """获取当前人偶的配色方案"""
        return AVATAR_COLORS.get(self._avatar_name, AVATAR_COLORS[DEFAULT_AVATAR])

    def _create_bones(self):
        """创建所有骨骼实体，按部位设置颜色
        创建后根据每个模型的实际长度动态调整子骨骼的关节位置，确保不断开"""
        color_map = self._get_color_map()
        default_color = (150, 150, 150)
        models_dir = self._get_models_dir()

        for name, parent_idx, offset, stl_file, sensor_id, model_offset in BONES:
            color = color_map.get(name, default_color)
            bone = BoneEntity(self, name, parent_idx, offset, stl_file, sensor_id, model_offset, color, models_dir)
            self.bones.append(bone)

        # 动态调整子骨骼的Y轴offset：基于子骨骼类型决定连接在父顶部/中心/底部
        # 向上延伸的子骨骼（Spine, Neck）：连接在父模型顶部
        # 向下延伸的子骨骼（四肢）：连接在父模型底部
        # 居中的子骨骼（Pelvis, Head）：连接在父模型中心
        # 父模型对齐方式：
        #   居中（Hips, Head）：顶部=+half_len, 底部=-half_len
        #   向上延伸（Spine, Neck）：顶部=+full_len, 底部=0
        #   向下延伸（四肢）：顶部=0, 底部=-full_len
        CENTERED_PARENTS = {'Hips', 'Head'}
        UPWARD_PARENTS = {'Spine', 'Neck'}
        # 连接在父顶部的子骨骼
        # Spine/Neck向上延伸；UpperArm从肩部开始（模型向下延伸）；Head连接在Neck顶部
        TOP_ATTACH_CHILDREN = {'Spine', 'Neck', 'Shoulder_L', 'Shoulder_R', 'UpperArm_L', 'UpperArm_R', 'Head'}
        CENTERED_CHILDREN = {'Pelvis'}       # 居中的子骨骼，连接在父中心
        # 手臂微调：UpperArm连接在Spine顶部往下一点点（肩部上方与手臂上方平齐）
        ARM_HEIGHT_OFFSET = 0.055

        parent_child_pairs = [
            (0, 2),    # Hips -> Spine (向上，Spine在Hips顶部)
            (2, 3),    # Spine -> Neck (向上)
            (3, 4),    # Neck -> Head (向上)
            (2, 5),    # Spine -> Shoulder_L (向上，肩在Spine顶部)
            (2, 6),    # Spine -> UpperArm_L (与Shoulder_L平级，S8下滑不可靠)
            (6, 7),    # UpperArm_L -> ForeArm_L (向下)
            (7, 8),    # ForeArm_L -> Hand_L (向下)
            (2, 9),    # Spine -> Shoulder_R (向上)
            (2, 10),   # Spine -> UpperArm_R (与Shoulder_R平级)
            (10, 11),  # UpperArm_R -> ForeArm_R (向下)
            (11, 12),  # ForeArm_R -> Hand_R (向下)
            (0, 1),    # Hips -> Pelvis (居中)
            (1, 13),   # Pelvis -> Thigh_L (向下，大腿在Pelvis底部)
            (1, 16),   # Pelvis -> Thigh_R (向下)
            (13, 14),  # Thigh_L -> Shin_L (向下)
            (14, 15),  # Shin_L -> Foot_L (向下)
            (16, 17),  # Thigh_R -> Shin_R (向下)
            (17, 18),  # Shin_R -> Foot_R (向下)
        ]
        for parent_idx, child_idx in parent_child_pairs:
            parent_bone = self.bones[parent_idx]
            child_bone = self.bones[child_idx]

            # 计算父模型的顶部Y和底部Y（相对于父关节）
            if parent_bone.name in CENTERED_PARENTS:
                parent_top_y = parent_bone.model_y_length / 2
                parent_bottom_y = -parent_bone.model_y_length / 2
            elif parent_bone.name in UPWARD_PARENTS:
                parent_top_y = parent_bone.model_y_length
                parent_bottom_y = 0.0
            else:
                # 向下延伸（四肢）或无网格（Pelvis）
                parent_top_y = 0.0
                parent_bottom_y = -parent_bone.model_y_length

            # 根据子骨骼类型决定连接位置
            if child_bone.name in TOP_ATTACH_CHILDREN:
                offset_y = parent_top_y      # 连接在父顶部（肩部/头顶）
                # 手臂微调：稍微往下一点，使手臂上方与肩部上方平齐
                if child_bone.name in ('UpperArm_L', 'UpperArm_R'):
                    offset_y -= ARM_HEIGHT_OFFSET
            elif child_bone.name in CENTERED_CHILDREN:
                offset_y = 0.0               # 居中：连接在父中心
            elif parent_bone.name == 'Pelvis':
                # Pelvis有hips.stl网格，大腿连接在网格底部
                offset_y = -parent_bone.model_y_length / 2
            else:
                offset_y = parent_bottom_y   # 连接在父底部（肘部/腕部/膝盖等）

            new_offset = QVector3D(
                child_bone.offset.x(),
                offset_y,
                child_bone.offset.z()
            )
            child_bone.offset = new_offset
            child_bone.joint_transform.setTranslation(new_offset)

        # 根据人偶整体高度动态调整Hips的Y位置，让脚刚好在地面上方
        # 计算脚的最低世界Y坐标（累加所有offset，包括Hips的offset）
        min_foot_y = 999.0
        for foot_idx in [15, 18]:
            foot_bone = self.bones[foot_idx]
            # 累加从Foot到Hips的所有offset Y（Hips的offset已经包含了基准高度）
            total_y = 0
            idx = foot_idx
            while idx >= 0:
                total_y += self.bones[idx].offset.y()
                idx = self.bones[idx].parent_idx
            # 脚模型底部在脚关节下方half_len（Foot是居中模型）
            foot_half = foot_bone.model_y_length / 2
            foot_bottom_y = total_y - foot_half
            min_foot_y = min(min_foot_y, foot_bottom_y)
        # 调整Hips的Y，让滑雪板底部在地面上方0.03（滑雪板在脚下方0.05+厚度）
        ground_clearance = 0.10
        hips_adjust = ground_clearance - min_foot_y
        hips_bone = self.bones[0]
        new_hips_offset = QVector3D(
            hips_bone.offset.x(),
            hips_bone.offset.y() + hips_adjust,
            hips_bone.offset.z()
        )
        hips_bone.offset = new_hips_offset
        hips_bone.joint_transform.setTranslation(new_hips_offset)

    def _create_ski_gear(self):
        """创建滑雪板和雪杖（装饰，固定在脚上和手上）"""
        gear_colors = AVATAR_GEAR_COLORS.get(self._avatar_name, AVATAR_GEAR_COLORS[DEFAULT_AVATAR])
        models_dir = self._get_models_dir()

        # 滑雪板（左右脚各一个，作为Foot的子实体）
        # 通过骨骼名称查找索引，避免硬编码索引出错
        foot_l_idx = next((i for i, b in enumerate(self.bones) if b.name == 'Foot_L'), 13)
        foot_r_idx = next((i for i, b in enumerate(self.bones) if b.name == 'Foot_R'), 16)
        for foot_idx in [foot_l_idx, foot_r_idx]:
            ski_entity = Qt3DCore.QEntity(self.bones[foot_idx].entity)
            ski_mesh = Qt3DRender.QMesh()
            ski_mesh.setSource(QUrl.fromLocalFile(os.path.join(models_dir, 'ski.stl')))
            ski_entity.addComponent(ski_mesh)
            ski_mat = _make_material((180, 180, 190), shininess=100)
            ski_mat.setDiffuse(QColor(*gear_colors['ski']))
            ski_entity.addComponent(ski_mat)
            ski_transform = Qt3DCore.QTransform()
            ski_transform.setTranslation(QVector3D(0, -0.05, 0.2))
            ski_entity.addComponent(ski_transform)
            self._gear_entities.append(ski_entity)
            self._ski_transforms.append(ski_transform)

        # 雪杖（左右手各一个，挂到手部骨骼下，T-Pose时竖直向下，前臂拧动时跟着画圈）
        hand_l_idx = next((i for i, b in enumerate(self.bones) if b.name == 'Hand_L'), 7)
        hand_r_idx = next((i for i, b in enumerate(self.bones) if b.name == 'Hand_R'), 10)
        for hand_idx, side in [(hand_l_idx, -1), (hand_r_idx, 1)]:
            pole_entity = Qt3DCore.QEntity(self.bones[hand_idx].entity)
            pole_mesh = Qt3DRender.QMesh()
            pole_mesh.setSource(QUrl.fromLocalFile(os.path.join(models_dir, 'pole.stl')))
            pole_entity.addComponent(pole_mesh)
            pole_mat = _make_material((140, 140, 150), shininess=60)
            pole_mat.setDiffuse(QColor(*gear_colors['pole']))
            pole_entity.addComponent(pole_mat)
            pole_transform = Qt3DCore.QTransform()
            # 雪杖STL原点在中心，下移半个杖长让手柄(顶端)对准手掌
            pole_transform.setTranslation(QVector3D(0, -0.08, -0.35))
            # T-Pose时雪杖水平指向后方（绕X轴旋转90°，从竖直转为水平向后）
            pole_transform.setRotation(QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), 90))
            pole_entity.addComponent(pole_transform)
            self._gear_entities.append(pole_entity)
            self._pole_transforms.append(pole_transform)
            self._pole_hand_indices.append((hand_idx, side))

    def _destroy_bones_and_gear(self):
        """销毁所有骨骼和装备实体（切换人偶时调用）"""
        # 先销毁装备
        for entity in self._gear_entities:
            entity.setParent(None)
            entity.deleteLater()
        self._gear_entities.clear()
        self._pole_transforms.clear()
        self._pole_hand_indices.clear()
        self._ski_transforms.clear()

        # 销毁骨骼（从叶子到根，避免父子关系问题）
        for bone in reversed(self.bones):
            bone.entity.setParent(None)
            bone.entity.deleteLater()
        self.bones.clear()

    def set_avatar(self, avatar_name):
        """切换人偶：销毁旧模型，从新目录加载STL并重建骨骼"""
        if avatar_name == self._avatar_name:
            return
        # 验证人偶目录存在
        avatar_dir = os.path.join(BASE_MODELS_DIR, avatar_name)
        if not os.path.isdir(avatar_dir):
            print(f"[Qt3D] 人偶目录不存在: {avatar_dir}, 使用默认")
            avatar_name = DEFAULT_AVATAR

        self._avatar_name = avatar_name
        print(f"[Qt3D] 切换人偶: {avatar_name}")

        # 销毁旧骨骼和装备
        self._destroy_bones_and_gear()

        # 重建骨骼
        self._create_bones()

        # 设置父子关系
        for i, bone in enumerate(self.bones):
            if bone.parent_idx >= 0:
                bone.entity.setParent(self.bones[bone.parent_idx].entity)

        # 重建滑雪板和雪杖
        self._create_ski_gear()

        self.avatar_changed.emit(avatar_name)

    def get_avatar(self):
        return self._avatar_name

    def update_angles(self, angles: dict):
        """收到BLE角度数据，保存供定时器更新"""
        if not self._bvh_mode:
            # 固件采集帧号(与BLE包/固件log对应)，先取出避免混入LR交换与_angles
            if 'frame_cnt' in angles:
                self._last_frame_cnt = angles.pop('frame_cnt')
            # 实时模式交换左右：人偶面对我们，用户左手=屏幕右，需翻转
            _LR_MAP = {2:3, 3:2, 4:5, 5:4, 6:7, 7:6, 8:9, 9:8, 10:11, 11:10, 12:13, 13:12}
            angles = {_LR_MAP.get(k, k): v for k, v in angles.items()}
        self._angles.update(angles)
        self._connected = True

    def set_connected(self, connected: bool):
        self._connected = connected

    # ==================== BVH播放控制 ====================

    def set_bvh_retarget(self, enabled):
        """设置是否启用世界空间重定向"""
        self._bvh_retarget = enabled
        if self._bvh_player is not None:
            self._bvh_player.set_retarget(enabled)

    def is_bvh_retarget(self):
        return self._bvh_retarget

    def is_bvh_retarget(self):
        return self._bvh_retarget

    def is_bvh_retarget(self):
        return self._bvh_retarget

    def load_bvh(self, file_path):
        """加载BVH文件并进入播放模式"""
        try:
            self._bvh_player.load(file_path)
            self._bvh_player.set_retarget(self._bvh_retarget)
            self._bvh_mode = True
            self._bvh_player.play()
            self._last_update_time = 0
            self._bvh_debug_count = 0
            # 打印关节映射信息
            p = self._bvh_player
            print(f"[BVH] 关节列表: {list(p.joints.keys())}")
            mapped = {k: v for k, v in p.BONE_TO_SENSOR.items() if k in p.joints and v is not None}
            print(f"[BVH] 已映射关节: {mapped}")
            # 打印第一帧的角度数据
            first_angles = p.get_frame_angles(0)
            print(f"[BVH] 第一帧角度: {first_angles}")
            return True
        except Exception as e:
            print(f"[BVH] 加载失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def stop_bvh(self):
        """停止BVH播放，返回BLE模式"""
        self._bvh_mode = False
        self._bvh_player.stop()
        self._angles.clear()

    def play_bvh(self):
        self._bvh_player.play()

    def pause_bvh(self):
        self._bvh_player.pause()

    def seek_bvh(self, frame_idx):
        self._bvh_player.seek(frame_idx)

    def set_bvh_speed(self, speed):
        self._bvh_player.set_speed(speed)

    def set_bvh_loop(self, loop):
        self._bvh_player.set_loop(loop)

    # ==================== Log播放控制（新增） ====================

    def _load_and_play_log(self):
        """加载angle_log.txt并开始播放"""
        import re
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'angle_log.txt')
        if not os.path.exists(log_path):
            print(f"[Log播放] 找不到log文件: {log_path}")
            return

        print(f"[Log播放] 正在读取: {log_path}")
        frames = []

        with open(log_path, 'r', encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 匹配FRAME和角度数据在同一行
                frame_match = re.search(r'\[FRAME (\d+)\]', line)
                if not frame_match:
                    continue

                frame_num = int(frame_match.group(1))
                angles = {}

                # 解析所有传感器角度
                # 格式: S1腰:108/4/-3 或 S1:108.4/4.2/-3.1
                sensor_pattern = r'S(\d+)[^:|]*:([-\d.]+)/([-\d.]+)/([-\d.]+)'
                matches = re.findall(sensor_pattern, line)
                for match in matches:
                    sensor_id = int(match[0])
                    y = float(match[1])
                    x = float(match[2])
                    z = float(match[3])
                    angles[sensor_id] = (y, x, z)

                if angles:
                    frames.append({
                        'frame_num': frame_num,
                        'angles': angles
                    })

        print(f"[Log播放] 解析到 {len(frames)} 帧")
        if len(frames) == 0:
            return

        # 只取最后50帧（避免太长）
        self._log_frames = frames[-50:]
        print(f"[Log播放] 使用最后 {len(self._log_frames)} 帧")

        # 过滤掉完全静止的帧，只保留有变化的帧（慢动作播放）
        filtered_frames = []
        prev_s6 = None
        for frame in self._log_frames:
            if 6 in frame['angles']:
                s6 = frame['angles'][6]
                if prev_s6 is None or abs(s6[0] - prev_s6[0]) > 5:  # y轴变化超过5°才保留
                    filtered_frames.append(frame)
                prev_s6 = s6
            else:
                filtered_frames.append(frame)

        self._log_frames = filtered_frames
        print(f"[Log播放] 过滤后 {len(self._log_frames)} 帧（只保留S6变化>5°的帧）")

        print(f"[Log播放] 第一帧角度: {self._log_frames[0]['angles']}")
        print(f"[Log播放] 最后一帧角度: {self._log_frames[-1]['angles']}")

        # 打印S6左小腿的变化
        print(f"[Log播放] S6左小腿角度变化:")
        for i, frame in enumerate(self._log_frames):
            if 6 in frame['angles']:
                y, x, z = frame['angles'][6]
                print(f"  帧{i+1}: y={y:.1f}, x={x:.1f}, z={z:.1f}")

        # 开始播放
        self._log_playing = True
        self._log_frame_idx = 0
        self._log_timer.start(1000)  # 每1000ms播放一帧（1fps，慢动作）
        print(f"[Log播放] 开始播放，共 {len(self._log_frames)} 帧，每帧1秒")

    def _play_log_frame(self):
        """播放一帧log数据"""
        if not self._log_playing or self._log_frame_idx >= len(self._log_frames):
            return

        frame = self._log_frames[self._log_frame_idx]
        print(f"[Log播放] 第 {self._log_frame_idx+1}/{len(self._log_frames)} 帧: Frame {frame['frame_num']}")
        print(f"[Log播放] 角度数据: {frame['angles']}")

        # 设置角度（注意：log里的角度已经做过LR交换了，不要再交换！）
        self._angles.clear()
        for k, v in frame['angles'].items():
            self._angles[k] = v

        self._connected = True
        self._log_frame_idx += 1

    def _stop_log_play(self):
        """停止播放log"""
        self._log_playing = False
        self._log_timer.stop()
        print("[Log播放] 停止播放")

    def get_bvh_info(self):
        """获取BVH文件信息"""
        p = self._bvh_player
        return {
            'file_path': p.file_path,
            'file_size': p.file_size,
            'num_joints': len(p.joints),
            'num_frames': p.num_frames,
            'frame_time': p.frame_time,
            'total_time': p.get_total_time(),
            'current_frame': p.current_frame,
            'current_time': p.get_current_time(),
            'progress': p.get_progress(),
            'playing': p.playing,
            'speed': p.speed,
            'loop': p.loop,
        }

    def is_bvh_mode(self):
        return self._bvh_mode

    def _update_poses(self):
        """根据当前角度更新所有骨骼的旋转"""
        # BVH播放模式：从BVH播放器获取当前帧的角度数据
        if self._bvh_mode and self._bvh_player.frame_data is not None:
            import time
            now = time.time()
            if self._last_update_time > 0:
                delta = now - self._last_update_time
            else:
                delta = 0.033
            self._last_update_time = now
            # 播放时更新进度，暂停时也获取当前帧（用于进度条拖动）
            if self._bvh_player.playing:
                bvh_angles = self._bvh_player.update(delta)
            else:
                # 根据重定向开关选择方法
                if self._bvh_retarget:
                    bvh_angles = self._bvh_player.get_frame_angles_retargeted(self._bvh_player.current_frame)
                else:
                    bvh_angles = self._bvh_player.get_frame_angles(self._bvh_player.current_frame)
            if bvh_angles is not None:
                self._angles.update(bvh_angles)
                # 调试输出：每60帧打印一次
                if not hasattr(self, '_bvh_debug_count'):
                    self._bvh_debug_count = 0
                self._bvh_debug_count += 1
                if self._bvh_debug_count % 60 == 0:
                    print(f"[BVH Debug] frame={self._bvh_player.current_frame}, "
                          f"playing={self._bvh_player.playing}, "
                          f"angles_keys={sorted(bvh_angles.keys())}, "
                          f"sample={list(bvh_angles.items())[:3]}")

        world_rot = [QQuaternion()] * len(self.bones)

        # [调试] 每30帧打印全部13路传感器角度，并落盘到 angle_log.txt（带渲染帧号）
        if not hasattr(self, '_all_dbg'):
            self._all_dbg = 0
        self._all_dbg += 1
        if self._all_dbg % 30 == 0 and self._angles:
            names = {1:'S1腰',2:'S2左髋',3:'S3右髋',4:'S4左大腿',5:'S5右大腿',
                     6:'S6左小腿',7:'S7右小腿',8:'S8左肩',9:'S9右肩',10:'S10左上臂',
                     11:'S11右上臂',12:'S12左前臂',13:'S13右前臂'}
            parts = []
            for sid in range(1, 14):
                if sid in self._angles:
                    y, x, z = self._angles[sid]
                    parts.append(f"{names.get(sid,f'S{sid}')}:{y:.0f}/{x:.0f}/{z:.0f}")
            line = f"[{HOST_BUILD_TAG}] [FRAME {self._last_frame_cnt}] " + " | ".join(parts)
            print("[ANGLES] " + line)
            try:
                if not hasattr(self, '_angle_log_fh'):
                    self._angle_log_fh = _open_shared_angle_log(
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "angle_log.txt"))
                self._angle_log_fh.write(line + "\n")
                self._angle_log_fh.flush()
            except Exception:
                pass

        for i, bone in enumerate(self.bones):
            # 相对旋转
            if bone.name == 'Hips':
                # Hips（根节点）使用S1腰背部传感器控制整体躯干旋转
                # 相机在+Z看人偶背面，pitch(ex)和roll(ez)方向与正面视角相反，需取反
                if 1 in self._angles:
                    y, x, z = self._angles[1]
                    rel_rot = euler_to_quaternion(y, -x, -z)
                else:
                    rel_rot = QQuaternion()
            elif bone.name == 'Pelvis':
                # Pelvis（骨盆）使用传感器2、3的平均，就像Spine使用8、9的平均一样
                if not hasattr(self, '_pelvis_dbg'):
                    self._pelvis_dbg = 0
                self._pelvis_dbg += 1
                if self._pelvis_dbg % 30 == 0:
                    print(f"[Pelvis DBG] keys={sorted(self._angles.keys())}, "
                          f"a2={self._angles.get(2)}, a3={self._angles.get(3)}")
                if 2 in self._angles and 3 in self._angles:
                    y, x, z = average_euler(self._angles[2], self._angles[3])
                    # x轴取反：前后方向修正
                    rel_rot = euler_to_quaternion(y, -x, z)
                elif 2 in self._angles:
                    y, x, z = self._angles[2]
                    rel_rot = euler_to_quaternion(y, -x, z)
                elif 3 in self._angles:
                    y, x, z = self._angles[3]
                    rel_rot = euler_to_quaternion(y, -x, z)
                else:
                    rel_rot = QQuaternion()
            elif bone.name == 'Spine':
                if self._bvh_mode and self._bvh_retarget:
                    # virdyn 标准BVH重定向播放：Spine用肩传感器8/9平均（git HEAD原逻辑，播放virdyn正确）。
                    # 重定向输出的8/9=Spine世界旋转（肩世界旋转回退），躯干弯曲需显示。
                    if 8 in self._angles and 9 in self._angles:
                        y = (self._angles[8][0] + self._angles[9][0]) * 0.5
                        x = (self._angles[8][1] + self._angles[9][1]) * 0.5
                        z = (self._angles[8][2] + self._angles[9][2]) * 0.5
                        rel_rot = euler_to_quaternion(y, x, z)
                    elif 8 in self._angles:
                        y, x, z = self._angles[8]
                        rel_rot = euler_to_quaternion(y, x, z)
                    elif 9 in self._angles:
                        y, x, z = self._angles[9]
                        rel_rot = euler_to_quaternion(y, x, z)
                    else:
                        rel_rot = QQuaternion()
                else:
                    # B方案：Spine（躯干）不再吃肩部传感器S8/S9（那是肩关节转角，不是躯干）。
                    # 躯干姿态由根节点Hips(S1)经层级传导而来；这里固定为0，只做纵向连接。
                    # 肩部动作由Shoulder分支独立读S8/S9展示（见Shoulder_L/R分支）。
                    rel_rot = QQuaternion()
            elif bone.name == 'Shoulder_L':
                # 方案A：左肩独立关节。实时读S8（前平举主转在肩S8，绕人体Y约90°）；
                # virdyn retarget时Spine已用S8/S9平均，肩不再叠加，保持原播放行为。
                if self._bvh_mode and self._bvh_retarget:
                    rel_rot = QQuaternion()
                elif 8 in self._angles:
                    y, x, z = self._angles[8]
                    rel_rot = euler_to_quaternion(y, -x, -z)
                else:
                    rel_rot = QQuaternion()
            elif bone.name == 'Shoulder_R':
                # 方案A：右肩独立关节，实时读S9。
                if self._bvh_mode and self._bvh_retarget:
                    rel_rot = QQuaternion()
                elif 9 in self._angles:
                    y, x, z = self._angles[9]
                    rel_rot = euler_to_quaternion(y, -x, -z)
                else:
                    rel_rot = QQuaternion()
            elif bone.name == 'Thigh_L':
                # 左大腿：用传感器4（左大腿）
                if 4 in self._angles:
                    y, x, z = self._angles[4]
                else:
                    y, x, z = 0, 0, 0
                # x轴取反：前后方向修正（向前抬起=正方向）
                rel_rot = euler_to_quaternion(y, -x, z)
            elif bone.name == 'Thigh_R':
                # 右大腿：用传感器5（右大腿）
                if 5 in self._angles:
                    y, x, z = self._angles[5]
                else:
                    y, x, z = 0, 0, 0
                # x轴取反：前后方向修正
                rel_rot = euler_to_quaternion(y, -x, z)
            elif bone.name == 'Shin_L':
                # 左小腿：用传感器6（左小腿）
                if 6 in self._angles:
                    y, x, z = self._angles[6]
                else:
                    y, x, z = 0, 0, 0
                # 先改回原来的公式，和大腿一样
                rel_rot = euler_to_quaternion(y, -x, z)
            elif bone.name == 'Shin_R':
                # 右小腿：用传感器7（右小腿）
                if 7 in self._angles:
                    y, x, z = self._angles[7]
                else:
                    y, x, z = 0, 0, 0
                # x轴取反：前后方向修正
                rel_rot = euler_to_quaternion(y, -x, z)
            elif bone.name == 'ForeArm_L':
                if self._bvh_mode and self._bvh_retarget:
                    # virdyn 重定向：直接用人体坐标 euler(y,x,z)，与备份版本一致
                    if 12 in self._angles:
                        y, x, z = self._angles[12]
                        rel_rot = euler_to_quaternion(y, x, z)
                    else:
                        rel_rot = QQuaternion()
                elif 12 in self._angles:
                    y, x, z = self._angles[12]
                    # ForeArm是上臂的子节点，固件输出的euler是人体坐标系下的
                    # 需要共轭变换到上臂坐标系：rel_rot = _T.conjugated() * q_human * _T
                    # x轴取反（拧转方向修正），z轴取负
                    _T = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), -90)
                    rel_rot = _T.conjugated() * euler_to_quaternion(y, -x, -z) * _T
                else:
                    rel_rot = QQuaternion()
            elif bone.name == 'ForeArm_R':
                if self._bvh_mode and self._bvh_retarget:
                    # virdyn 重定向：直接用人体坐标 euler(y,x,z)，与备份版本一致
                    if 13 in self._angles:
                        y, x, z = self._angles[13]
                        rel_rot = euler_to_quaternion(y, x, z)
                    else:
                        rel_rot = QQuaternion()
                elif 13 in self._angles:
                    y, x, z = self._angles[13]
                    # ForeArm是上臂的子节点，固件输出的euler是人体坐标系下的
                    # 需要共轭变换到上臂坐标系：rel_rot = _T.conjugated() * q_human * _T
                    # x轴取反（拧转方向修正），z轴取负
                    _T = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), 90)
                    rel_rot = _T.conjugated() * euler_to_quaternion(y, -x, -z) * _T
                else:
                    rel_rot = QQuaternion()
            elif bone.name == 'UpperArm_L':
                if self._bvh_mode and self._bvh_retarget:
                    # virdyn 标准BVH重定向：retargeted 输出已是人体坐标 euler(y,x,z)，直接用
                    # （10-05备份版本实测播放virdyn正确，此处e2q(y,x,z)不交换y/x）
                    if 10 in self._angles:
                        y, x, z = self._angles[10]
                        rel_rot = euler_to_quaternion(y, x, z)
                    else:
                        rel_rot = QQuaternion()
                else:
                    # T-pose基准修正：默认骨架上臂沿-Y(下垂)，T=Rz(-90)把上臂转到水平T-pose向左
                    # z轴取负：标定后固件输出z符号与上位机渲染约定相反，取负后上下方向正确
                    # x轴取反：拧转方向修正
                    q_arm = QQuaternion()
                    if 10 in self._angles:
                        y, x, z = self._angles[10]
                        q_arm = euler_to_quaternion(y, -x, -z)
                    _T = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), -90)
                    rel_rot = q_arm * _T
            elif bone.name == 'UpperArm_R':
                if self._bvh_mode and self._bvh_retarget:
                    # virdyn 重定向：直接用人体坐标 euler(y,x,z)，与备份版本一致
                    if 11 in self._angles:
                        y, x, z = self._angles[11]
                        rel_rot = euler_to_quaternion(y, x, z)
                    else:
                        rel_rot = QQuaternion()
                else:
                    # T-pose基准修正：默认骨架上臂沿-Y(下垂)，T=Rz(+90)把上臂转到水平T-pose向右
                    # z轴取负：标定后固件输出z符号与上位机渲染约定相反，取负后上下方向正确
                    # x轴取反：拧转方向修正
                    q_arm = QQuaternion()
                    if 11 in self._angles:
                        y, x, z = self._angles[11]
                        q_arm = euler_to_quaternion(y, -x, -z)
                    _T = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), 90)
                    rel_rot = q_arm * _T
            elif bone.sensor_id and bone.sensor_id in self._angles:
                y, x, z = self._angles[bone.sensor_id]
                if self._bvh_mode and self._bvh_retarget:
                    # virdyn 标准BVH重定向：retargeted 输出已是人体坐标 euler(y,x,z)，直接用
                    # （10-05备份版本实测播放virdyn正确，此处e2q(y,x,z)不交换y/x）
                    rel_rot = euler_to_quaternion(y, x, z)
                else:
                    # 固件方案B输出标准euler(ey,ex,ez)，与固件BVH存盘ZXY(Ry·Rx·Rz)标准重建一致，
                    # 统一用e2q(y,x,z)。(旧固件轴约定 hack e2q(x,y,z) 已移除)
                    rel_rot = euler_to_quaternion(y, x, z)
            else:
                rel_rot = QQuaternion()

            # 固件方案B(T-pose双臂水平标定)基准：角度0即双臂水平，上位机骨骼UpperArm offset已
            # 按T-pose水平建模，不再叠加tpose旋转(旧逻辑把双臂水平转下垂，方向反了)。
            # 注：勾选remap播放virdyn时走上方retarget分支，本块不生效，不受影响。

            # Gimbal lock continuity: euler_to_quaternion may return q or -q (same rotation).
            # Pick the branch closest to previous frame to avoid 180° visual flips.
            if self._prev_rel_rot is not None and i < len(self._prev_rel_rot) and self._prev_rel_rot[i] is not None:
                prev = self._prev_rel_rot[i]
                dot = rel_rot.scalar() * prev.scalar() + rel_rot.x() * prev.x() + rel_rot.y() * prev.y() + rel_rot.z() * prev.z()
                if dot < 0:
                    rel_rot = QQuaternion(-rel_rot.scalar(), -rel_rot.x(), -rel_rot.y(), -rel_rot.z())
                # Debug: log low-dot events
                if dot < 0.5 and i < 14:
                    if not hasattr(self, '_dot_dbg'):
                        self._dot_dbg = {}
                    self._dot_dbg[i] = (dot, bone.name)

            if bone.parent_idx >= 0:
                world_rot[i] = world_rot[bone.parent_idx] * rel_rot
            else:
                world_rot[i] = rel_rot

            bone.joint_transform.setTranslation(bone.offset)
            bone.joint_transform.setRotation(rel_rot)

            # BVH重定向模式下，模型网格绕Y轴180度（修正STL模型正面朝向）
            # 只旋转上半身模型网格，不改变骨骼旋转，确保动作数据不变
            # 原因：Virdyn BVH中Spine世界旋转含180度（朝后），Hips世界旋转不含（朝前）
            # 所以上半身mesh需转180度才朝前，下半身mesh不转才朝前
            # 需要转180度的mesh：上半身 + 脚
            ROTATE_MESHES = {'Spine', 'Neck', 'Head',
                             'UpperArm_L', 'UpperArm_R',
                             'ForeArm_L', 'ForeArm_R',
                             'Hand_L', 'Hand_R',
                             'Foot_L', 'Foot_R'}
            # 实时BLE朝前(−Z)：躯干/头/脚绕Y180翻到对向观察者；脚取反model_offset.z保持相对位置
            FACE_MESHES = {'Spine', 'Neck', 'Head', 'Foot_L', 'Foot_R'}
            if bone.has_mesh and hasattr(bone, 'mesh_transform'):
                if self._bvh_mode and self._bvh_retarget and bone.name in ROTATE_MESHES:
                    bone.mesh_transform.setRotation(QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), 180))
                    # Foot转180度后，Z偏移取反（保持脚与小腿的相对位置）
                    if bone.name in ('Foot_L', 'Foot_R'):
                        bone.mesh_transform.setTranslation(QVector3D(
                            bone.model_offset.x(), bone.model_offset.y(), -bone.model_offset.z()))
                    else:
                        bone.mesh_transform.setTranslation(bone.model_offset)
                else:
                    # 初始与BLE实时一致：全部mesh保持单位(不转)朝前——用户确认此位姿(含左右)为正确，不做Y180交换；
                    # 仅virdyn重定向(retarget)走上方ROTATE_MESHES分支保留Y180
                    bone.mesh_transform.setRotation(QQuaternion())
                    bone.mesh_transform.setTranslation(bone.model_offset)

        # Save per-bone rel_rot for next frame's gimbal-lock continuity
        self._prev_rel_rot = [bone.joint_transform.rotation() for bone in self.bones]

        # [调试] 每30帧打印关键关节实际渲染角度（局部+全局）
        if self._all_dbg % 30 == 0 and self.bones:
            render_names = {'Hips':'Hips', 'Spine':'Spine', 'UpperArm_L':'UArm_L',
                            'UpperArm_R':'UArm_R', 'ForeArm_L':'FArm_L', 'ForeArm_R':'FArm_R',
                            'Thigh_L':'Thigh_L', 'Thigh_R':'Thigh_R', 'Shin_L':'Shin_L', 'Shin_R':'Shin_R'}

            # 先计算所有骨骼的全局变换（从根节点逐级级联）
            global_rot = []
            for i, bone in enumerate(self.bones):
                local_q = bone.joint_transform.rotation()
                if bone.parent_idx < 0:
                    # 根节点：全局=局部
                    global_rot.append(local_q)
                else:
                    # 子节点：全局 = 父全局 * 局部
                    parent_global = global_rot[bone.parent_idx]
                    global_rot.append(parent_global * local_q)

            render_parts = []
            for i, bone in enumerate(self.bones):
                if bone.name in render_names:
                    # 局部角度（相对于父骨骼）
                    ly, lx, lz = quaternion_to_euler_yxz(bone.joint_transform.rotation())
                    # 全局角度（世界坐标系）
                    gy, gx, gz = quaternion_to_euler_yxz(global_rot[i])
                    render_parts.append(f"{render_names[bone.name]}:L{ly:.0f}/{lx:.0f}/{lz:.0f}|G{gy:.0f}/{gx:.0f}/{gz:.0f}")
            render_line = f"[{HOST_BUILD_TAG}] [RENDER] " + " | ".join(render_parts)
            print(render_line)
            try:
                if not hasattr(self, '_angle_log_fh'):
                    self._angle_log_fh = _open_shared_angle_log(
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "angle_log.txt"))
                self._angle_log_fh.write(render_line + "\n")
                self._angle_log_fh.flush()
            except Exception:
                pass

        # 雪杖已挂到前臂/手部骨骼下，自动跟随手臂旋转，无需手动更新

        # 滑雪板：初始与BLE实时保持单位朝前(脚下偏移+0.2不取反)；仅virdyn重定向绕Y180并Z取反
        for ski_t in self._ski_transforms:
            if self._bvh_mode and self._bvh_retarget:
                ski_t.setRotation(QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), 180))
                ski_t.setTranslation(QVector3D(0, -0.05, -0.2))  # Z取反
            else:
                ski_t.setRotation(QQuaternion())
                ski_t.setTranslation(QVector3D(0, -0.05, 0.2))


    # ==================== 3D视图相机控制 ====================

    def _create_camera_controls(self, parent_layout):
        """创建3D视图控制按钮栏"""
        from PyQt6.QtCore import QSize
        btn_icon_size = QSize(28, 28)
        # 标准视图按钮样式
        btn_style = """
            QPushButton {
                background-color: #3a3a4a;
                color: #ddd;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 11px;
                min-width: 28px;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #4a5a8a;
                border-color: #6a8aba;
            }
            QPushButton:pressed {
                background-color: #2a3a6a;
            }
        """

        def make_btn(icon_name, tooltip, callback):
            btn = QPushButton()
            icon_path = os.path.join(VIEW_ICONS_DIR, icon_name)
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(btn_icon_size)
            else:
                btn.setText(icon_name[:2])  # 图标不存在时显示前两个字符
            btn.setToolTip(tooltip)
            btn.setStyleSheet(btn_style)
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(callback)
            return btn

        # 第一行：标准视图（纯图形符号 + 英文提示）
        row1 = QHBoxLayout()
        row1.setSpacing(3)
        row1.addWidget(make_btn('view_front.png', 'Front View', lambda: self._set_standard_view('front')))
        row1.addWidget(make_btn('view_back.png', 'Back View', lambda: self._set_standard_view('back')))
        row1.addWidget(make_btn('view_left.png', 'Left View', lambda: self._set_standard_view('left')))
        row1.addWidget(make_btn('view_right.png', 'Right View', lambda: self._set_standard_view('right')))
        row1.addWidget(make_btn('view_top.png', 'Top View', lambda: self._set_standard_view('top')))
        row1.addWidget(make_btn('view_bottom.png', 'Bottom View', lambda: self._set_standard_view('bottom')))
        row1.addWidget(make_btn('view_iso.png', 'Isometric View', lambda: self._set_standard_view('iso')))
        row1.addStretch(1)

        # 第二行：旋转 + 缩放 + 平移 + 重置
        row2 = QHBoxLayout()
        row2.setSpacing(3)
        # 旋转控制
        row2.addWidget(make_btn('rotate_left.png', "Rotate Left (Yaw -15deg)", lambda: self._rotate_yaw(-15)))
        row2.addWidget(make_btn('rotate_right.png', "Rotate Right (Yaw +15deg)", lambda: self._rotate_yaw(15)))
        row2.addWidget(make_btn('tilt_up.png', "Tilt Up (Pitch +10deg)", lambda: self._rotate_pitch(10)))
        row2.addWidget(make_btn('tilt_down.png', "Tilt Down (Pitch -10deg)", lambda: self._rotate_pitch(-10)))
        # 分隔
        sep1 = QPushButton("|")
        sep1.setEnabled(False)
        sep1.setStyleSheet("background: transparent; color: #555; border: none;")
        row2.addWidget(sep1)
        # 缩放控制
        row2.addWidget(make_btn('zoom_in.png', 'Zoom In', lambda: self._zoom(0.85)))
        row2.addWidget(make_btn('zoom_out.png', 'Zoom Out', lambda: self._zoom(1.18)))
        # 分隔
        sep2 = QPushButton("|")
        sep2.setEnabled(False)
        sep2.setStyleSheet("background: transparent; color: #555; border: none;")
        row2.addWidget(sep2)
        # 平移控制
        row2.addWidget(make_btn('pan_up.png', "Pan Up", lambda: self._pan(0, 0.1)))
        row2.addWidget(make_btn('pan_down.png', "Pan Down", lambda: self._pan(0, -0.1)))
        row2.addWidget(make_btn('pan_left.png', "Pan Left", lambda: self._pan(-0.1, 0)))
        row2.addWidget(make_btn('pan_right.png', "Pan Right", lambda: self._pan(0.1, 0)))
        # 分隔
        sep3 = QPushButton("|")
        sep3.setEnabled(False)
        sep3.setStyleSheet("background: transparent; color: #555; border: none;")
        row2.addWidget(sep3)
        # 重置视图
        row2.addWidget(make_btn('view_reset.png', "Reset View", self._reset_view))
        row2.addStretch(1)

        # 第三行：Log播放控制（新增）
        row3 = QHBoxLayout()
        row3.setSpacing(3)
        row3.addWidget(make_btn('play.png', "播放Log文件", self._load_and_play_log))
        row3.addWidget(make_btn('pause.png', "停止播放", self._stop_log_play))
        row3.addStretch(1)

        parent_layout.addLayout(row1)
        parent_layout.addLayout(row2)
        parent_layout.addLayout(row3)

    def _get_view_center(self):
        """获取相机观察中心点"""
        return self.camera.viewCenter()

    def _zoom(self, factor):
        """缩放相机（沿视线方向移动）
        factor < 1: 放大, factor > 1: 缩小
        """
        pos = self.camera.position()
        center = self._get_view_center()
        direction = pos - center
        new_pos = center + direction * factor
        # 限制缩放范围
        dist = (new_pos - center).length()
        if 0.5 < dist < 20:
            self.camera.setPosition(new_pos)

    def _pan(self, dx, dy):
        """平移相机（在垂直于视线的平面上移动）
        dx: 水平平移量, dy: 垂直平移量
        """
        pos = self.camera.position()
        center = self._get_view_center()
        forward = (center - pos).normalized()
        up = self.camera.upVector().normalized()
        right = QVector3D.crossProduct(forward, up).normalized()
        # 实际向上方向（垂直于视线）
        real_up = QVector3D.crossProduct(right, forward).normalized()

        offset = right * dx + real_up * dy
        self.camera.setPosition(pos + offset)
        self.camera.setViewCenter(center + offset)

    def _rotate_yaw(self, angle_deg):
        """绕Y轴旋转相机位置（左右旋转）"""
        center = self._get_view_center()
        pos = self.camera.position()
        relative = pos - center
        angle = math.radians(angle_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        # 绕Y轴旋转
        new_x = relative.x() * cos_a + relative.z() * sin_a
        new_z = -relative.x() * sin_a + relative.z() * cos_a
        new_pos = QVector3D(new_x, relative.y(), new_z) + center
        self.camera.setPosition(new_pos)

    def _rotate_pitch(self, angle_deg):
        """绕水平轴旋转相机位置（上下旋转）"""
        center = self._get_view_center()
        pos = self.camera.position()
        relative = pos - center
        # 计算当前俯仰角
        horiz_dist = math.sqrt(relative.x()**2 + relative.z()**2)
        current_pitch = math.atan2(relative.y(), horiz_dist)
        new_pitch = current_pitch + math.radians(angle_deg)
        # 限制俯仰角范围（避免翻转）
        new_pitch = max(-math.pi/2 + 0.1, min(math.pi/2 - 0.1, new_pitch))
        # 计算新位置
        total_dist = relative.length()
        new_y = total_dist * math.sin(new_pitch)
        new_horiz = total_dist * math.cos(new_pitch)
        # 保持水平方向不变
        if horiz_dist > 0.001:
            scale = new_horiz / horiz_dist
            new_x = relative.x() * scale
            new_z = relative.z() * scale
        else:
            new_x = 0
            new_z = new_horiz
        new_pos = QVector3D(new_x, new_y, new_z) + center
        self.camera.setPosition(new_pos)

    def _set_standard_view(self, view_name):
        """设置标准视图"""
        center = QVector3D(0, 0.98, 0)
        views = {
            'front':  QVector3D(0, 1.0, 3.0),
            'back':   QVector3D(0, 1.0, -3.0),
            'left':   QVector3D(-3.0, 1.0, 0),
            'right':  QVector3D(3.0, 1.0, 0),
            'top':    QVector3D(0, 4.0, 0.01),
            'bottom': QVector3D(0, -2.0, 0.01),
            'iso':    QVector3D(2.2, 1.8, 2.2),
        }
        if view_name in views:
            self.camera.setPosition(views[view_name])
            self.camera.setViewCenter(center)
            self.camera.setUpVector(QVector3D(0, 1, 0))

    def _reset_view(self):
        """重置视图到默认角度"""
        self.camera.setPosition(QVector3D(0, 1.2, 2.5))
        self.camera.setViewCenter(QVector3D(0, 0.98, 0))
        self.camera.setUpVector(QVector3D(0, 1, 0))

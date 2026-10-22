import asyncio
import os
import configparser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLabel, QFrame, QFormLayout, QProgressBar,
    QDialog, QDialogButtonBox, QFileDialog, QSlider, QCheckBox, QComboBox, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QIcon
import time
from datetime import datetime
# 3D视图模块
from skeleton_qt3d_view import Qt3DSkeletonWidget, get_available_avatars, DEFAULT_AVATAR
from bvh_file_dialog import BvhFileManagerDialog

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')


def load_config():
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH, encoding='utf-8')
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        cfg.write(f)


def get_config_avatar():
    cfg = load_config()
    if cfg.has_option('Appearance', 'avatar'):
        return cfg.get('Appearance', 'avatar')
    return DEFAULT_AVATAR


def set_config_avatar(avatar_name):
    cfg = load_config()
    if not cfg.has_section('Appearance'):
        cfg.add_section('Appearance')
    cfg.set('Appearance', 'avatar', avatar_name)
    save_config(cfg)

def get_config_last_bvh_dir():
    """获取最近打开BVH文件的目录"""
    cfg = load_config()
    if cfg.has_option('File', 'last_bvh_dir'):
        d = cfg.get('File', 'last_bvh_dir')
        if os.path.isdir(d):
            return d
    # 默认：用户桌面的bvhdownload目录
    default_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'bvhdownload')
    if not os.path.isdir(default_dir):
        default_dir = os.path.expanduser('~')
    return default_dir

def set_config_last_bvh_dir(dir_path):
    """保存最近打开BVH文件的目录"""
    cfg = load_config()
    if not cfg.has_section('File'):
        cfg.add_section('File')
    cfg.set('File', 'last_bvh_dir', dir_path)
    save_config(cfg)


class AvatarSelectDialog(QDialog):
    def __init__(self, current_avatar, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Avatar")
        self.setMinimumSize(280, 320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Available Avatars:"))
        self.list_widget = QListWidget()
        avatars = get_available_avatars()
        for name in avatars:
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)
            if name == current_avatar:
                self.list_widget.setCurrentItem(item)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected(self):
        item = self.list_widget.currentItem()
        return item.text() if item else None

class MainWindow(QWidget):
    def __init__(self, ble_mgr):
        super().__init__()
        self.ble_mgr = ble_mgr
        self.setWindowTitle("Syntrak MotionCap Viewer V1.0")
        self.setWindowIcon(QIcon("pics/Ski.png"))
        self.resize(1000, 650)
        # ============ 全局样式（与文件管理窗口风格一致） ============
        self.setStyleSheet("""
            QWidget { background-color: #f5f7fa; color: #2c3e50; font-size: 12px; }
            QLabel { color: #2c3e50; font-size: 12px; }
            QPushButton {
                background-color: #3498db; color: white; border: none;
                padding: 8px 16px; border-radius: 4px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #1a5276; }
            QPushButton:disabled { background-color: #bdc3c7; color: #ecf0f1; }
            QListWidget {
                border: 1px solid #bdc3c7; border-radius: 6px;
                background-color: white; color: #2c3e50; font-size: 12px; padding: 4px;
                outline: none;
            }
            QListWidget::item { padding: 6px; border-radius: 3px; color: #2c3e50; }
            QListWidget::item:hover { background-color: #d6eaf8; color: #1a5276; }
            QListWidget::item:selected { background-color: #1a5276; color: #ffffff; font-weight: bold; }
            QTextEdit {
                border: 1px solid #bdc3c7; border-radius: 4px; padding: 6px;
                background-color: white; color: #2c3e50; font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #bdc3c7; border-radius: 4px; text-align: center;
                background-color: white; height: 18px; font-size: 11px; color: #2c3e50;
            }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 3px; }
            QScrollBar:vertical {
                background: #ecf0f1; width: 10px; margin: 0; border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #95a5a6; min-height: 25px; border-radius: 5px; margin: 1px;
            }
            QScrollBar::handle:vertical:hover { background: #7f8c8d; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QFrame { background-color: #f5f7fa; }
        """)

        # ============ 左侧控制面板 ============
        layout_left = QVBoxLayout()

        # 顶部LOGO图片：单独布局实现水平居中，下方控件靠左
        h_layout_logo = QHBoxLayout()
        self.lbl_conn_icon = QLabel()
        self.lbl_conn_icon.setFixedSize(256, 64)
        self.lbl_conn_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout_logo.addStretch(1)
        h_layout_logo.addWidget(self.lbl_conn_icon)
        h_layout_logo.addStretch(1)
        layout_left.addLayout(h_layout_logo)

        # 功能按钮
        self.btn_scan = QPushButton("Scan Devices")
        self.btn_scan.setToolTip("<b>Scan Bluetooth Devices</b><br/>Search nearby available Syntrak motion capture suits.")
        self.btn_scan.setIconSize(QSize(28, 28))
        self.btn_scan.setFixedHeight(44)
        self.btn_scan.setIcon(QIcon("pics/scan.png"))

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setIconSize(QSize(28, 28))
        self.btn_connect.setFixedHeight(44)
        self.btn_connect.setIcon(QIcon("pics/connect2.png"))
        self._is_ble_connected = False
        self.btn_connect.setToolTip("Connect to the selected device")




        layout_left.addWidget(self.btn_scan)
        layout_left.addWidget(self.btn_connect)

        # 横向布局：按钮 + 状态图标并排
        # ======新增时间同步按钮======
        self.btn_sync_time = QPushButton("Sync Time")
        self.btn_sync_time.setToolTip("Sync PC local time to the device")
        self.btn_sync_time.setIconSize(QSize(32, 32))
        self.btn_sync_time.setFixedHeight(48)
        self.btn_sync_time.setIcon(QIcon("pics/timesync.png"))
        self.btn_sync_time.setVisible(False)# 默认隐藏

        self.btn_file_mgr = QPushButton("bvh File Mgr")
        self.btn_file_mgr.setVisible(False)
        self.btn_file_mgr.setToolTip("Browse and download BVH files stored on the device")
        self.btn_file_mgr.setIconSize(QSize(32, 32))
        self.btn_file_mgr.setFixedHeight(48)
        self.btn_file_mgr.setIcon(QIcon("pics/bvhfiles.png"))
        self.btn_file_mgr.setVisible(False)

        # ============【新增：开始/停止记录按钮 】============
        self.btn_toggle_record = QPushButton("Start Rec")
        self.btn_toggle_record.setIconSize(QSize(32, 32))
        self.btn_toggle_record.setFixedHeight(48)
        self.btn_toggle_record.setVisible(False)

        # ============【新增：查看传感器姿态按钮】============
        self.btn_view_sensors = QPushButton("View Sensors")
        self.btn_view_sensors.setToolTip("View real-time IMU sensor quaternion and attitude")
        self.btn_view_sensors.setIcon(QIcon("pics/sensors.png"))
        self.btn_view_sensors.setIconSize(QSize(32, 32))
        self.btn_view_sensors.setFixedHeight(48)
        self.btn_view_sensors.setVisible(False)

        # ============【新增：人偶选择按钮】============
        self.btn_avatar = QPushButton("  Avatar")
        self.btn_avatar.setToolTip("Select 3D avatar style")
        self.btn_avatar.setIcon(QIcon("pics/Ski.png"))
        self.btn_avatar.setIconSize(QSize(28, 28))
        self.btn_avatar.setFixedHeight(44)

        # ============【新增：打开BVH文件按钮】============
        self.btn_open_bvh = QPushButton("  Play BVH")
        self.btn_open_bvh.setToolTip("Open and play local BVH file (BLE must be disconnected)")
        self.btn_open_bvh.setIcon(QIcon("pics/play_bvh.png"))
        self.btn_open_bvh.setIconSize(QSize(28, 28))
        self.btn_open_bvh.setFixedHeight(44)


        # BLE功能按钮布局
        from PyQt6.QtWidgets import QSizePolicy
        v_btn_layout = QVBoxLayout()
        # 第一行：Sync Time, View Sensors
        h_btn_row1 = QHBoxLayout()
        h_btn_row1.addWidget(self.btn_sync_time, 1)
        h_btn_row1.addWidget(self.btn_view_sensors, 1)
        v_btn_layout.addLayout(h_btn_row1)
        # 第二行：Start Rec, bvh File Mgr
        h_btn_row2 = QHBoxLayout()
        h_btn_row2.addWidget(self.btn_toggle_record, 1)
        h_btn_row2.addWidget(self.btn_file_mgr, 1)
        v_btn_layout.addLayout(h_btn_row2)
        # 第三行：Avatar选择（单独一行）
        v_btn_layout.addWidget(self.btn_avatar)
        # 第四行：Open BVH（单独一行）
        v_btn_layout.addWidget(self.btn_open_bvh)
        layout_left.addLayout(v_btn_layout)

        # 成员变量缓存当前录制状态
        self._is_recording = False
        # 绑定点击事件
        self.btn_toggle_record.clicked.connect(self.on_toggle_record_click)
        self.btn_view_sensors.clicked.connect(self.on_view_sensors_click)
        self.btn_avatar.clicked.connect(self.on_avatar_click)
        self.btn_open_bvh.clicked.connect(self.on_open_bvh_click)
        # 绑定BLE录制状态信号
        self.ble_mgr.sig_recording_state.connect(self.on_recording_state_changed)


        # ============ 设备详细信息面板（软硬件版本、MAC） ============
        group_frame = QFrame()
        group_frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        form_layout = QFormLayout(group_frame)

        self.label_mac = QLabel("Not Connected")
        self.label_devName = QLabel("--")
        self.label_hw_ver = QLabel("--")
        self.label_fw_ver = QLabel("--")
        self.label_bat_level = QProgressBar()
        self.label_bat_level.setRange(0,100)
        self.label_bat_level.setFormat("%p%");
        self.label_bat_level.setVisible(False)


        form_layout.addRow("BLE MAC:", self.label_mac)
        form_layout.addRow("Device:", self.label_devName)
        form_layout.addRow("Hardware Version:", self.label_hw_ver)
        form_layout.addRow("Firmware Version:", self.label_fw_ver)
        form_layout.addRow("Battery Level:", self.label_bat_level)

        layout_left.addWidget(QLabel("【Device Information】"))
        layout_left.addWidget(group_frame)

        # 设备列表 + 日志
        self.list_devices = QListWidget()
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)

        layout_left.addWidget(QLabel("Device List："))
        layout_left.addWidget(self.list_devices)
        layout_left.addWidget(QLabel("System Log："))
        layout_left.addWidget(self.text_log)

        # ============ 右侧3D视图（从config读取人偶）============
        self._current_avatar = get_config_avatar()
        self.skeleton_view = Qt3DSkeletonWidget(avatar_name=self._current_avatar)

        # ============ BVH播放控制面板（默认隐藏）============
        self.bvh_panel = QFrame()
        self.bvh_panel.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        self.bvh_panel.setStyleSheet("background-color: #1a1a2e; border-radius: 8px;")
        bvh_layout = QVBoxLayout(self.bvh_panel)

        # 文件信息行
        self.lbl_bvh_info = QLabel("No BVH file loaded")
        self.lbl_bvh_info.setStyleSheet("color: #ecf0f1; font-size: 12px;")
        self.lbl_bvh_info.setWordWrap(True)
        bvh_layout.addWidget(self.lbl_bvh_info)

        # 进度条行
        progress_row = QHBoxLayout()
        self.lbl_bvh_time = QLabel("00:00 / 00:00")
        self.lbl_bvh_time.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        self.slider_bvh = QSlider(Qt.Orientation.Horizontal)
        self.slider_bvh.setRange(0, 1000)
        self.slider_bvh.setValue(0)
        self.slider_bvh.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #34495e; border-radius: 3px; }
            QSlider::handle:horizontal { width: 14px; height: 14px; background: #3498db; border-radius: 7px; margin: -4px 0; }
        """)
        progress_row.addWidget(self.lbl_bvh_time)
        progress_row.addWidget(self.slider_bvh, 1)
        bvh_layout.addLayout(progress_row)

        # 控制按钮行
        ctrl_row = QHBoxLayout()
        self.btn_bvh_play = QPushButton("Play")
        self.btn_bvh_play.setFixedHeight(32)
        self.btn_bvh_play.setStyleSheet("QPushButton { background-color: #27ae60; color: white; border-radius: 4px; } QPushButton:hover { background-color: #2ecc71; }")
        self.btn_bvh_stop = QPushButton("Stop")
        self.btn_bvh_stop.setFixedHeight(32)
        self.btn_bvh_stop.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border-radius: 4px; } QPushButton:hover { background-color: #ec7063; }")
        self.cmb_bvh_speed = QComboBox()
        self.cmb_bvh_speed.addItems(["0.5x", "1x", "1.5x", "2x", "4x"])
        self.cmb_bvh_speed.setCurrentIndex(1)
        self.cmb_bvh_speed.setFixedHeight(32)
        self.chk_bvh_loop = QCheckBox("Loop")
        self.chk_bvh_loop.setChecked(True)
        self.chk_bvh_loop.setStyleSheet("color: #ecf0f1;")
        self.chk_bvh_retarget = QCheckBox("Remap Virdyn BVH")
        self.chk_bvh_retarget.setChecked(False)
        self.chk_bvh_retarget.setStyleSheet("color: #ecf0f1;")
        self.chk_bvh_retarget.setToolTip("Remap Virdyn BVH format to our skeleton")

        ctrl_row.addWidget(self.btn_bvh_play)
        ctrl_row.addWidget(self.btn_bvh_stop)
        ctrl_row.addWidget(QLabel("Speed:"))
        ctrl_row.addWidget(self.cmb_bvh_speed)
        ctrl_row.addWidget(self.chk_bvh_loop)
        ctrl_row.addWidget(self.chk_bvh_retarget)
        ctrl_row.addStretch()
        bvh_layout.addLayout(ctrl_row)

        self.bvh_panel.setVisible(False)

        # BVH UI更新定时器
        self._bvh_ui_timer = QTimer(self)
        self._bvh_ui_timer.timeout.connect(self._update_bvh_ui)
        self._bvh_ui_timer.start(100)

        # 绑定BVH控制事件
        self.btn_bvh_play.clicked.connect(self.on_bvh_play_click)
        self.btn_bvh_stop.clicked.connect(self.on_bvh_stop_click)
        self.cmb_bvh_speed.currentIndexChanged.connect(self.on_bvh_speed_changed)
        self.chk_bvh_loop.stateChanged.connect(self.on_bvh_loop_changed)
        self.chk_bvh_retarget.stateChanged.connect(self.on_bvh_retarget_changed)
        self.slider_bvh.sliderMoved.connect(self.on_bvh_slider_moved)

        # ============ 整体布局 ============
        main_layout = QHBoxLayout()
        # 左侧容器，限制宽度
        left_panel = QWidget()
        left_panel.setLayout(layout_left)
        left_panel.setMinimumWidth(320)  # 最小宽度
        left_panel.setMaximumWidth(420)  # 最大宽度，防止拉太宽
        main_layout.addWidget(left_panel)
        # 右侧容器：3D视图 + BVH播放面板
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.skeleton_view, stretch=1)
        right_layout.addWidget(self.bvh_panel)
        main_layout.addWidget(right_container, stretch=1)
        self.setLayout(main_layout)
        # ============ 绑定按钮点击 ============
        self.btn_scan.clicked.connect(self.on_click_scan)
        self.btn_connect.clicked.connect(self.on_click_connect_toggle)
        self.list_devices.itemDoubleClicked.connect(self.on_list_item_double_click)
        self.btn_sync_time.clicked.connect(self.on_sync_system_time)

        # ============ BLE信号绑定【全部在UI内绑定，main.py清除所有信号绑定】 ============
        self.ble_mgr.sig_device_found.connect(self.update_device_list)
        self.ble_mgr.sig_scan_start.connect(self.clear_device_list)
        self.ble_mgr.sig_scan_start.connect(self._on_scan_start)
        self.ble_mgr.sig_scan_finished.connect(self._on_scan_finished)
        self.ble_mgr.sig_connected.connect(self.on_ble_connected)
        self.ble_mgr.sig_disconnected.connect(self.on_ble_disconnected)
        self.ble_mgr.sig_device_info.connect(self.update_device_detail_info)
        self.ble_mgr.sig_angle_data.connect(self.skeleton_view.update_angles)
        self.ble_mgr.sig_log.connect(self.append_log)
        self.ble_mgr.sig_file_resp.connect(self.on_file_response)
        self.ble_mgr.sig_file_remark.connect(self.on_file_remark)
        self.ble_mgr.sig_file_chunk.connect(self.on_file_chunk)
        self.ble_mgr.sig_batch_end.connect(self.on_batch_end)

        self._file_dialog: Optional[BvhFileManagerDialog] = None
        self.btn_file_mgr.clicked.connect(self.open_bvh_file_manager)

        # 扫描去重缓存
        self.found_addr_set = set()

        # 初始状态图片
        self.update_conn_icon(False)
        self._update_connect_button(False)
        self._clear_device_info()

    def on_file_response(self, payload: bytes):
        """BLE收到pkg_type=0x10文件列表JSON应答，转发给对话框"""
        if self._file_dialog is not None and self._file_dialog.isVisible():
            self._file_dialog.process_file_response(payload)

    def on_file_remark(self, payload: bytes):
        """BLE收到pkg_type=0x11文件备注应答，转发给对话框"""
        if self._file_dialog is not None and self._file_dialog.isVisible():
            self._file_dialog.process_remark_response(payload)

    def on_file_chunk(self, payload: bytes):
        """BLE收到pkg_type=0x03文件分块数据，转发给对话框"""
        if self._file_dialog is not None and self._file_dialog.isVisible():
            self._file_dialog.process_file_chunk(payload)

    def on_batch_end(self, next_offset: int):
        """BLE收到pkg_type=0x04批次结束通知，转发给对话框立即请求下一批"""
        if self._file_dialog is not None and self._file_dialog.isVisible():
            self._file_dialog.process_batch_end(next_offset)

    def open_bvh_file_manager(self):
        if self._file_dialog is None:
            self._file_dialog = BvhFileManagerDialog(self)
            # 弹窗发送BLE命令，交给ble_mgr异步发送
            self._file_dialog.sig_send_ble_cmd.connect(lambda pkt:
                                                       asyncio.get_running_loop().create_task(
                                                           self.ble_mgr.send_command(pkt, "FileOp"))
                                                       )
            self._file_dialog.sig_log.connect(self.append_log)
        self._file_dialog.show()
        self._file_dialog.raise_()
        self._file_dialog.refresh_dir()

    # ==================== 顶部连接状态图片 ====================
    def update_conn_icon(self, connected: bool):
        if connected:
            pix = QPixmap("pics/conn_on.png")
            tips="Syntrak MotionCap Gen 1 Connected"
        else:
            pix = QPixmap("pics/conn_off.png")
            tips = "No Device Connected"

        scaled_pix = pix.scaled(
            self.lbl_conn_icon.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_conn_icon.setPixmap(scaled_pix)
        self.lbl_conn_icon.setToolTip(tips)

    def on_ble_connected(self, mac_addr: str):
        """蓝牙链路建立成功"""
        self.update_conn_icon(True)
        self._update_connect_button(True)
        self.label_mac.setText(mac_addr)
        self.skeleton_view.set_connected(True)
        # BLE连接时：隐藏Open BVH按钮，如果有BVH播放则停止并隐藏面板
        self.btn_open_bvh.setVisible(False)
        if self.skeleton_view.is_bvh_mode():
            self.skeleton_view.stop_bvh()
            self.bvh_panel.setVisible(False)
        self.btn_sync_time.setVisible(True)  # 连接成功显示
        self.btn_file_mgr.setVisible(True)
        self.btn_toggle_record.setVisible(True)
        self.btn_view_sensors.setVisible(True)  # 连接成功显示传感器查看按钮

        # 连接成功即创建传感器数据解析器并订阅IMU数据，持续缓存
        from sensor_data_parser import SensorDataParser
        if not hasattr(self, '_sensor_parser') or self._sensor_parser is None:
            self._sensor_parser = SensorDataParser()
            try:
                self.ble_mgr.sig_imu_data.connect(self._on_sensor_imu_data)
                print("[SensorParser] created and subscribed on BLE connect")
            except Exception as e:
                print(f"[SensorParser] subscribe failed: {e}")

        # 刚连接默认状态：未录制
        self._is_recording = False
        self._update_rec_ui()

    def on_ble_disconnected(self):
        """断开连接，清空所有信息"""
        self.update_conn_icon(False)
        self._update_connect_button(False)
        self._clear_device_info()
        self.skeleton_view.set_connected(False)
        # BLE断开时：显示Open BVH按钮
        self.btn_open_bvh.setVisible(True)
        self.btn_sync_time.setVisible(False) # 断开隐藏
        self.btn_file_mgr.setVisible(False)
        self.btn_toggle_record.setVisible(False)
        self.btn_view_sensors.setVisible(False)  # 断开隐藏传感器查看按钮
        # 断开时重置传感器解析器（下次连接重新创建）
        if hasattr(self, '_sensor_parser'):
            try:
                # 解除IMU信号订阅，避免多次断开-连接后 sig_imu_data 累积多个连接
                # （每次连接都 connect，从不断开，高频IMU数据会触发N倍槽，累积过多易压垮Qt事件队列）
                self.ble_mgr.sig_imu_data.disconnect(self._on_sensor_imu_data)
            except Exception:
                pass
            self._sensor_parser = None

        if self._file_dialog:
            self._file_dialog.clear_file_tree()

    def _clear_device_info(self):
        self.label_mac.setText("No Connection")
        self.label_hw_ver.setText("--")
        self.label_fw_ver.setText("--")
        self.label_devName.setText("--")
        self.label_bat_level.setVisible(False)

    def update_device_detail_info(self, hw_ver: str, fw_ver: str, dev_name:str, batLevel:int):
        """收到设备上报的软硬件版本信息，刷新面板"""
        self.label_hw_ver.setText(hw_ver)
        self.label_fw_ver.setText(fw_ver)
        self.label_devName.setText(dev_name)
        if batLevel<0:
            batLevel = 0
        elif batLevel>100:
            batLevel = 100
        self.label_bat_level.setValue(batLevel)
        if batLevel<20:
            self.label_bat_level.setStyleSheet("""
            QProgressBar {
                border:1px solid #bdc3c7;
                border-radius:4px;
                background-color:white;
                text-align:center;
                color:#2c3e50;
            }
            QProgressBar::chunk {
                background-color:#e74c3c;
                border-radius:3px;
            }
            """)
        elif batLevel>50:
            self.label_bat_level.setStyleSheet("""
            QProgressBar {
                border:1px solid #bdc3c7;
                border-radius:4px;
                background-color:white;
                text-align:center;
                color:#2c3e50;
            }
            QProgressBar::chunk {
                background-color:#27ae60;  
                border-radius:3px;
            }
            """)
        else:
            self.label_bat_level.setStyleSheet("""
            QProgressBar {
                border:1px solid #bdc3c7;
                border-radius:4px;
                background-color:white;
                text-align:center;
                color:#2c3e50;
            }
            QProgressBar::chunk {
                background-color:#f39c12;
                border-radius:3px;
            }
            """)

        self.label_bat_level.setVisible(True)

    # ==================== 设备列表管理（去重） ====================
    def clear_device_list(self):
        self.list_devices.clear()
        self.found_addr_set.clear()

    def update_device_list(self, addr: str, name: str):
        if addr in self.found_addr_set:
            return
        self.found_addr_set.add(addr)
        item = QListWidgetItem(f"{name} [{addr}]")
        item.setData(Qt.ItemDataRole.UserRole, addr)
        self.list_devices.addItem(item)

    # ==================== 按钮响应函数 ====================
    def _on_scan_start(self):
        """Scan started: show Scanning... and disable button"""
        self.btn_scan.setText("Scanning...")
        self.btn_scan.setEnabled(False)

    def _on_scan_finished(self):
        """Scan finished: restore Scan Devices and enable button"""
        self.btn_scan.setText("Scan Devices")
        self.btn_scan.setEnabled(True)

    def on_click_scan(self):
        self.append_log("Start scanning clicked")
        loop = asyncio.get_running_loop()
        loop.create_task(self.ble_mgr.start_scan())

    def on_click_connect_toggle(self):
        """合并Connect/Disconnect按钮：根据当前状态切换"""
        if self._is_ble_connected:
            self.append_log("Request to disconnect")
            loop = asyncio.get_running_loop()
            loop.create_task(self.ble_mgr.disconnect())
        else:
            item = self.list_devices.currentItem()
            if not item:
                self.append_log("Warning: select a device from list to connect!")
                return
            addr = item.data(Qt.ItemDataRole.UserRole)
            self.append_log(f"Prepare to connect device: {addr}")
            loop = asyncio.get_running_loop()
            loop.create_task(self.ble_mgr.connect_device(addr))

    def _update_connect_button(self, connected: bool):
        """更新Connect/Disconnect按钮的标题、图标和状态"""
        self._is_ble_connected = connected
        if connected:
            self.btn_connect.setText("Disconnect")
            self.btn_connect.setToolTip("Disconnect from the current device")
            self.btn_connect.setIcon(QIcon("pics/disconnect2.png"))
        else:
            self.btn_connect.setText("Connect")
            self.btn_connect.setToolTip("Connect to the selected device")
            self.btn_connect.setIcon(QIcon("pics/connect2.png"))

    def on_list_item_double_click(self, item: QListWidgetItem):
        addr = item.data(Qt.ItemDataRole.UserRole)
        self.append_log(f"Double-clicked a device, connecting to:{addr}")
        loop = asyncio.get_running_loop()
        loop.create_task(self.ble_mgr.connect_device(addr))

    # ==================== 日志输出 ====================
    def append_log(self, msg: str):
        self.text_log.append("- "+msg)
        sb = self.text_log.verticalScrollBar()
        sb.setValue(sb.maximum()+2)

    import time
    from datetime import datetime

    def on_sync_system_time(self):
        """同步PC UTC时间(日期+时分秒)发送给ESP32‑S3，匹配ble_cmd_pkt_t协议"""
        if not self.ble_mgr.client or not self.ble_mgr.client.is_connected:
            self.append_log("No device connected, cannot sync time!")
            return

        import time
        import asyncio

        # UTC unix timestamp(秒)
        utc_ts = int(time.time())
        # time.timezone: UTC‑本地(秒)；取反得到 tz_offset_sec = 本地‑UTC
        tz_offset_sec = -time.timezone

        cmd_id = 0x07
        param_len = 8
        pkt = bytearray()
        pkt.append(cmd_id)
        pkt.extend(param_len.to_bytes(2, byteorder="little", signed=False))
        pkt.extend(utc_ts.to_bytes(4, byteorder="little", signed=False))
        pkt.extend(tz_offset_sec.to_bytes(4, byteorder="little", signed=True))

        self.append_log(f"Sync time: UTC_ts={utc_ts}, tz_offset_sec={tz_offset_sec}")
        loop = asyncio.get_running_loop()
        loop.create_task(self.ble_mgr.send_command(bytes(pkt), "Time Sync"))

    def on_view_sensors_click(self):
        """打开传感器姿态查看窗口（parser已在BLE连接时创建，直接用）"""
        from sensor_viewer_dialog import SensorViewerDialog
        if not hasattr(self, '_sensor_parser') or self._sensor_parser is None:
            # 兜底：如果还没创建（理论上不会发生）
            from sensor_data_parser import SensorDataParser
            self._sensor_parser = SensorDataParser()
            self.ble_mgr.sig_imu_data.connect(self._on_sensor_imu_data)
        self._sensor_dialog = SensorViewerDialog(self._sensor_parser, self)
        self._sensor_dialog.show()

    def on_avatar_click(self):
        dlg = AvatarSelectDialog(self._current_avatar, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected()
            if selected and selected != self._current_avatar:
                self._current_avatar = selected
                self.skeleton_view.set_avatar(selected)
                set_config_avatar(selected)
                self.append_log(f'Avatar changed to: {selected}')

    # ==================== BVH播放控制 ====================

    def on_open_bvh_click(self):
        """打开BVH文件对话框"""
        try:
            last_dir = get_config_last_bvh_dir()
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open BVH File", last_dir, "BVH Files (*.bvh);;All Files (*)"
            )
            if file_path:
                # 保存最近目录
                set_config_last_bvh_dir(os.path.dirname(file_path))
                if self.skeleton_view.load_bvh(file_path):
                    self.bvh_panel.setVisible(True)
                    self.btn_bvh_play.setText("Pause")
                    self.append_log(f"[BVH] Loaded: {file_path}")
                else:
                    self.append_log(f"[BVH] Failed to load: {file_path}")
        except Exception as e:
            self.append_log(f"[BVH] Error: {e}")
            import traceback
            traceback.print_exc()

    def on_bvh_play_click(self):
        if self.skeleton_view._bvh_player.playing:
            self.skeleton_view.pause_bvh()
            self.btn_bvh_play.setText("Play")
        else:
            self.skeleton_view.play_bvh()
            self.btn_bvh_play.setText("Pause")

    def on_bvh_stop_click(self):
        self.skeleton_view.stop_bvh()
        self.bvh_panel.setVisible(False)
        self.btn_bvh_play.setText("Play")
        self.slider_bvh.setValue(0)

    def on_bvh_speed_changed(self, index):
        speeds = [0.5, 1.0, 1.5, 2.0, 4.0]
        self.skeleton_view.set_bvh_speed(speeds[index])

    def on_bvh_loop_changed(self, state):
        self.skeleton_view.set_bvh_loop(state == Qt.CheckState.Checked.value)

    def on_bvh_retarget_changed(self, state):
        enabled = (state == Qt.CheckState.Checked.value)
        self.skeleton_view.set_bvh_retarget(enabled)
        status = "ON" if enabled else "OFF"
        self.append_log("[BVH] Remap Virdyn: " + status)

    def on_bvh_slider_moved(self, value):
        total = self.skeleton_view._bvh_player.num_frames
        if total > 0:
            frame = int(value / 1000 * (total - 1))
            self.skeleton_view.seek_bvh(frame)

    def _update_bvh_ui(self):
        try:
            if not self.bvh_panel.isVisible():
                return
            info = self.skeleton_view.get_bvh_info()
            if info['num_frames'] == 0:
                return
            size_kb = info['file_size'] / 1024
            size_str = f"{size_kb/1024:.1f} MB" if size_kb > 1024 else f"{size_kb:.0f} KB"
            fps = 1.0 / info['frame_time'] if info['frame_time'] > 0 else 0
            self.lbl_bvh_info.setText(
                f"File: {info['file_path'].split(chr(47))[-1]} | Size: {size_str} | "
                f"Joints: {info['num_joints']} | Frames: {info['num_frames']} | "
                f"FPS: {fps:.1f} | Frame: {info['current_frame']+1}/{info['num_frames']}"
            )
            cur, total = info['current_time'], info['total_time']
            self.lbl_bvh_time.setText(f"{int(cur//60):02d}:{int(cur%60):02d} / {int(total//60):02d}:{int(total%60):02d}")
            if not self.slider_bvh.isSliderDown():
                self.slider_bvh.setValue(int(info['progress'] * 1000))
            self.btn_bvh_play.setText("Pause" if info['playing'] else "Play")
        except Exception:
            pass

    def _on_sensor_imu_data(self, data):
        """接收BLE转发的传感器四元数数据，转发给解析器
        data 格式: {sensor_id: {"online": bool, "quat": (qw,qx,qy,qz)}}
        """
        if not hasattr(self, '_sensor_parser'):
            return
        # 调试日志：确认收到数据
        if not hasattr(self, '_imu_debug_count'):
            self._imu_debug_count = 0
        self._imu_debug_count += 1
        if self._imu_debug_count <= 5:
            print(f"[DEBUG] _on_sensor_imu_data called, keys={list(data.keys())}, types={[type(k).__name__ for k in data.keys()]}")
        for sid, info in data.items():
            if not isinstance(sid, int) or sid < 1 or sid > 13:
                if self._imu_debug_count <= 5:
                    print(f"[DEBUG] skip sid={sid} (type={type(sid).__name__})")
                continue
            if not isinstance(info, dict) or 'quat' not in info:
                if self._imu_debug_count <= 5:
                    print(f"[DEBUG] skip info for sid={sid}: {info}")
                continue
            q = info['quat']
            if len(q) < 4:
                continue
            status = info.get('status', 0)
            s = self._sensor_parser.get_sensor(sid)
            if s:
                s.update(q[0], q[1], q[2], q[3], status)
                self._sensor_parser.sig_sensor_updated.emit(sid)
                if self._imu_debug_count <= 5:
                    print(f"[DEBUG] updated sensor {sid}: q=[{q[0]:.3f},{q[1]:.3f},{q[2]:.3f},{q[3]:.3f}] status=0x{status:02X}")

    def on_toggle_record_click(self):
        """点击按钮：切换录制状态，发送BLE命令 pkg_type=0x11"""
        if not self.ble_mgr.is_connected():
            return

        # 按钮点击：想要切换状态；实际状态以设备上报sig_recording_state为准
        want_start = not self._is_recording
        self._is_recording = want_start  #测试界面
        self.on_recording_state_changed(want_start)
        pkt = bytearray()
        if want_start:
            cmd_id = 0x01
        else:
            cmd_id = 0x02
        pkt.append(cmd_id)
        pkt.extend((0).to_bytes(2, byteorder="little"))
        self.append_log(f"Send BLE cmd: {'Start Record' if want_start else 'Stop Record'}")

        loop = asyncio.get_running_loop()
        loop.create_task(self.ble_mgr.send_command(bytes(pkt), "ToggleRecord"))

    def on_recording_state_changed(self, is_rec: bool):
        """BLE收到设备上报真实录制状态，更新UI"""
        self._is_recording = is_rec
        self._update_rec_ui()

    def _update_rec_ui(self):
        """刷新按钮文字 + 状态图片"""
        """更新按钮文字和图标"""
        if self._is_recording:
            self.btn_toggle_record.setText("Stop Rec")
            self.btn_toggle_record.setToolTip("Stop Recording bvh on the device")
            self.btn_toggle_record.setIcon(QIcon("pics/rec_active.png"))

            # 可选：按钮变成红色，强调正在录制
            self.btn_toggle_record.setStyleSheet("""
                        QPushButton {
                            background-color: #e74c3c;
                            color: white;
                            border-radius: 8px;
                            padding: 8px 16px;
                        }

                        QPushButton:hover {
                            background-color: #c0392b;
                        }

                        QPushButton:pressed {
                            background-color: #922b21;
                        }
                    """)

        else:
            self.btn_toggle_record.setText("Start Record")
            self.btn_toggle_record.setToolTip("Start Recording bvh on the device")
            self.btn_toggle_record.setIcon(QIcon("pics/rec_idle.png"))

            # 恢复普通按钮样式
            self.btn_toggle_record.setStyleSheet("""
                        QPushButton {
                            background-color: #3498db;
                            color: white;
                            border-radius: 8px;
                            padding: 8px 16px;
                        }

                        QPushButton:hover {
                            background-color: #2980b9;
                        }

                        QPushButton:pressed {
                            background-color: #1a5276;
                        }
                    """)
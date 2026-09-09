import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLabel, QFrame, QFormLayout, QProgressBar
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
import time
from datetime import datetime
# 3D视图模块
from skeleton_3d_view import Skeleton3DWidget
from bvh_file_dialog import BvhFileManagerDialog

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


        # 4个BLE按钮分成2行，每行2个，每个按钮占整行一半宽度
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
        layout_left.addLayout(v_btn_layout)

        # 成员变量缓存当前录制状态
        self._is_recording = False
        # 绑定点击事件
        self.btn_toggle_record.clicked.connect(self.on_toggle_record_click)
        self.btn_view_sensors.clicked.connect(self.on_view_sensors_click)
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

        # ============ 右侧3D视图 ============
        self.skeleton_view = Skeleton3DWidget()

        # ============ 整体布局 ============
        main_layout = QHBoxLayout()
        # 左侧容器，限制宽度
        left_panel = QWidget()
        left_panel.setLayout(layout_left)
        left_panel.setMinimumWidth(320)  # 最小宽度
        left_panel.setMaximumWidth(420)  # 最大宽度，防止拉太宽
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.skeleton_view, stretch=1)
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
        self.btn_sync_time.setVisible(True)  # 连接成功显示
        self.btn_file_mgr.setVisible(True)
        self.btn_toggle_record.setVisible(True)
        self.btn_view_sensors.setVisible(True)  # 连接成功显示传感器查看按钮

        # 刚连接默认状态：未录制
        self._is_recording = False
        self._update_rec_ui()

    def on_ble_disconnected(self):
        """断开连接，清空所有信息"""
        self.update_conn_icon(False)
        self._update_connect_button(False)
        self._clear_device_info()
        self.skeleton_view.set_connected(False)
        self.btn_sync_time.setVisible(False) # 断开隐藏
        self.btn_file_mgr.setVisible(False)
        self.btn_toggle_record.setVisible(False)
        self.btn_view_sensors.setVisible(False)  # 断开隐藏传感器查看按钮

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
        """打开传感器姿态查看窗口"""
        from sensor_viewer_dialog import SensorViewerDialog
        from sensor_data_parser import SensorDataParser
        if not hasattr(self, '_sensor_parser'):
            self._sensor_parser = SensorDataParser()
            try:
                self.ble_mgr.sig_imu_data.connect(self._on_sensor_imu_data)
                print("[DEBUG] sig_imu_data connected to _on_sensor_imu_data successfully")
            except Exception as e:
                print(f"[DEBUG] FAILED to connect sig_imu_data: {e}")
        else:
            print("[DEBUG] _sensor_parser already exists, reusing")
        self._sensor_dialog = SensorViewerDialog(self._sensor_parser, self)
        self._sensor_dialog.show()

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
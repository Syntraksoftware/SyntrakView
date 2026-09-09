'''
功能：扫描以`Syntrak`开头设备、连接、接收 Notify、解析 IMU 数据包，向外发送信号
'''
import asyncio
import struct
from PyQt6.QtCore import QObject, pyqtSignal
from bleak import BleakScanner, BleakClient
from bleNotifyReassembler import  BleNotifyReassembler
#Characteristics
WRITE_CHAR_UUID = "c0b0a090-8070-6050-4030-2013ddffbbaa" # command
NOTIFY_REAL_UUID = "c0b0a090-8070-6050-4030-2011ddddbbaa" #
NOTIFY_IMU_UUID  = "c0b0a090-8070-6050-4030-2012ddeebbaa" # 传感器四元数(ble_imu_pkt_t)

class BleManager(QObject):
    sig_log = pyqtSignal(str)
    sig_scan_start = pyqtSignal()
    sig_scan_finished = pyqtSignal()
    sig_device_found = pyqtSignal(str, str)
    sig_connected = pyqtSignal(str)
    sig_disconnected = pyqtSignal()   # 新增：断开通知UI刷新图标
    sig_imu_data = pyqtSignal(dict)
    sig_device_info = pyqtSignal(str, str, str, int) # 参数：hw_ver, sw_ver, dev_name, build_time
    sig_file_resp = pyqtSignal(bytes)  # 文件列表应答payload
    sig_file_remark = pyqtSignal(bytes)  # 文件备注应答payload
    sig_file_chunk = pyqtSignal(bytes)  # 文件分块数据payload
    sig_batch_end = pyqtSignal(int)  # 批次结束通知，参数=next_offset
    sig_recording_state=pyqtSignal(bool)
    sig_angle_data = pyqtSignal(dict)  # 13关节相对转角: {sensor_id: [Y,X,Z]度}

    def __init__(self):
        super().__init__()
        self.client: BleakClient | None = None
        self.connected_addr: str | None = None
        self.NOTIFY_REAL_UUID= NOTIFY_REAL_UUID
        self.NOTIFY_IMU_UUID = NOTIFY_IMU_UUID
        self.WRITE_CHAR_UUID=WRITE_CHAR_UUID
        self._reassembler = BleNotifyReassembler()
    def is_connected(self) -> bool:
        """对外提供查询连接状态"""
        return self.client is not None and self.client.is_connected

    async def disconnect(self):
        """断开连接，统一封装"""
        if self.is_connected():
            try:
                await self.client.disconnect()
            except Exception as e:
                self.sig_log.emit(f"Disconnection Exception:{e}")
            self.client = None
            self.connected_addr = None
            self.sig_disconnected.emit()
            self.sig_log.emit("Device disconnected!")

    def _on_ble_disconnected(self, client):
        """BLE意外断开回调（Bleak在检测到断开时调用，包括上位机崩溃后的超时断开）"""
        # 避免重复触发（用户主动disconnect也会触发此回调）
        if self.client is None:
            return
        addr = self.connected_addr or "unknown"
        self.client = None
        self.connected_addr = None
        self.sig_disconnected.emit()
        self.sig_log.emit(f"BLE disconnected unexpectedly: {addr}")

    async def connect_device(self, address: str):
        # 清理旧连接
        if self.client is not None and self.client.is_connected:
            try:
                await self.client.disconnect()
            except:
                pass
            self.client = None

        client = BleakClient(address, disconnected_callback=self._on_ble_disconnected)
        try:
            self.sig_log.emit(f"Start connecting to: {address}")
            await client.connect()
            self.sig_log.emit("BLE connected, discovering services...")

            # 【最终稳定写法，不调用任何discover / get_services】
            self.sig_log.emit("===== Discovered Characteristics =====")
            for service in client.services:
                for char in service.characteristics:
                    self.sig_log.emit(f"Char UUID: {char.uuid} | Properties: {char.properties}")

            self.client = client
            # ========== 开启real通道notify，接收设备信息、姿态数据 ==========
            try:
                await self.client.start_notify(self.NOTIFY_REAL_UUID, self._on_notify_real)
                self.sig_log.emit("subscribed Real notify channel")
            except Exception as e:
                self.sig_log.emit(f"subscribe Real notify failed: {str(e)}")

            # ========== 开启IMU通道notify，接收13个传感器的四元数 ==========
            try:
                await self.client.start_notify(self.NOTIFY_IMU_UUID, self._on_notify_imu)
                self.sig_log.emit("subscribed IMU notify channel")
            except Exception as e:
                self.sig_log.emit(f"subscribe IMU notify failed: {str(e)}")

            self.sig_connected.emit(address)
            self.sig_log.emit("Device connect success")

        except Exception as e:
            self.sig_log.emit(f"Connection failed: {str(e)}")
            try:
                if client.is_connected:
                    await client.disconnect()
            except:
                pass

    async def start_scan(self):
        try:
            msg = "Start scanning Bluetooth devices start with syntrak..."
            print(msg)
            self.sig_log.emit(msg)
            self.sig_scan_start.emit()

            devices = await BleakScanner.discover(timeout=5)
            match_cnt = 0
            for dev in devices:
                dev_name = dev.name or ""
                if dev_name.lower().startswith("syntrak"):
                    self.sig_device_found.emit(dev.address, dev.name)
                    match_cnt += 1
            self.sig_log.emit(f"{match_cnt} Syntrak devices found")
        except Exception as e:
            msg = f"Scan exception：{str(e)}"
            print("【BLE ERROR】", msg)
            self.sig_log.emit(msg)
        finally:
            self.sig_scan_finished.emit()

    async def send_command(self, data: bytes, cmdinfo: str):
        if self.client is None or not self.client.is_connected:
            return
        try:
            await self.client.write_gatt_char(self.WRITE_CHAR_UUID, data, response=False)
        except Exception as e:
            self.sig_log.emit(f"{cmdinfo} command send failed: {str(e)}")

    def _on_notify_real(self, sender, data: bytes):
        """chr_real 通道notify回调，先重组再解析数据包"""
        if not hasattr(self, '_real_notify_count'):
            self._real_notify_count = 0
            self._real_pkt_count = 0
        self._real_notify_count += 1
        pkt_count_before = self._real_pkt_count
        for full_pkt in self._reassembler.feed(data):
            self._real_pkt_count += 1
            # full_pkt 是【完整原始业务包】：pkg_type(1)+pkg_len(2)+payload
            pkg_type = full_pkt[0]
            payload = full_pkt[3:]
            if pkg_type == 0x00:  #device information
                offset = 3
                hw_ver_bytes = full_pkt[offset:offset + 32]
                offset += 32
                sw_ver_bytes = full_pkt[offset:offset + 32]
                offset += 32
                dev_name_bytes = full_pkt[offset:offset + 64]
                offset += 64
                batLevel = int.from_bytes(full_pkt[offset:offset + 2], byteorder="little")
                offset += 2
                is_recording = int.from_bytes(full_pkt[offset:offset + 1], byteorder="little")

                hw_ver = hw_ver_bytes.split(b'\x00')[0].decode("utf‑8", "ignore")
                sw_ver = sw_ver_bytes.split(b'\x00')[0].decode("utf‑8", "ignore")
                dev_name = dev_name_bytes.split(b'\x00')[0].decode("utf‑8", "ignore")
                self.sig_device_info.emit(hw_ver, sw_ver, dev_name, batLevel)
                self.sig_recording_state.emit(is_recording)
            elif pkg_type == 0x01:
                # PKG_TYPE_ANGLE 相对转角包（169字节payload）
                if not hasattr(self, '_angle_pkt_count'):
                    self._angle_pkt_count = 0
                self._angle_pkt_count += 1
                if self._angle_pkt_count <= 10 or self._angle_pkt_count % 50 == 0:
                    print(f"[BLE ANGLE] pkt #{self._angle_pkt_count}, full_len={len(full_pkt)}, payload_len={len(payload)}")
                if len(payload) >= 166:
                    import struct
                    joint_angles = {}
                    base = 10
                    for sid in range(1, 14):
                        off = base + (sid - 1) * 12
                        y, x, z = struct.unpack_from('<fff', payload, off)
                        joint_angles[sid] = [y, x, z]
                    self.sig_angle_data.emit(joint_angles)
                else:
                    print(f"[BLE ANGLE] ERROR: payload too short ({len(payload)}), full_pkt={full_pkt[:20].hex()}")
            elif pkg_type == 0x02:
                # PKG_TYPE_IMU_RAW IMU原始包
                pass
            elif pkg_type == 0x03:
                # ===== 文件分块数据包，转发UI处理payload =====
                self.sig_file_chunk.emit(payload)
            elif pkg_type == 0x04:
                # ===== 批次结束通知，payload=next_offset(4B LE) =====
                next_offset = int.from_bytes(payload[0:4], "little")
                self.sig_batch_end.emit(next_offset)
            elif pkg_type == 0x10:
                # ===== 文件列表JSON应答包，转发UI处理payload =====
                self.sig_log.emit(f"[FileList Reply] payload len:{len(payload)}")
                self.sig_file_resp.emit(payload)
            elif pkg_type == 0x11:
                # ===== 文件备注应答包，转发UI处理payload =====
                self.sig_log.emit(f"[FileRemark Reply] payload len:{len(payload)}")
                self.sig_file_remark.emit(payload)

    def _on_notify_imu(self, sender, data: bytes):
        """
        chr_imu 通道notify回调，解析 ble_imu_pkt_t。
        数据包格式（20字节）：
          byte0:     pkg_type (0x02=PKG_TYPE_IMU_RAW)
          byte1-2:   pkg_len (uint16 little-endian)
          byte3:     sensor_id (uint8, 1~13)
          byte4-19:  q[4] (4个float little-endian, qw,qx,qy,qz)

        发出的 dict 格式与 skeleton_3d_view.update_imu_data 期望的一致：
          {sensor_id: {"online": True, "quat": (qw,qx,qy,qz)}}
        """
        if len(data) < 20:
            self.sig_log.emit(f"[IMU notify] too short: {len(data)} bytes")
            return
        try:
            # 调试：打印前10字节的十六进制，确认数据布局
            if not hasattr(self, '_imu_hex_count'):
                self._imu_hex_count = 0
            self._imu_hex_count += 1
            if self._imu_hex_count <= 3:
                hex_str = ' '.join(f'{b:02X}' for b in data[:10])
                print(f"[DEBUG IMU HEX] len={len(data)} bytes: {hex_str}")
            pkg_type = data[0]
            if pkg_type != 0x02:
                self.sig_log.emit(f"[IMU notify] wrong pkg_type=0x{pkg_type:02X}, skip")
                return
            sensor_id = data[3]
            qw, qx, qy, qz = struct.unpack_from('<4f', data, 4)
            # status 字段在 byte20（如果数据包有21字节）
            status = data[20] if len(data) >= 21 else 0
            self.sig_log.emit(f"[IMU notify] id={sensor_id} q=[{qw:.3f},{qx:.3f},{qy:.3f},{qz:.3f}] status=0x{status:02X}")
            # 批量格式：单元素 dict，key=sensor_id(int)
            self.sig_imu_data.emit({
                sensor_id: {
                    "online": True,
                    "quat": (qw, qx, qy, qz),
                    "status": status,
                }
            })
        except Exception as e:
            self.sig_log.emit(f"[IMU notify] parse error: {e}")
